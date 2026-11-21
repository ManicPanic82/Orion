# ADR-004: Atomic Model Profiles

- **Status:** Accepted
- **Decision:** A user selects one named Model Profile that represents the complete runnable configuration: base model, adapter state, tokenizer, backend, device preference, quantisation, context, and generation settings.

## Context
Users should not have to discover, locate, and manually pair a base model with a compatible adapter. A partial or silently degraded load can produce incorrect behaviour and misleading results.

## Consequences
- Profile manifests are versioned and validated.
- Base and adapter compatibility is checked before loading.
- Required adapter absence or incompatibility fails the profile load.
- Runtime support is validated rather than assumed.
- The Model Manager owns atomic load/unload state and health checks.
- Profile versions reference shared model artifacts rather than duplicating large weights.
- The active profile is not replaced by a training result without explicit user approval.
- Backend-specific adapter support is documented in a compatibility matrix.
- Rollback preserves the previous known-good profile and artifacts.

## Alternatives considered
- Expose base model and adapter as separate user selections: rejected because it creates avoidable pairing errors.
- Hard-code one inference backend: rejected because hardware/runtime support may change.
- Automatically fall back to base-only inference: rejected because it hides a materially different model configuration.

## Risks and follow-up
Adapter attachment and quantisation support vary by backend. The implementation must validate actual runtime behaviour and must not claim universal LoRA attachment support.