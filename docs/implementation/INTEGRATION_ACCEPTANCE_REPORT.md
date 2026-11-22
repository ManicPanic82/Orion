# Integration and Security Acceptance Report

Orion — status of the security/integration repair cycle.

- Reviewed branch: `phase-11-15-remaining` @ `8f427e7`.
- Report written after the security and integration repair pass; see
  "Repair evidence" for the exact commands and results.

## Verdict

Orion still is **not** the integrated Resident AI Workstation the roadmap
intends. Subsystems are present and individually sound; they are not wired
together. Do not treat the README's "Phases 1–15 present; all targeted phases
implemented" claim as a product claim. The real milestone is: Orion starts with
Windows, remains resident, loads its model, accepts an objective, plans and
executes a task through its permission gateway, remembers the experience,
learns from approved examples, and safely continues without the user managing
individual subsystems. The foundation for that milestone is now in place; the
wiring and end-to-end acceptance are outstanding (details below).

## User-reported critical findings — repair status

| # | Finding (user) | Status | Where fixed |
|---|---|---|---|
| 1 | Automation permission bypass: read-only default + optional restrictions | **Fixed** | `src/orion/automation/models.py`, `src/orion/automation/executor.py` |
| 2 | Approval reuse not bound to capability/resource/action/args; grants ignore action/scope | **Fixed** | `src/orion/permissions/gateway.py`, `src/orion/permissions/models.py` |
| 3 | Redacted experience data enters training via dataset builder | **Fixed** | `src/orion/experience/manager.py`, `src/orion/learning/builder.py` |
| 4 | Core exits after 30 s; supervisor only computes restart decisions | **Fixed** | `src/orion/core/__main__.py`, `src/orion/core/supervisor.py` |
| 5 | Candidate promotion without evaluation; evaluation not candidate-bound | **Fixed** | `src/orion/learning/manager.py` |

### 1. Automation permission bypass

- `ExecutionRequest.idempotency` now defaults to `NON_IDEMPOTENT` — a
  side-effecting classification is never assumed.
- `AutomationExecutor.validate_request()` is default-deny and requires:
  non-empty `allowed_executables`, non-empty `approved_roots`, and the
  executable must be in the allowlist.
- `classify_request()` performs deterministic classification: read-only only
  when the command matches the fixed module-level allowlist (`git status`,
  `git log`); everything else is non-idempotent. A model-supplied "read_only"
  classification can only widen within the allowlist.
- `run_powershell()` always runs the supplied script (any caller-supplied
  `-EncodedCommand`/args are dropped), so a supplied request can no longer
  cause the script to be ignored.

Acceptance (tests): 13 tests in `tests/unit/test_automation.py` — read-only
without gateway only via allowlist; side effects denied without gateway;
mandatory restrictions raise; supplied PowerShell script always wins.

### 2. Approval binding and grant enforcement

- `PermissionGateway.decide(approval_id=...)` now binds the approval to the
  complete request: capability, resource, action, scope, and args hash. Any
  mismatch (or expired/revoked/non-approved approval) is DENY
  (`approval_invalid`). One-time consumption retained.
- The auto-match loop now also requires action and scope equality and drops
  the empty-args-hash bypass.
- `PermissionGrant.matches()` enforces `action` and `scope` when set on the
  grant (resource matching already used `relative_to` semantics).

Acceptance (tests): 7 tests in `tests/unit/test_permissions.py`
(`test_approval_binding_rejects_wrong_*`, `test_approval_binding_accepts_matching_request`,
`test_grant_enforces_action_constraint`, `test_grant_enforces_scope_constraint`).

### 3. Redaction

- `ExperienceRecorder.redact()` now scrubs stored data (metadata keys, action
  inputs, `observed_result`) in addition to recording `redacted_fields` and the
  REDACTED privacy state.
- `_example_from_experience` in the dataset builder re-applies redaction
  (`_scrub`/`_redacted`) as defense in depth: a redacted request/summary can
  never enter a dataset in original form even if stored data is mutated after
  redaction.

Acceptance (tests): `test_redact_scrubs_stored_data`,
`test_redacted_experience_does_not_leak_into_dataset` (blob assertions on the
built dataset JSONL).

### 4. Core lifetime and supervision

- `core/__main__.main()` blocks on `stop_event.wait()` — no 30-second idle
  timeout. Shutdown remains explicit (SIGTERM/SIGINT/injected stop →
  `core.stop()` in `finally`).
- `CoreSupervisor.supervise(spawn, stop_event=...)` actually supervises: starts
  the child, watches it, records crashes, and restarts it with exponential
  backoff while the policy allows. Clean exit or requested stop returns 0;
  budget exhaustion returns 1.

Acceptance (tests): 5 tests in `tests/unit/test_core_supervisor.py`
(restart within budget, budget exhaustion → FAILED, stop event → 0, zero exit
is clean).

### 5. Learning promotion

- `LearningManager.evaluate_candidate()`: without an accuracy metric and
  without an explicit `passed`, it raises `ValueError` (no more auto-pass).
  Known regression (`metrics["regression"] is False`) forces `passed=False`.
- `LearningManager.promote_candidate()`: requires an evaluation
  (`ValueError` if none), requires `evaluation.metrics`, requires the
  evaluation to belong to the candidate (`evaluation.candidate_profile_id ==
  candidate_id`), requires `passed=True`, and still requires explicit
  approval. Rollback metadata retained.

Acceptance (tests): 8 tests in `tests/unit/test_learning.py`.

## Additional defects fixed

| Finding | Fix | Tests |
|---|---|---|
| ProjectManager root validation used `str.startswith` (sibling prefix accepted) | `root_path.is_relative_to(...)` in `src/orion/projects/manager.py` | 3 in `tests/unit/test_projects.py` (incl. `proj2` vs allowed root `proj`) |
| Dataset split took the first N records | Seeded shuffle (`_split_ids`, seed from version + content); eval/train disjoint and covering | `test_dataset_split_is_reproducible` |
| Hardware inventory: CPU "unknown", RAM 0, GPU name = `platform.processor()` | Real PowerShell queries: `Win32_Processor`, `Win32_ComputerSystem.TotalPhysicalMemory`, `Win32_VideoController` with vendor detection; graceful fallback | `test_inventory_collects_real_values_when_queries_succeed`, `test_inventory_falls_back_when_queries_return_nothing` |
| PowerShell executor: supplied request could ignore the script | See #1 (script always runs) | `test_powershell_supplied_request_script_wins` |
| Phase integration: capability executor vs. real permission gateway — incompatible interfaces and two `PermissionDecision` enums | `src/orion/capabilities/permissions.py` now aliases the real enum/contract (`decide(...) -> PolicyDecision`); `CapabilityExecutor` calls the real gateway signature (`idempotency`, `step_id`, `args`) and checks `decision.decision`; `MockPermissionGateway` returns a labelled mock `PolicyDecision(ALLOW)` | existing `test_capabilities.py`, `test_agent_tasks.py` — Agent now uses manager APIs (`update_task`/`update_step`) |
| Task repository in-memory | New `SQLiteTaskRepository` (durable, migrations pattern); `TaskManager` durable by default (`db_path` overridable) | `tests/unit/test_task_repository.py`: roundtrip, restart survival, delete |
| Experience in-memory | New `SQLiteExperienceStore` (`src/orion/experience/store.py`); `ExperienceRecorder(store=...)` routes get/list/save/delete through the store; recorder durable path unit-tested | `test_sqlite_experience_store_roundtrip`, `test_sqlite_experience_store_delete` |

## Integration status (user's "biggest architectural problem")

| Component | State | Notes |
|---|---|---|
| **Workstation UI ↔ Core** | **Not wired** | `MainWindow` uses `MockStateProvider` by default (`src/orion/ui/main_window.py`: `provider or MockStateProvider()`); `CommandCentrePage` subtitle still says "Phase 1 shell... every value below is simulated" (`src/orion/ui/pages/command_centre.py`). |
| **Resident Agent ↔ Task Engine** | Partial | Interface mismatch fixed (shared gateway contract); Agent→`TaskManager` writes now go through manager APIs; durable `TaskManager` default. |
| **Model Manager / real model host** | Not wired | Mock host only (Phase 3 admission). |
| **Memory** | Wired path present | SQLite `MemoryStore` durable; UI memory page separate Phase 6. |
| **Tasks** | Wired (durable) | `SQLiteTaskRepository` default; `TaskManager` durable. |
| **Experience** | Partial | Durable via `SQLiteExperienceStore` (opt-in `store` param); recorder default remains in-memory. |
| **Learning / Evolution** | Partial | Pipeline complete; promotion requires evaluation (repaired); no end-to-end trigger wiring yet. |
| **Voice** | Mock only | Phase 9 mock STT/TTS by design. |
| **Automation** | Hardened, not wired | Executor semantics now fail-closed; no production caller changes. |
| **Project Intelligence** | Hardened | Root validation + deterministic test command request. |
| **Gaming / Visual** | Mock only | Phase 14 early slice. |
| **Delegation** | Mock only | Phase 12 adapter by design. |
| **Workflows** | Early | Phase 13 primitives. |
| **Hardware** | Partial | Inventory now real (PowerShell); benchmarks/telemetry still recorded objects. |
| **Model Profiles (Phase 3)** | Partial | Mock host by design. |
| **Phase 4–5, 9, 12, 14 UI wiring** | Outstanding | Higher-level flows not integrated into the Workstation. |

## End-to-end acceptance target (user's milestone)

"Orion starts with Windows, remains resident, loads its model, accepts an
objective, plans and executes a task through its permission gateway, remembers
the experience, learns from approved examples, and can safely continue working
without the user having to manage individual subsystems."

Status today: foundation repaired and tested; full acceptance criteria still
to be encoded as end-to-end tests (startup + resident lifetime, permission
flow through the gateway with approvals, task execution through the durable
task engine, memory + experience capture, learning gate, shutdown/recovery).

## Repair evidence (commands and results)

```powershell
# Unit tests after repairs:
.\.venv\Scripts\python.exe -m pytest          # 281 passed (was 243 before the repair pass)
.\.venv\Scripts\python.exe -m ruff check .    # All checks passed
.\.venv\Scripts\python.exe scripts\smoke_launch.py   # executed; see validation log below
```

Git facts:
- Branch `main` untouched; branch `phase-11-15-remaining` at `8f427e7` preserved.
- No pushes, no merges, no branch changes.

## Known limitations and unimplemented items

- UI ↔ Core wiring: the Workstation still uses `MockStateProvider`; the Core
  API client is not connected in the UI.
- Real model host: still mock (`src/orion/models/host.py`, `src/orion/model_manager/`).
- Voice, Gaming, Delegation: mock/early by design (Phases 9, 12, 14).
- Hardware telemetry/benchmarks: recorded objects, not measured; GTX 980 and
  GTX 1660 hardware validation still outstanding.
- `docs/implementation/PHASE_02_HANDOFF.md` was missing; created (see
  PHASE_02_HANDOFF.md).
- README's "Phase 15 implemented / all targeted phases implemented" claim is
  outdated: update to "Phases 1–15 have implementation foundations;
  integration and acceptance validation outstanding" (done in this pass).
- Phase 11–14 handoffs contain only test/lint claims: a status update note was
  added pointing to this report.

## Risks requiring user decisions

- Making `ExperienceRecorder()` default to `SQLiteExperienceStore` changes the
  hermeticity of unit tests (writes `%APPDATA%\Orion\orion.db`); left as
  opt-in store for now.
- `TaskManager` durable default writes `app_data_dir()/orion.db`; tests were
  updated to use `InMemoryTaskRepository` where behavior under test is not
  durability.
- Scope: full UI↔Core integration and end-to-end acceptance tests are
  deliberately deferred to a dedicated integration pass.
