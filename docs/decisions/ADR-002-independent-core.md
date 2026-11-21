# ADR-002: UI Independent from Background Core

- **Status:** Accepted
- **Decision:** Orion Workstation is a client of Orion Core. Core runs independently and owns task lifecycle.

## Context
The assistant must continue working when the dashboard is closed.

## Consequences
- UI communicates over a versioned local API/event stream.
- Core owns tasks, persistence, model lifecycle, and background execution.
- UI reconnects and resynchronises from authoritative state.
- Start with a supervised process; Windows Service registration is deferred until justified.
- UI shutdown and Core shutdown are separate operations.