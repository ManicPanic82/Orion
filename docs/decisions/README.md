# Architecture Decision Records

Architecture Decision Records (ADRs) capture decisions that materially affect system structure, safety, dependencies, or long-term maintenance.

## Status vocabulary

- **Proposed:** Under discussion; not yet binding.
- **Accepted:** Approved baseline.
- **Superseded:** Replaced by a later decision.
- **Deprecated:** No longer recommended, retained for historical context.

## Accepted baseline decisions

| ID | Decision | Status |
|---|---|---|
| [ADR-001](ADR-001-integrated-agent.md) | One integrated resident agent | Accepted |
| [ADR-002](ADR-002-independent-core.md) | UI separate from background Core | Accepted |
| [ADR-003](ADR-003-permission-gateway.md) | Deterministic permission gateway | Accepted |
| [ADR-004](ADR-004-model-profiles.md) | Atomic base-model + adapter profiles | Accepted |
| [ADR-005](ADR-005-memory-learning-separation.md) | Separate memory, experience, and training | Accepted |
| [ADR-006](ADR-006-mock-first.md) | Mock-first integration strategy | Accepted |
| [ADR-007](ADR-007-sqlite-persistence.md) | SQLite as initial authoritative store | Accepted |
| [ADR-008](ADR-008-windows-first.md) | Windows-first development | Accepted |

## Adding an ADR

Create a numbered file with:
- Title and status.
- Context/problem.
- Decision.
- Alternatives considered.
- Consequences/trade-offs.
- Security/privacy impact.
- Migration implications.
- Date and references.

Do not silently rewrite an accepted ADR. Supersede it with a new ADR and update architecture/roadmap references.