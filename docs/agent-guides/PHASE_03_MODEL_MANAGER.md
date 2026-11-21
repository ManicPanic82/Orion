# Agent Guide: Phase 3 — Model Manager and Model Profiles

## Objective
Provide one simple profile selection/load workflow while validating the complete model configuration underneath.

## Prerequisites
Core service and persistence foundations. Read CONTRACTS.md and hardware guide.

## In scope
- Versioned Model Profile schema and manifest validation.
- Profile repository and management UI.
- Model-host protocol.
- Mock model host.
- Load/unload state machine.
- Base/adapter/tokenizer/runtime compatibility validation.
- Health-check inference and typed failures.
- Runtime/device capability reporting.

## Implementation instructions
1. Define profile schema with profile ID/version, base model identity/revision/path, adapter state/path/type/revision, tokenizer, backend, device preference, quantisation, context and generation limits.
2. Distinguish explicitly between no adapter, optional adapter, and required adapter.
3. Validate paths are inside approved model roots or explicitly approved locations.
4. Validate backend capability before allocating resources.
5. Check base and adapter compatibility; do not infer compatibility from filenames alone.
6. Load base, attach adapter using the backend's documented mechanism, apply settings, and run a health prompt.
7. Publish READY only after all required steps succeed.
8. On partial failure, unload/release resources and retain a typed diagnostic.
9. Switching profiles must have explicit unload/load transitions and safe failure behaviour.
10. Do not copy large base weights when duplicating profiles; reference immutable model artifacts.
11. Mock host must implement the same interface and display MOCK state.

## Forbidden shortcuts
- Never silently load base-only when a required adapter is missing.
- Do not assume every backend supports live LoRA attachment.
- Do not hard-code GTX 980 support.
- Do not modify the user's existing training environment.

## Acceptance tests
- Valid mock profile loads and generates.
- Missing required adapter fails.
- Incompatible base/adapter fails.
- Unsupported backend feature fails clearly.
- Partial load cleans up.
- Profile switching works.
- Health failure prevents READY.
- Profile manifest import/export round-trips.

## Handoff
Provide schema example, compatibility rules, runtime support matrix, and tests. Mark all real hardware/runtime support as unverified until tested.