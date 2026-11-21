# Agent Guide: Phase 11 — Project Intelligence

## Objective
Give Orion current, evidence-based understanding of registered development projects.

## Prerequisites
Scoped filesystem read capability, Git inspection adapter, task engine, permission model.

## In scope
- Project registry UI and storage.
- Project root validation.
- Git read-only inspection.
- Documentation and configuration indexing.
- Configured test commands.
- Project briefing with evidence timestamps.
- Optional watchdog foundations.

## Implementation instructions
1. User explicitly registers project roots and allowed scopes.
2. Validate paths and avoid scanning outside registered roots.
3. Use read-only Git operations by default.
4. Collect branch, status, recent commit metadata, selected docs, and test results.
5. Run tests only from configured command profiles through the controlled executor.
6. Clearly distinguish current observations from cached memory and conversational claims.
7. Store last-inspected timestamps and evidence references.
8. Git writes remain gated by permissions; push, merge, and destructive operations require approval.
9. Do not index secrets, build artifacts, virtual environments, or excluded paths by default.
10. Project briefings should cite local evidence paths/commit identifiers where possible.

## Forbidden shortcuts
- No assumption that remembered branch/status is current.
- No unrestricted recursive scan of user drives.
- No Git push/merge without approval.
- No automatic modification of project files during inspection.

## Acceptance tests
- Register and inspect approved project.
- Reject out-of-scope path.
- Report current branch/status accurately.
- Excluded files are not indexed.
- Cached data marked stale when not re-inspected.
- Test command uses controlled executor.
- Write Git action is blocked pending approval.

## Handoff
Document project schema, scan exclusions, Git commands, evidence freshness, and test results.