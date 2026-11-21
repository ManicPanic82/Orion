# ADR-003: Deterministic Permission Gateway

- **Status:** Accepted
- **Decision:** All side-effecting capability invocations pass through a deterministic Permission Gateway. Autonomy level never creates a permission grant.

## Context
A model can produce unsafe, incorrect, or prompt-injected action proposals. Natural-language instructions are not a security boundary.

## Consequences
- Policy is application code, not prompt text.
- Gateway failure defaults to deny.
- Approvals are scoped and auditable.
- External agents inherit Orion's restrictions.
- Risk classification can increase supervision but cannot override explicit denial.