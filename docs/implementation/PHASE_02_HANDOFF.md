# Phase 2 Handoff - Orion Core background process

Branch: `phase-2-core-service` (not pushed, not merged)
Phase: 2
Commit: `39d58cc` `feat(phase-2): Add Orion Core background process infrastructure`

## Scope

Implemented the Orion Core background process infrastructure:

- Standalone Core entry point (`python -m orion.core`): Core runs without any UI.
- Core service facade (`OrionCore`): lifecycle state machine
  (STOPPED → STARTING → READY/DEGRADED/FAILED), health monitor (process + API
  checks), structured event stream, loopback-only API server with bearer token,
  request/response validation, reconnect/resync semantics.
- `CoreSupervisor` + `RestartPolicy`: bounded exponential-backoff restart budget
  (1 restart, 1s → 30s) and crash diagnostics. Later repaired into real
  supervision — see below.
- Core entry point is now persistent: blocks on `stop_event.wait()` until
  SIGTERM/SIGINT or an injected stop. Previously the process exited after
  30 seconds idle (`stop_event.wait(timeout=30.0)`), which was a defect.

## Files

- `src/orion/core/__main__.py`, `src/orion/core/service.py`, `src/orion/core/api.py`,
  `src/orion/core/events.py`, `src/orion/core/health.py`, `src/orion/core/lifecycle.py`,
  `src/orion/core/supervisor.py`.
- `src/orion/config/settings.py` — Core connection configuration.
- Tests: `tests/unit/test_core_api.py`, `test_core_events.py`, `test_core_health.py`,
  `test_core_lifecycle.py`, `test_core_no_qt.py`, `test_core_service.py`,
  `test_core_supervisor.py`.

## Repairs (integration/security pass, 2026-11-22)

- **Persistent service lifetime:** `core/__main__.py` no longer times out after
  30 seconds; the Core stays resident until an explicit stop.
- **Real supervised restart behaviour:** `CoreSupervisor.supervise(spawn, stop_event)`
  now actually supervises: it starts the child via `spawn`, watches it, records
  crashes, and restarts while the policy permits. Previously the supervisor only
  computed restart decisions and never started/restarted anything (no child
  process existed). Unit tests prove: restart within budget, failure when the
  budget is exhausted, clean stop, zero-exit child.

## Validation

- `.\.venv\Scripts\python.exe -m pytest` — at commit time: 116/117 passing, with a
  pre-existing supervisor test failure the commit message flagged as "unrelated".
  This document records the repair; the full suite now passes (see
  INTEGRATION_ACCEPTANCE_REPORT.md).
- `.\.venv\Scripts\python.exe -m ruff check .` — all checks passed.

## Known limitations

- The Workstation UI still uses the Phase 1 `MockStateProvider`; the UI is not
  wired to the running Core.
- The supervisor's supervise loop is tested with fake children; there is no
  production caller yet (Core is its own process).

See `docs/implementation/INTEGRATION_ACCEPTANCE_REPORT.md` for the integration
and security acceptance status.
