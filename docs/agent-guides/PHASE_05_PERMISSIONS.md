# Agent Guide: Phase 5 — Adaptive Autonomy and Permission Gateway

## Objective
Implement deterministic, auditable enforcement of permissions and approval requirements.

## Prerequisites
Capability invocation contract and task engine. Read SECURITY.md.

## In scope
- Autonomy modes: Assist, Supervised, Independent, Restricted.
- Permission grants and resource scopes.
- Risk classifier.
- Permission decision engine.
- Approval request lifecycle and UI.
- Audit trail.
- Pause/cancel/stop/revoke controls.

## Implementation instructions
1. Model autonomy mode separately from permission grants.
2. Define a deterministic policy function taking actor, capability/action, resource, scope, risk, mode, and approval evidence.
3. Return ALLOW, DENY, or REQUIRE_APPROVAL with policy version and rationale code.
4. Default to DENY if policy cannot be evaluated.
5. Require capability executor to obtain a fresh decision immediately before side effect.
6. Bind approval to exact action, arguments/resource scope, task, expiry, and one-time/persistent status.
7. Do not let the model create or edit policy.
8. Make persistent grants narrow, inspectable, and revocable.
9. Add emergency pause to prevent new side effects and cancellation to running work where safe.
10. Audit policy decisions and action outcomes with redacted data.

## Forbidden shortcuts
- No “Independent means allow all”.
- No broad approval token reusable for unrelated actions.
- No bypass for trusted/learned procedures.
- No fail-open behaviour.
- No policy stored only in model prompt.

## Acceptance tests
- All four autonomy modes behave as specified.
- Missing grant remains denied in Independent mode.
- Expired/wrong-scope approval rejected.
- Gateway outage blocks side effect.
- Policy version and rationale are auditable.
- Revocation takes effect.
- Emergency pause blocks new actions.
- Prompt injection cannot alter policy.

## Handoff
Provide policy table, decision examples, threat tests, and documented approval UX.