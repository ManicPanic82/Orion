# Agent Guide: Phase 2 — Orion Core Background Service

## Objective
Introduce an independently running Core process and make the desktop UI a reconnectable client.

## Prerequisites
Phase 1 complete. Read architecture runtime boundaries, contracts, security, and testing strategy.

## In scope
- Core process entry point.
- Supervisor and component lifecycle.
- Loopback-only API.
- Local client authentication/session strategy.
- Versioned request/response schemas.
- Health endpoint and structured health model.
- Event stream with reconnect/resynchronisation.
- Tray integration if stable in the selected Windows/Qt stack.
- Graceful shutdown, crash detection, bounded restart policy.

## Implementation instructions
1. Define lifecycle states: STOPPED, STARTING, READY, DEGRADED, STOPPING, FAILED.
2. Define explicit API contracts and schema versions before UI wiring.
3. Bind only to loopback. Do not expose arbitrary command/file endpoints.
4. Authenticate local clients using an appropriate per-user secret/session or OS-backed mechanism; document residual same-user risks.
5. Use request IDs and idempotency keys for operations that may be retried.
6. Publish events with IDs and sequence/cursor information. On reconnect, client fetches authoritative snapshot then resumes events.
7. Treat event delivery as at-least-once or best-effort; consumers must tolerate duplicates.
8. Core owns its children and shuts them down gracefully. Never kill unrelated processes.
9. Add health checks and exponential/backoff restart limits. After repeated failure, stop restarting and expose diagnostics.
10. Closing the UI must not signal Core shutdown. Tray exit and Core stop must be distinct actions.

## Forbidden shortcuts
- No Windows Service registration in this phase.
- No unauthenticated API.
- No unrestricted execution endpoint.
- No assuming events alone are durable task state.
- No infinite restart loop.

## Acceptance tests
- Start Core without UI.
- Connect and disconnect UI repeatedly.
- Close UI; Core remains healthy.
- Restart Core; UI reconnects and reloads state.
- Simulate Core crash and observe bounded recovery.
- Verify non-loopback binding is rejected.
- Verify invalid/oversized requests are rejected.
- Verify clean shutdown and owned child cleanup.

## Handoff
Document API routes/schemas, authentication approach, lifecycle states, startup/stop commands, and test evidence.