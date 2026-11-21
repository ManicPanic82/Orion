# Agent Guide: Phase 12 — Main-Agent Delegation

## Objective
Allow Orion to delegate appropriate work to the user's existing main AI agent without creating a second resident personality or widening permissions.

## Prerequisites
Task engine, external adapter contract, permission gateway, project scope model.

## In scope
- Delegation provider interface.
- Mock provider.
- Structured task package.
- Submission/progress/result lifecycle.
- Result verification.
- Parent/child task linkage.
- Provider health and failure handling.

## Implementation instructions
1. Do not assume the external agent's API. Inspect its supported interface only when this phase is authorised.
2. Define provider-neutral task payload: objective, scope, constraints, allowed workspace, expected artifacts, acceptance criteria, and permission context.
3. Remove secrets and unrelated user context before sending.
4. Require permission for external data transfer.
5. Bind delegated work to the same project/workspace restrictions.
6. Treat external response and files as untrusted observations.
7. Inspect diffs, run approved tests, and verify outputs before declaring completion.
8. Track provider task ID, timestamps, status, errors, and returned artifacts.
9. Handle provider unavailable, timeout, partial result, and cancellation.
10. The external agent cannot approve its own actions or grant itself more permissions.

## Forbidden shortcuts
- No assumed endpoint or protocol.
- No unrestricted repository access.
- No automatic acceptance of returned code.
- No secrets in handoff payload.
- No delegated permission escalation.

## Acceptance tests
- Mock delegation lifecycle works.
- Parent/child task linkage persists.
- External transfer approval is enforced.
- Provider timeout/failure is handled.
- Returned artifact is inspected.
- Delegated agent cannot bypass Orion's permission gateway.

## Handoff
Document provider protocol, payload schema, data-sharing controls, and result-verification evidence.