# ADR-001: One Integrated Resident Agent

- **Status:** Accepted
- **Decision:** Orion has one central resident assistant identity, objective manager, memory, and learning history. Coding, research, gaming, automation, and other domains are modular capabilities, not separate resident personalities.

## Context
The product must feel coherent across different tasks and retain one identity and accumulated knowledge.

## Consequences
- The agent core owns objective interpretation and orchestration.
- Capabilities expose contracts and tools.
- Internal modularity is encouraged; separate competing agent identities are not.
- The main external AI is a delegation/reasoning resource, not another Orion personality.
- Capability-specific model profiles may exist as runtime configurations without fragmenting identity.