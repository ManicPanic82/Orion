# Testing and Verification Strategy

## 1. Purpose

Orion is an autonomous-capable application. Correctness includes safety, lifecycle, persistence, recovery, and truthful reporting, not only whether a screen renders.

Tests must be repeatable on Windows and use mocks for external dependencies until a real adapter is deliberately enabled.

## 2. Test layers

### Unit
Pure domain logic: schemas, policy decisions, state transitions, risk classification, profile validation, memory eligibility, dataset formatting.

### Component
A subsystem with its repository/provider mocked: task manager, model manager, event publisher, capability executor, memory manager.

### Integration
Real subsystem boundaries: UI client to local API, API to task manager, task manager to SQLite, permission gateway to executor, profile manager to model-host adapter.

### Acceptance
User workflows across the application, including closing/reopening UI, approvals, cancellation, recovery, model profile load, and learning review.

### Simulation/fault injection
Service crash, model host failure, database lock/unavailability, event disconnect, timeout, duplicate delivery, partial model load, trainer outage, and interrupted non-idempotent task.

## 3. Required test invariants

- Autonomy mode never grants missing permission.
- Permission gateway failure blocks side effects.
- UI process exit does not terminate Core.
- UI reconnect reloads authoritative state.
- Task transitions reject invalid transitions.
- Non-idempotent actions are not blindly retried.
- Required adapter absence causes profile load failure.
- Profile is not READY before health check.
- Memory remains after model replacement.
- Excluded memory/experiences are not retrieved/selected.
- Failed experience is not emitted as a positive success example.
- Dataset provenance is complete.
- Candidate model promotion requires explicit user approval.
- Mock provider is labelled mock.
- Voice failure leaves text path operational.
- External agent cannot widen Orion permissions.

## 4. Windows validation

Use the project's selected Python version and virtual environment. Document exact PowerShell commands in the implementation README once created.

Prefer:
- `..venv\Scripts\python.exe -m pytest`
- `..venv\Scripts\python.exe -m ruff check .`
- `..venv\Scripts\python.exe -m mypy <configured paths>`

Only run commands for tools actually configured. Do not claim success for skipped commands.

## 5. UI testing

- Test view-model/state logic independently of Qt where possible.
- Add Qt tests for navigation, state rendering, settings, and interactions.
- Verify mock labels are visible.
- Verify unavailable/degraded/error states.
- Do not use hard-coded fake telemetry in production UI paths.

## 6. Database testing

- Fresh database migration.
- Upgrade from previous schema.
- Foreign-key enforcement.
- Transaction rollback on failure.
- Backup and restore.
- Concurrent read/write behaviour appropriate to the chosen connection strategy.
- Corrupt/unavailable database degraded behaviour.

## 7. Acceptance scenarios

1. Start Core without UI.
2. Connect UI to Core.
3. Close UI and confirm Core remains healthy.
4. Reopen UI and recover current state.
5. Submit objective and observe task lifecycle.
6. Cancel running task.
7. Deny restricted action.
8. Approve a scoped action and verify exact target.
9. Simulate gateway failure and confirm no side effect.
10. Load valid Model Profile.
11. Fail profile with missing adapter.
12. Fail profile with incompatible backend.
13. Restart service and recover only safe tasks.
14. Record, review, exclude, and retrieve an experience.
15. Build dataset and verify provenance.
16. Simulate trainer unavailable.
17. Evaluate candidate and reject promotion without user approval.
18. Restore backup.
19. Interrupt TTS and verify text still works.
20. Verify external delegation retains local permission boundaries.

## 8. Test reporting

Every implementation handoff includes exact commands, pass/fail/skip counts, environment details relevant to failures, and tests not run. Never invent benchmark values or imply a mock test proves real hardware/runtime support.