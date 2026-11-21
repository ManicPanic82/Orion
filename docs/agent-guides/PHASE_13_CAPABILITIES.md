# Agent Guide: Phase 13 — Capability Expansion and Adaptive Workflows

## Objective
Enable Orion to build a growing library of reusable, versioned procedures and bounded user-defined goals.

## Prerequisites
Stable capability registry, permissions, task engine, memory and experience subsystems.

## In scope
- Capability discovery and health.
- Procedure schema/versioning.
- Procedure proposal and review.
- User-defined goals and success criteria.
- Scheduling/triggers.
- Daily briefing.
- Quiet Intelligence mode.
- Task/resource budgets.

## Implementation instructions
1. A procedure is a structured workflow referencing registered capabilities, not arbitrary executable code.
2. Include purpose, preconditions, inputs, steps, permissions, expected outputs, verification, rollback/recovery, and version.
3. Procedures require review before being enabled for autonomous execution.
4. Capability availability is checked at execution time.
5. Goals must specify scope, success criteria, schedule/trigger, budgets, and stop conditions.
6. A goal never implies unlimited permissions.
7. Add budgets for runtime, tool calls, retries, tokens, delegation, and resource use.
8. Quiet Intelligence mode defers low-priority notifications but never suppresses configured critical alerts.
9. Daily briefing uses verified task/project events and clearly labels suggestions.
10. User can inspect, disable, edit, and revoke procedures/goals.

## Forbidden shortcuts
- No self-installing arbitrary code.
- No procedure can bypass current permission checks.
- No unbounded loops or unlimited schedules.
- No fabricated daily briefing content.

## Acceptance tests
- Procedure validation and versioning.
- Disabled capability blocks procedure.
- Permission changes affect saved procedure.
- Goal budget stops execution.
- Schedule respects quiet hours.
- User pause/disable takes effect.
- Briefing data traces to real events.

## Handoff
Document procedure schema, scheduling model, budget enforcement, and user controls.