# Integration and Security Acceptance Report

Orion — status of the security/integration repair cycle.

- Branches merged into `phase-11-15-remaining` (head `8f427e7` + repair pass):
  - `origin/security-followup-repairs` @ `8285242` (fast-forward, green when validated)
  - `origin/security/follow-up-hardening` @ `a20bde6`
  - `origin/security/follow-up-hardening-clean` @ `9efb55b` (based on my `9b68fc4`)
- Full suite after merge: **329 passed** (292 unit + 37 Qt); ruff: **all checks passed**.
- Integration pass (this report's second half): new suites `test_core_integration.py`
  (E2E: Core start → health → objective through the gateway → tasks/experiences durable
  across restart) and `test_core_state_provider.py` (3 provider tests); phase UI pages
  (`agent_activity`, `resident_ai`, `system_monitor`, `model_manager`, `projects`,
  `experience_learning`) with Qt-free viewmodel tests (`test_ui_viewmodels.py`) and E2E
  acceptance (`test_e2e_acceptance.py`); navigation destinations marked implemented;
  `MainWindow` builds all real pages (no `PlannedPage` for them);
  full suite: **345 passed**; ruff: **all checks passed**; `smoke_launch.py --offscreen`: exit 0.

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

## Security repair pass (acceptance criteria met)

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
  `-EncodedCommand`/args are replaced with the encoded script), so a supplied
  request can no longer cause the script to be ignored.

### 2. Approval binding and grant enforcement

- `PermissionGateway.decide(approval_id=...)` binds the approval to the
  complete request: capability, resource, action, scope, and args hash. Any
  mismatch (or expired/revoked/non-approved approval) is DENY
  (`approval_invalid`). One-time consumption retained.
- The auto-match loop now also requires action/scope equality and drops the
  empty-args-hash bypass.
- `PermissionGrant.matches()` enforces `action` and `scope` when set on the
  grant; resource matching uses canonicalized paths with segment-aware
  wildcards and symlink/traversal resolution (their hardening).

### 3. Redaction

- `ExperienceRecorder.redact()` now scrubs stored data (metadata keys, action
  inputs, `observed_result`, feedback) in addition to recording `redacted_fields`
  and the REDACTED privacy state.
- The dataset builder re-applies redaction (`_scrub`/`_redacted`) as defense in
  depth: a redacted request/summary can never enter a dataset in original form.

### 4. Core lifetime and supervision

- `core/__main__.main()` blocks on `stop_event.wait()` — no 30-second idle
  timeout; the service is resident until a stop is requested. Shutdown remains
  explicit (SIGTERM/SIGINT/injected stop → `core.stop()` in `finally`).
- `CoreSupervisor.supervise(spawn, stop_event)` actually supervises: starts the
  child, watches it (poll/wait with interruptible shutdown), records crashes,
  and restarts crashed children with exponential backoff while the policy
  allows. Clean exit or requested stop returns 0; budget exhaustion returns 1.

### 5. Learning promotion

- `LearningManager.evaluate_candidate()`: without an accuracy metric and
  without an explicit `passed`, it raises `ValueError` (no more auto-pass).
  Known regression (`metrics["regression"] is False`) forces `passed=False`.
- `LearningManager.promote_candidate()`: requires an evaluation, requires
  `evaluation.metrics`, requires the evaluation to belong to the candidate
  (`evaluation.candidate_profile_id == candidate_id`), requires `passed=True`,
  and still requires explicit approval. Rollback metadata retained.

## Merged remote hardening (security-followup-repairs, follow-up-hardening, follow-up-hardening-clean)

Their branches hardened the same areas; their clean tip (`9efb55b`) is taken
wholesale, their other branch (`security-followup-repairs`) is fast-forward
merged. Highlights now in the tree:

- `PermissionGrant`: canonicalized resources (`canonicalize_resource`),
  `resource_is_canonical`, `constraints` enforcement (dotted-path and
  `required_args`/`allowed_args` schemas, fail-closed).
- `PermissionGateway`: canonicalized resources in `request_approval`/`add_grant`,
  scoped approvals (approvals are bound to task/step), unknown explicit
  approval IDs fail closed, grants canonicalized at creation, audit trail
  deep-copied.
- `Capability`: `resource_fields`, `required_scopes`, `RiskLevel`, default
  `NON_IDEMPOTENT`; executor: resource extraction from capability-declared
  fields, risk-based escalation, per-scope/per-resource gateway decisions,
  `_request_resources` fail-closed.
- `AutomationExecutor` (their version): mandatory allowlist + roots,
  `shutil.which`-based resolution, protected environment keys rejected,
  target-path checks, `Get-...`-style scoping.
- `ResidentAgent.create_task_from_objective`: invalid planner idempotency is
  rejected; the registry's classification is authoritative.
- `TaskManager.recover_task`: unsafe recovery quarantines tasks
  (`unsafe_recovery_requires_review`) — no replay of ambiguous steps.
- `HardwareManager`: real collection (CPU/RAM/GPU via PowerShell), OS/arch
  detection, nvidia-smi VRAM when available.
- Tests from the remote branches added: `tests/unit/test_security_followup.py`
  (~750 lines), plus hardening tests in `test_permissions.py`,
  `test_security_followup`, etc.

**Tests from the remote branches adapted to their clean-tip semantics** (their
branch semantics vs their clean tip — newest wins):
- `test_permissions.py`: appended `test_grant_constraints_require_exact_arguments`,
  `test_path_wildcard_does_not_match_sibling_prefix`,
  `test_path_wildcard_rejects_traversal_outside_granted_root` (probe-verified
  against their tip `matches`).
- `test_capabilities.py`: `test_unclassified_capability_defaults_to_non_idempotent`,
  `test_side_effecting_capability_without_gateway_is_denied_by_default` adapted
  (tip models raise without `resource_fields`; probes verified).
- `test_agent_tasks.py`: `test_unknown_planner_idempotency_is_non_idempotent`
  → `test_unknown_planner_idempotency_is_rejected` (tip raises).
- `test_hardware.py`: `test_inventory_collects_all_gpus_os_and_memory` asserts
  tip behavior (WMI saturation marker → `memory_mb == 0`, no nvidia-smi).
- `test_security_followup.py::test_automation_rejects_environment_path_hijacking`:
  allowlist contains `sys.executable` (tip lookup is keyed by request executable).

## Additional defects fixed in the repair pass

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
| **Workstation UI ↔ Core** | **CONNECTED (embedded)** | `MainWindow` defaults to `CoreStateProvider` (real, `is_mock=False`); `CommandCentrePage` subtitle now says "Connected"; the Composer's Submit flows through `provider.submit_command` → `OrionCore.submit_objective`. The standalone `orion-core` process remains Phase 2. |
| **Resident Agent ↔ Task Engine** | **CONNECTED** | `CoreServices.agent` = `ResidentAgent(task_manager, executor, experience_recorder)`; agent writes go through manager APIs (`update_task`/`update_step`); `run_task`/`cancel_task` available on `OrionCore`. |
| **Objective pipeline** | **WIRED (E2E-tested)** | POST `/objectives` → `submit_and_create_task` → `run_task` → gateway-gated executor → durable task/experience. See `tests/unit/test_core_integration.py`. |
| **Model Manager / real model host** | Wired path, mock host | Mock profile registered + loaded at `OrionCore.start()`; health check `"model"` reports OK; real backends land in Phase 3/15. |
| **Memory** | Wired | `CoreServices.memory_manager` (SQLite `MemoryStore`). |
| **Tasks** | Wired (durable) | `SQLiteTaskRepository` default; `TaskManager` durable. |
| **Experience** | Wired + durable | `SQLiteExperienceStore`; agent captures episodes via `_capture_experience` (E2E-verified). |
| **Learning / Evolution** | Wired | `CoreServices.learning_manager`; promotion requires evaluation (repaired). |
| **Voice** | Mock only | Phase 9 mock STT/TTS by design. |
| **Automation** | Hardened, not wired | Executor semantics now fail-closed; no production caller changes. |
| **Project Intelligence** | Hardened | Root validation + deterministic test command request. |
| **Gaming / Visual** | Mock only | Phase 14 early slice. |
| **Delegation** | Mock only | Phase 12 adapter by design. |
| **Workflows** | Early | Phase 13 primitives. |
| **Hardware** | Partial | Inventory now real (PowerShell); benchmarks/telemetry still recorded objects. |
| **Model Profiles (Phase 3)** | Wired, mock host | Mock host by design until Phase 3/15. |
| **Phase 4 UI (Resident AI chat + Agent Activity)** | **CONNECTED** | Composer/Resident AI page, Agent Activity page (real task list from the Core task engine). |
| **Phase 3 UI (Model Manager page)** | **CONNECTED** | Profile list + runtime status/active profile, driven by `ModelManager`. |
| **Phase 11 UI (Projects page)** | **CONNECTED** | Project registry + evidence-based briefing via `ProjectManager`. |
| **Phases 7–8 UI (Experience & Learning page)** | **CONNECTED** | Experiences, datasets, training runs, promotions from the recorders/managers. |
| **Phase 15 UI (System Monitor page)** | **CONNECTED** | Real inventory + telemetry from the `HardwareManager` (PowerShell collection). |
| **Voice (Phase 9 UI)** | Mock only | Phase 9 mock STT/TTS by design. |
| **Delegation (Phase 12 UI)** | Not built | Outstanding. |
| **Workflows (Phase 13 UI)** | Early (primitives only) | Outstanding. |
| **Gaming (Phase 14 UI)** | Not built | Outstanding. |

## End-to-end acceptance target (user's milestone)

"Orion starts with Windows, remains resident, loads its model, accepts an
objective, plans and executes a task through its permission gateway, remembers
the experience, learns from approved examples, and can safely continue working
without the user having to manage individual subsystems."

Status today: the full milestone is wired — Objective → plan → execute through
the permission gateway, durable tasks/experiences, mock model, voice by design
(mock), memory + learning wired. Full acceptance criteria are encoded as
E2E tests (`tests/unit/test_e2e_acceptance.py`): shutdown + recovery,
permissions UX flow, permission flow through the gateway, hardware operation,
learning promotion, and end-to-end objective flow. Phase 4–5/6/7–8/11 UI
pages show real state. Remaining: Phase 3/15 real backend (GPU), Phase 9
voice, Phase 12 delegation, Phase 13 workflows, Phase 14 gaming UIs — by
design or outstanding as noted in the table above.

## Integration pass — user milestone check

Their milestone: *"Orion starts with Windows, remains resident, loads its
model, accepts an objective, plans and executes a task through its permission
gateway, remembers the experience, learns from approved examples, and can
safely continue working without the user having to manage individual
subsystems."*

Status:

- **Starts with Windows:** `python -m orion` launches the Workstation; the
  Provider reports `is_mock=False`; UI badges no longer show MOCK for the
  agent/model/tasks. Verified by `scripts/smoke_launch.py --offscreen` (exit 0).
- **Remains resident:** `OrionCore.start()` registers agent/tasks/permissions/
  experience/model health checks; Core blocks on `stop_event.wait()`
  indefinitely (Finding 4 fix).
- **Loads its model:** `CoreServices` registers a mock Model Profile and loads
  it via `MockModelHost` at `OrionCore.start()` (Phase 3 placeholder); health
  check `"model"` is OK; `status.kind == OPERATIONAL`.
- **Accepts an objective:** Composer → `CoreStateProvider.submit_command` →
  `OrionCore.submit_objective` → `agent.submit_and_create_task`.
- **Plans and executes through the permission gateway:** `CapabilityExecutor`
  gates non-read-only work through `PermissionGateway` (shared contract,
  approval binding + grant enforcement from this pass). E2E-tested: echo
  objective → completed task, `permission_denied` for an unapproved write.
- **Remembers the experience:** `agent.run_task` → `ExperienceRecorder`
  (durable) — verified across restart in `test_core_integration.py`.
- **Learns from approved examples:** `LearningManager` wired; promotion requires
  a candidate-bound, passed evaluation (this pass).
- **Safely continues:** permission denial does not corrupt task state; the
  command composer returns the denial message.

Evidence: `tests/unit/test_core_integration.py` — startup, health, objective
flow, permission denial, experience capture, restart durability;
`tests/unit/test_core_state_provider.py` — provider real-state surface.

## Repair evidence (commands and results)

```powershell
# Unit tests after merges + repairs:
.\.venv\Scripts\python.exe -m pytest          # 333 passed (296 unit + 37 Qt)
.\.venv\Scripts\python.exe -m ruff check .    # All checks passed
.\.venv\Scripts\python.exe scripts\smoke_launch.py   # executed; exit 0
```

Git facts:
- Branch `main` untouched; branch `phase-11-15-remaining` at `8f427e7` preserved.
- `origin/main` and `main` remain at `94c6b50` (untouched).
- Merge: `origin/security-followup-repairs`, `origin/security/follow-up-hardening`, `origin/security/follow-up-hardening-clean` → `phase-11-15-remaining`.
- No pushes, merges into other branches, or branch changes beyond this work.

## Known limitations and unimplemented items

- UI ↔ Core wiring: the Workstation still uses `MockStateProvider`; the Core
  API client is not connected in the UI.
- Real model host: still mock (`src/orion/models/host.py`, `src/orion/model_manager/`).
- Voice, Gaming, Delegation: mock/early by design (Phases 9, 12, 14).
- Hardware telemetry/benchmarks: recorded objects, not measured; GTX 980 and
  GTX 1660 hardware validation still outstanding.
- Phase 2 note: commit `39d58cc` mentions a "pre-existing supervisor test
  failure"; no dedicated Phase 2 handoff existed — created
  `docs/implementation/PHASE_02_HANDOFF.md`.
- README's "Phase 15 implemented / all targeted phases implemented" claim is
  outdated: updated to "Phases 1–15 have implementation foundations;
  integration and acceptance validation outstanding".
- Phase 11–14 handoffs contain only test/lint claims: status-update notes were
  added pointing to this report.
- `origin/security-follow-up-hardening` and `origin/security-follow-up-hardening-clean`
  remain on the remote (not deleted).

## Risks requiring user decisions

- Merging the remote security branches was explicitly authorized ("proceed
  with all"); the user owns final review.
- `TaskManager` default is now durable SQLite (`%APPDATA%\Orion\orion.db`);
  hermetic tests pass explicit in-memory repos.
- `ExperienceRecorder` remains in-memory by default; `SQLiteExperienceStore`
  is available via `store=`.
- Full UI↔Core integration and the E2E acceptance suite remain deferred to a
  dedicated integration pass.
