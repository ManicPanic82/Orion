# Orion Implementation Roadmap

## Delivery strategy

Build Orion as a sequence of working, testable vertical slices. Establish architecture and contracts first, then deliver a small operational system before adding advanced capabilities.

Do not parallelise phases that depend on unfinished contracts. A phase is complete only when its acceptance tests pass and its documentation is updated.

## Phase 0 — Architecture baseline

**Scope:** Product and engineering documentation only.

Deliverables:
- Product vision and boundaries.
- System architecture.
- Agent rules.
- Subsystem guides.
- Data, API, security, and testing contracts.
- Architecture decision records.

Exit criteria:
- A new agent can identify the current phase and its scope from repository docs.
- Major component boundaries and safety invariants are explicit.
- No application functionality is claimed as implemented.

## Phase 1 — Project foundation and Operations Centre

**Goal:** A polished, navigable PySide6 shell with honest mock state.

Implement:
- Python project metadata and supported version policy.
- Application entry point and configuration.
- Main window, navigation, theme, reusable components.
- Command Centre page.
- Task/status panels with explicit MOCK labels.
- Main command input (local mock submission only).
- Expandable activity console.
- Settings persistence.
- Unit tests for configuration and view-model/state behaviour.

Do not implement real inference, automation, voice, learning, or a background service.

Exit criteria:
- Starts using documented PowerShell instructions.
- Navigation and basic interactions work.
- Settings survive restart.
- Mock state is visibly marked.
- Tests pass on the target Windows environment.

## Phase 2 — Orion Core background process

**Goal:** UI-independent service lifecycle.

Implement:
- Core process entry point.
- Supervisor and health reporting.
- Loopback-only local API.
- Local session/authentication design.
- Structured request validation.
- Event stream and reconnect/resync.
- Tray client and lifecycle controls.
- Graceful shutdown and crash detection.

Exit criteria:
- Core runs without UI.
- UI can disconnect/reconnect.
- Closing UI does not stop Core.
- Service health and event state are real.
- Restart does not duplicate active tasks.

Start as a supervised ordinary process. Do not register a Windows Service until a tested installation/update/uninstall design justifies it.

## Phase 3 — Model Manager and Model Profiles

**Goal:** One user action loads a complete, validated model configuration.

Implement:
- Versioned profile schema.
- Profile repository and UI.
- Mock model-host adapter.
- Runtime interface and typed errors.
- Base/adapter compatibility validation.
- Atomic load/unload lifecycle.
- Health-check inference and state reporting.

Exit criteria:
- Valid mock profile loads.
- Missing required adapter fails.
- Incompatible profile fails.
- Partial load is cleaned up.
- No false READY state.

## Phase 4 — Resident Agent and Task Engine

**Goal:** Accept an objective and track a controlled multi-step task.

Implement:
- Agent interface.
- Objective intake and clarification state.
- Task and task-step state machines.
- Planner abstraction.
- Capability registry.
- Mock capability executor.
- Cancellation, progress, result verification.
- Persistent task history.

Exit criteria:
- Objective creates a durable task.
- State transitions are validated.
- Mock steps run and produce observations.
- Cancellation is effective.
- UI displays authoritative task state.

## Phase 5 — Adaptive Autonomy and Permission Gateway

**Goal:** Deterministic control of all side effects.

Implement:
- Assist, Supervised, Independent, Restricted modes.
- Permission scopes and resource matching.
- Risk classification.
- Approval request lifecycle.
- Audit trail.
- Emergency pause/cancel/stop controls.
- Policy simulation tests.

Exit criteria:
- Every side-effecting tool invocation is gated.
- Denials cannot be overridden by the model.
- Missing permission never becomes allowed due to autonomy mode.
- Gateway failure blocks side effects.
- Approval is scoped, expiring where appropriate, and auditable.

## Phase 6 — Persistent Memory

**Goal:** Durable, searchable, user-controllable personal knowledge.

Implement:
- SQLite migrations and repositories.
- Memory schema and sensitivity labels.
- Capture controls and exclusions.
- Retrieval interface.
- Inspect/edit/delete/export.
- Backup and restore.

Exit criteria:
- Memory survives model/service restart.
- Scope and provenance are visible.
- Excluded/deleted items are not returned in normal retrieval.
- Restore is tested.
- Sensitive data is excluded from ordinary logs.

## Phase 7 — Experience Recorder

**Goal:** Capture useful task episodes without indiscriminate surveillance.

Implement:
- Episode schema.
- Objective/plan/action/observation/outcome capture.
- User feedback and corrections.
- Success/failure/partial/inconclusive classification.
- Capture pause and exclusions.
- Review UI and eligibility status.

Exit criteria:
- Experiences trace to tasks.
- Failure is not labelled as positive success.
- Capture controls are honoured.
- Sensitive data is screened before training eligibility.

## Phase 8 — Orion Evolution learning pipeline

**Goal:** Reviewed experiences become reproducible training artifacts.

Implement:
- Experience selection and curation.
- Privacy and quality review.
- Dataset builder and supported JSONL formats.
- Immutable dataset versions and provenance.
- Mock trainer connector, then real adapter.
- Training run tracking.
- Held-out evaluation.
- Candidate profile registration.
- User-approved promotion and rollback.

Exit criteria:
- Dataset output validates against the trainer contract.
- Every example traces to approved source experience.
- Candidate evaluation is reproducible.
- Active profile is unchanged until explicit approval.
- Rollback metadata is retained.

## Phase 9 — Voice

**Goal:** Push-to-talk voice through the same command interface.

Implement:
- Global shortcut.
- Microphone capture and privacy state.
- Local STT adapter.
- Local TTS adapter.
- Spoken responses and notifications.
- Interrupt/stop-speaking.
- Quiet hours and voice settings.

Exit criteria:
- Voice request and typed request reach the same agent API.
- Voice provider failure does not break text.
- Mic status is visible.
- User can interrupt speech immediately.

Wake word, VAD, and continuous conversation are later optional increments.

## Phase 10 — Windows automation

**Goal:** Controlled, auditable Windows operations.

Implement:
- Process execution service.
- PowerShell adapter.
- Approved workspace scopes.
- Argument validation.
- Timeouts and cancellation.
- Output/exit-code capture.
- File-operation controls and recovery.
- Execution audit.

Exit criteria:
- Disallowed targets/paths are blocked.
- Timeout and cancellation tests pass.
- Commands run under defined identity and environment.
- No unrestricted shell is exposed to the model.

## Phase 11 — Project Intelligence

**Goal:** Evidence-based project understanding.

Implement:
- Project registry.
- Filesystem/Git read adapters.
- Test command profiles.
- Project briefing.
- Cached knowledge freshness indicators.
- Watchdog foundations.

Exit criteria:
- Branch/status/test claims come from actual inspection.
- Cached knowledge is labelled.
- Git write actions remain gated.
- Project access is scoped.

## Phase 12 — Main-agent delegation

**Goal:** Delegate suitable work to the user's existing main agent.

Implement:
- Replaceable adapter contract.
- Mock adapter.
- Structured task handoff.
- Progress and result retrieval.
- Verification of returned work.
- Permission inheritance.

Exit criteria:
- Delegations are traceable to parent tasks.
- External agent cannot widen Orion permissions.
- Failure and timeout are handled.
- Returned changes are inspected before being treated as complete.

## Phase 13 — Capability expansion and adaptive workflows

**Goal:** Reusable procedures and bounded ongoing goals.

Implement:
- Procedure registry/versioning.
- User-defined goals and success criteria.
- Scheduling and triggers.
- Daily briefing.
- Quiet Intelligence mode.
- Capability health and diagnostics.
- Improved planning and recovery.

Exit criteria:
- Procedures are inspectable and revocable.
- Goals do not imply unlimited permissions.
- Schedules have budgets, scopes, and stop controls.
- Notifications respect priority and quiet hours.

## Phase 14 — Gaming and visual interaction

**Goal:** A safe visual-observation/action learning loop.

Implement:
- Selected-window capture.
- Observation processing.
- Action interface.
- Foreground-window and input scope.
- Episode recording.
- Reward/progress evaluation.
- Demonstration and self-attempt datasets.

Exit criteria:
- Input cannot leak to unrelated windows.
- User can interrupt immediately.
- Episodes include observations, actions, and outcomes.
- Game-specific performance is evaluated independently.

## Phase 15 — Real hardware and performance validation

**Goal:** Validate real inference and sustained operation on actual hardware.

Implement:
- Supported inference backend(s).
- GTX 980 detection and Maxwell compatibility tests.
- Candidate model benchmarks.
- GTX 1660 training connector validation.
- VRAM/RAM/latency telemetry.
- Sustained operation and recovery tests.

Exit criteria:
- Hardware support is based on measured results.
- Unsupported operations fail clearly.
- Base and adapter load as one profile.
- Performance and stability reports are retained.
- Existing training environment has not been damaged.

## Cross-phase rules

- Tests accompany implementation, not follow it.
- Migrations are versioned and tested.
- Mock and real providers share contracts.
- User-visible state is backed by actual state.
- Security invariants are tested at capability boundaries.
- Keep the active phase small; defer unrelated improvements.
- Update this roadmap when scope changes, with a decision record.