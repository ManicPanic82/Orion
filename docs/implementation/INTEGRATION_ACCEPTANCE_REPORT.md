# Integration and Security Acceptance Report

Orion — status of the security/integration repair cycle.

- Original repair baseline: `phase-11-15-remaining` @ `8f427e7`.
- Follow-up hardening is recorded separately on `security/follow-up-hardening`; the original development branch and `main` remain unchanged.
- Report written after the security and integration repair pass; see
  "Repair evidence" for the exact commands and results.

## Verdict

Orion still is **not** the integrated Resident AI Workstation the roadmap
intends. Subsystem foundations are present, but the follow-up audit found additional permission, recovery, privacy, and evaluation edge cases. Follow-up hardening changes are now committed on an isolated branch; Windows execution and validation are still pending. Do not treat the README's "Phases 1–15 present; all targeted phases
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
- `PermissionGrant.matches()` requires exact capability/action/scope/resource selectors by default; wildcard selectors must be explicit, constraints are enforced, and path wildcards are segment-aware.

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
| Hardware inventory: CPU "unknown", RAM 0, GPU name = `platform.processor()` | PowerShell queries for CPU, RAM, Windows OS and all display adapters; NVIDIA VRAM/driver/device data uses `nvidia-smi` where available; WMI's 32-bit AdapterRAM cap is not treated as reliable VRAM | `test_inventory_collects_real_values_when_queries_succeed`, `test_inventory_falls_back_when_queries_return_nothing` |
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

Git facts (historical and current):
- The original branch `phase-11-15-remaining` was preserved.
- Follow-up changes were pushed to the isolated branch `security/follow-up-hardening`.
- `main` was not changed and no merge or pull request was created.
- The earlier statement "No pushes, no merges, no branch changes" described the original repair pass only and is superseded by this follow-up.

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


## Security follow-up hardening

The follow-up audit identified additional edge cases after the original 281-test
repair pass. These changes are isolated on `security/follow-up-hardening`.

| Finding | Follow-up change |
|---|---|
| Capability default was READ_ONLY | Capability and task-step defaults are now NON_IDEMPOTENT. The agent persists classification from the registered capability, never from planner output. |
| Capability metadata could be mutated after registration | Registry stores and returns isolated metadata snapshots while retaining trusted handler callables. |
| A capability could reference multiple resources | Each capability must declare its resource fields (or an explicit global selector); undeclared resource-like inputs fail closed. Executor requires authorization for every resource/scope pair. Medium/high/critical risk reads also require gateway authorization. |
| Resource grants could be escaped through path traversal or symlinks | Grant matching resolves filesystem paths and checks segment boundaries; lexical traversal and resolved symlink/junction escapes are rejected. |
| Required capability scopes were not enforced | CapabilityExecutor passes the actual resource, action, task/step, and every declared scope to the shared gateway. Scoped read-only operations require an exact grant/approval. |
| Grant constraints were ignored | Grant constraints now match exact dotted argument paths; malformed or unknown constraints fail closed. |
| Empty grant selectors acted as wildcards | Capability, action, scope, and resource selectors are exact by default. Wildcards must be explicit. Resource matching normalizes traversal segments and uses path-segment boundaries. |
| Returned policy objects could mutate gateway state | Grants, approvals, and audit records are copied at API boundaries; callers cannot widen stored policy by mutating returned objects. |
| Approval resource/scope/task/step could be reused | Approvals now bind exact capability, action, resource, scope, canonical argument hash, task ID, and step ID. Unknown explicit approval IDs are denied. Task/step-specific persistent approvals do not create reusable grants. |
| Planner could downgrade a step to READ_ONLY | Invalid planner classifications are rejected. Stored task classifications are reconciled from trusted registered capability metadata before execution. |
| Restart could replay an ambiguous in-flight step | Any persisted RUNNING step is quarantined on recovery. The task is paused for explicit reconciliation and the agent refuses to execute it automatically. In-memory task repository reads/writes are isolated snapshots. |
| Supervisor could block indefinitely during shutdown | The supervisor polls child processes, observes stop events, terminates children, escalates to kill after a grace period, and uses interruptible restart backoff. |
| Nested feedback/action content escaped redaction | Redaction recursively scrubs nested mappings and covers feedback content/author and action payloads. Experience records are isolated snapshots, serialization re-applies redaction, and later feedback remains scrubbed even if review state changes. |
| Caller could forge a passing evaluation object | Caller-supplied pass/fail is rejected. Evaluations require a registered dataset, non-empty held-out split, matching checksum and exact held-out example count. Evaluation and dataset records are isolated from caller mutation; promotion accepts only a matching manager-issued evaluation. |
| Task request IDs were not restored after restart | TaskManager rebuilds its request deduplication index from the durable repository. |
| Project records could be mutated after root validation | ProjectManager stores and returns snapshots and revalidates the canonical project root before inspection or test execution. |
| Training accepted unregistered or caller-mutated datasets | LearningManager accepts only its own registered dataset snapshots with a non-empty training split. |
| Hardware inventory omitted GPUs and misreported OS/VRAM | Inventory reports Windows OS details, all detected adapters, and NVIDIA VRAM/driver/device identity via nvidia-smi where available. Capped WMI adapter memory is not presented as reliable VRAM. |

Twenty-seven focused regression tests were added in `tests/unit/test_security_followup.py`; `tests/unit/test_learning.py` gained four dataset/evaluation tests and `tests/unit/test_projects.py` gained one project-root snapshot test. Existing experience, permission, and automation tests were updated for snapshot and exact-grant semantics. In total, 32 additional regression tests are authored on this branch. The follow-up changes have not been
executed in the user's Windows environment from this audit session. The
previous 281-passed/Ruff/smoke results apply to the earlier repair baseline,
not this follow-up branch.

Required local acceptance on Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q src tests scripts
.\.venv\Scripts\python.exe scripts\smoke_launch.py --offscreen
```

A passing local run is required before treating this follow-up as validated.
The held-out evaluation API now verifies dataset identity and split metadata,
but a real model evaluator that independently computes metrics against that
split remains part of the future model/learning integration milestone.
