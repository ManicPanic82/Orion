# Agent Guide: Phase 4 — Resident Agent and Task Engine

## Objective
Accept user objectives, create durable tasks, plan work, invoke mock capabilities, verify outcomes, and report progress.

## Prerequisites
Core API and event model, persistence, mock capability contract.

## In scope
- Objective intake.
- Agent orchestration interface.
- Planner abstraction.
- Task/task-step state machine.
- Capability registry.
- Mock capability executor.
- Progress events and cancellation.
- Result verification model.
- Durable task history and safe recovery metadata.

## Implementation instructions
1. Separate objective from task and task step. One objective may create multiple tasks.
2. Define allowed state transitions in one tested domain component.
3. Store task and step transitions transactionally.
4. Build planner output as structured, validated steps, not free-form executable code.
5. Resolve requested tools only from registered capabilities.
6. Route every side-effecting capability request through the permission interface even while using mocks.
7. Record attempted action, observed tool result, and verified objective outcome separately.
8. Support cancellation tokens and per-step timeouts.
9. Classify each operation by idempotency. Never automatically retry non-idempotent steps after ambiguous failure.
10. Recover by inspecting last durable checkpoint; ask user when safe resumption cannot be established.
11. Keep model calls behind an agent/model interface; tests use deterministic fake responses.

## Forbidden shortcuts
- No unrestricted shell tool.
- No direct OS operations from planner/model code.
- No treating tool success as task success.
- No retry loop without budget.
- No hidden task execution outside persisted task manager.

## Acceptance tests
- Objective creates task.
- Valid state transitions persist.
- Invalid transitions rejected.
- Mock multi-step task runs and reports progress.
- Cancellation stops pending work.
- Failure and partial success are represented.
- Duplicate request IDs do not create duplicate tasks.
- Restart recovery resumes only safe/idempotent steps.

## Handoff
Document state machine, planner schema, capability invocation path, retry rules, and acceptance results.