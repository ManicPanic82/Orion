# Core Contracts and Invariants

This document defines the first stable boundaries between Orion subsystems. Concrete Python protocols and schemas are introduced in the phase that implements them. Do not prematurely freeze vendor-specific details.

## 1. Common contract requirements

Every request/response crossing a subsystem boundary must have:
- A schema version.
- A unique request or correlation ID.
- Explicit success or typed error outcome.
- Validated input.
- Bounded execution time where applicable.
- Cancellation semantics for long-running work.
- Structured, redacted diagnostics.

Never pass arbitrary Python objects, Qt widgets, open database connections, or vendor SDK objects across boundaries.

## 2. Agent contract

Input: user objective, conversation/session context, relevant retrieved memory, available capability descriptions, and policy decision context.

Output: user-facing response and/or a structured plan containing proposed steps and capability requests.

The agent may not:
- Directly execute OS commands.
- Modify permission policy.
- Mark an unverified outcome successful.
- Promote model artifacts.
- Access unscoped files or private content.

The agent must expose uncertainty and ask for clarification when target identity or objective is ambiguous.

## 3. Task contract

A task has a stable ID, objective, status, timestamps, parent/child relation, plan/steps, current checkpoint, result, and audit references.

Task transitions are validated by application code. Each step records:
- Step ID and sequence.
- Capability ID/version.
- Input reference or redacted summary.
- Permission decision/approval reference.
- Start/end timestamps.
- Outcome and output reference.
- Retry/idempotency classification.

Do not persist secrets or unnecessary full payloads.

## 4. Capability contract

A capability declares:
- Stable capability ID and version.
- Human-readable purpose.
- Input/output schema.
- Required permission scopes.
- Risk category.
- Timeout and cancellation support.
- Idempotency classification.
- Health/availability.
- Audit and experience-capture policy.

Invocation must be performed by the application executor, not by model-generated imports or arbitrary code. The executor validates input, checks capability availability, asks the Permission Gateway, enforces timeout/cancellation, captures output, and records the result.

## 5. Permission decision contract

A decision must be one of:
- ALLOW
- DENY
- REQUIRE_APPROVAL

Decision evidence includes policy version, capability/action, resource scope, risk, autonomy mode, matching grant(s), approval reference, and rationale code.

The gateway is deterministic. Natural-language explanations may be generated after the decision, but cannot change it.

Default is DENY when policy cannot be evaluated.

## 6. Model host contract

Minimum operations:
- discover/describe runtime
- load validated runtime configuration
- unload
- generate
- cancel generation
- health check
- report runtime/device/resource information when supported

Model Manager owns profile validation and lifecycle. Backend adapters own implementation details. Generation requests must support cancellation and bounded output/context limits.

A Model Profile is READY only after base, adapter (if required), tokenizer/configuration, runtime, and health check all succeed.

## 7. Memory contract

Memory records are user-context records, not raw conversation archives. They require category, content, source/provenance, created/verified times, confidence, validity, sensitivity, project scope, and capture/review state.

Retrieval must respect exclusions and sensitivity policy. Deletion/exclusion must affect normal retrieval and future dataset eligibility. Training artifacts already exported require a documented deletion/rebuild process where feasible.

## 8. Experience contract

An experience is an episode linked to an objective/task and includes context, plan, actions, observations, outcome, feedback, provenance, and review state.

Outcome classes: SUCCESS, PARTIAL, FAILURE, CORRECTED, ABANDONED, INCONCLUSIVE, NOT_ELIGIBLE.

An experience cannot become a positive training example merely because execution ended. Eligibility requires quality and privacy review.

## 9. Dataset contract

A dataset version is immutable after creation. It records:
- Dataset ID/version.
- Format/schema.
- Builder version.
- Source experience IDs.
- Review approvals.
- Exclusions/redactions.
- Creation timestamp.
- Checksums.
- Split strategy.
- Licence/source metadata for imported public data.

Never include secrets or personal data without explicit review and permission. Keep held-out evaluation data separate from training data.

## 10. Model Profile contract

A profile binds base model identity/revision, adapter identity/revision or explicit no-adapter state, tokenizer, backend, runtime settings, device preference, quantisation, context limits, and compatibility metadata.

A profile must declare whether an adapter is required. If required and unavailable/incompatible, loading fails. Do not silently substitute a different base or adapter.

## 11. Event contract

Events are append-oriented notifications with event ID, timestamp, type, schema version, correlation/task ID, severity, source component, and redacted payload.

Consumers must tolerate duplicates and reconnect gaps. After reconnect, clients query authoritative state and use events for live updates. Event delivery is not a transaction guarantee.

## 12. API contract

The local API is loopback-only by default. It uses explicit routes/operations, schema validation, authentication/session controls, rate/size limits, and API versioning.

No endpoint may provide unrestricted command execution, arbitrary file access, policy mutation, or unauthenticated administrative control.

## 13. External adapter contract

Each external integration:
- Has a replaceable interface.
- Has mock and real implementations.
- Declares connection/health state.
- Has explicit permissions and data-sharing scope.
- Uses timeouts and cancellation where possible.
- Redacts secrets.
- Returns typed errors.
- Does not widen Orion's authority.

## 14. Cross-cutting invariants

1. Autonomy never grants permission.
2. Permission failure blocks side effects.
3. Model output is untrusted input.
4. UI closure does not terminate Core.
5. Model replacement does not erase memory.
6. Failed experiences are not positive demonstrations.
7. Candidate model promotion requires user approval.
8. Unverified work is not reported as verified.
9. No blind retry of non-idempotent operations.
10. Mock status is never represented as real status.