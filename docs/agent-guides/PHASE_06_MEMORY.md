# Agent Guide: Phase 6 — Persistent Memory

## Objective
Store and retrieve useful personal/project context independently of model identity.

## Prerequisites
SQLite migration/repository foundations and capture controls.

## In scope
- Memory record schema.
- Memory repository and manager.
- Scoped retrieval interface.
- Provenance, confidence, sensitivity, validity.
- Inspect/edit/delete/export UI.
- Project/conversation exclusions.
- Backup and restore.

## Implementation instructions
1. Treat memory as curated facts/preferences/decisions, not an unfiltered transcript archive.
2. Store provenance, source time, last verification, confidence, scope, sensitivity, and validity.
3. Separate temporary context from durable memory.
4. Support supersession and outdated status.
5. Retrieval must respect project scope, exclusions, deletion, and sensitivity policy.
6. Start with SQLite FTS or equivalent simple retrieval; define a replaceable interface before adding embeddings.
7. Provide user controls to inspect, correct, delete, pause capture, and exclude scopes.
8. Ensure deleted/excluded records are not returned by normal retrieval or selected for future training.
9. Back up database and test restoration.
10. Never store passwords, access tokens, or unrelated private content.

## Forbidden shortcuts
- No indiscriminate whole-chat retrieval.
- No memory derived from sensitive attributes.
- No model-specific memory format as the only store.
- No claim of secure deletion unless implemented and tested.

## Acceptance tests
- Create/search/update/delete memory.
- Scope and expiry filtering.
- Exclusion honoured.
- Model identity change does not affect memory.
- Backup restore reproduces expected records.
- Secret-like content is rejected or redacted by policy.

## Handoff
Document categories, retrieval ranking/filtering, deletion semantics, migration, and backup results.