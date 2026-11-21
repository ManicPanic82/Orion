# ADR-005: Separate Memory, Experience, and Training

- **Status:** Accepted
- **Decision:** Personal memory, task experiences, and model-training datasets are separate layers with explicit promotion between them.

## Context
Personal facts need immediate retrieval, while model training requires curated examples. Mixing them risks privacy leakage, stale facts, and low-quality training.

## Consequences
- Memory remains model-independent.
- Experiences record actions and outcomes.
- Only reviewed, privacy-screened experiences become dataset examples.
- Dataset provenance is retained.
- Training and promotion are deliberate, evaluated operations.