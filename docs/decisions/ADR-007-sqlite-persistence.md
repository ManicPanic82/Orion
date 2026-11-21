# ADR-007: SQLite as Initial Authoritative Store

- **Status:** Accepted
- **Decision:** SQLite is the initial authoritative store for structured Orion state.

## Context
The initial application is a single-user Windows workstation. A local transactional database is appropriate and avoids premature service infrastructure.

## Consequences
- Use migrations, foreign keys, transactions, indexes, and repository interfaces.
- Large model and dataset files remain outside the database.
- Retrieval/vector indexing remains replaceable.
- Revisit storage only when measured concurrency or scale requirements justify it.