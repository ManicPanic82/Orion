# ADR-006: Mock-First Integration Strategy

- **Status:** Accepted
- **Decision:** External systems and hardware integrations begin with mock adapters implementing the same contracts as real adapters.

## Context
Development must progress without depending on uncertain model runtimes, GPU compatibility, voice engines, trainer APIs, or external-agent protocols.

## Consequences
- Mocks are explicit in UI and logs.
- Mock success does not prove real integration.
- Real adapters replace mocks behind stable interfaces.
- Acceptance tests separately validate mock behaviour and real provider compatibility.