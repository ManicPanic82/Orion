# Agent Guide: Phase 8 — Orion Evolution Learning Pipeline

## Objective
Convert reviewed experiences into reproducible datasets, submit training jobs through a replaceable connector, evaluate candidates, and require user approval for promotion.

## Prerequisites
Experience review, dataset schema, Model Profile versioning, external trainer contract.

## In scope
- Eligibility selector and curation UI.
- Privacy/quality filters.
- Dataset builders for supported conversational/tool-use formats.
- Immutable dataset versioning and provenance.
- Mock trainer connector then real Simple HF Trainer adapter.
- Training run tracking.
- Held-out evaluation and candidate promotion workflow.

## Implementation instructions
1. Define dataset formats based on the actual trainer's supported schemas; inspect its public interface before implementing a real connector.
2. Build deterministic conversion with schema validation and reproducible manifests.
3. Preserve source experience IDs, review decisions, builder version, dataset hash, and split assignment.
4. Prevent train/evaluation leakage; keep held-out evaluation data separate.
5. Remove secrets, excluded data, duplicates, and low-quality/ambiguous examples.
6. Treat corrections as potential preference pairs only after review.
7. Keep the trainer integration outside the core learning domain behind an adapter.
8. Record exact base revision, adapter config, trainer version, seed/config, and output artifacts.
9. Evaluate candidate against fixed benchmark and current active baseline.
10. Promotion is a separate user-approved operation; preserve rollback profile and artifact references.
11. Never change active profile as a side effect of training completion.

## Forbidden shortcuts
- No training on all memory or all conversations.
- No unreviewed examples.
- No fabricated training metrics.
- No active adapter overwrite.
- No trainer-specific code leaking into domain model.

## Acceptance tests
- Eligible reviewed episodes build valid JSONL.
- Excluded/sensitive examples are omitted.
- Provenance manifest validates.
- Dataset version is immutable.
- Mock trainer lifecycle works.
- Candidate evaluation records actual metrics.
- Promotion denied without explicit approval.
- Rollback restores previous profile metadata.

## Handoff
Provide format examples, trainer contract, dataset audit report, evaluation criteria, and evidence of promotion gate.