# Orion Product Vision

## 1. Purpose

Orion is a persistent, local-first personal AI workstation. It is intended to become one integrated assistant that can understand user objectives, select suitable capabilities, perform permitted work, retain useful knowledge, and improve through carefully reviewed experience.

The user should express the outcome in ordinary language. Orion should determine a sensible plan, choose tools, execute within explicit boundaries, verify results, and explain what happened.

Examples include coding assistance, project maintenance, research, Windows workflow automation, gaming experiments, and delegation to a stronger external/main AI agent.

## 2. Product promise

**One assistant. One evolving intelligence. A growing set of capabilities.**

The assistant identity, memory, task history, and permission model remain coherent even when the underlying model, runtime, GPU, or capability implementation changes.

## 3. Confirmed product decisions

- One central resident agent, not multiple specialist personalities.
- Adaptive autonomy, bounded by explicit permissions.
- Text interaction first; push-to-talk voice in a later phase; wake-word listening only as an explicitly enabled extension.
- Integrated capabilities for coding, research, desktop automation, gaming, project intelligence, and delegation.
- Model-independent persistent memory.
- Separate experience capture, curation, dataset generation, training, evaluation, and promotion.
- A Model Profile loads a compatible base model and adapter as one atomic user-facing unit.
- A PySide6 dark Operations Centre communicates with an independently running background process.
- Mock-first development for external runtimes and integrations.

## 4. Operating principles

### User-directed objectives
The user sets goals and boundaries. Orion proposes and performs the work needed to reach them. A goal is not unlimited permission.

### Adaptive autonomy
Orion can act independently on low-risk permitted tasks, seek approval for consequential actions, and stop when a hard restriction applies. Confidence affects whether Orion asks for clarification; it never overrides a permission denial.

### Local-first, not local-only
Core memory, task state, model hosting, and local automation should work offline where practical. Network research and external delegation are optional capabilities and must be visible.

### Persistent but controllable
Closing the dashboard does not stop Orion Core. The user can pause, interrupt, cancel, stop, or disable automation. Persistent operation must never mean invisible operation.

### Learn carefully
Immediate memory is not model training. Experience records are not automatically positive examples. Only reviewed, privacy-screened, traceable examples may enter datasets. Candidate models must pass evaluation and receive user approval before promotion.

### Evidence over claims
Orion must distinguish a proposed action, attempted action, successful tool response, and verified outcome. Status panels and reports must be grounded in actual state.

## 5. Initial scope

The first release is a stable Windows desktop shell and background agent foundation, followed by model management, task execution, permissions, memory, experience capture, and learning integration.

Gaming and visual interaction are important long-term capabilities but must not distort the initial architecture. They should use the same objective/task/permission/experience foundations with specialized observation and action adapters.

## 6. Explicit non-goals

- An unrestricted shell exposed directly to a language model.
- Automatic execution of every suggested action.
- Automatic training on entire conversations.
- Live weight updates during ordinary conversations.
- Automatic promotion of an untested model.
- Separate resident agent identities for every capability.
- A hard dependency on one model family, GPU, inference runtime, voice engine, or main-agent product.
- Modifying the existing Simple HF Trainer or other projects as part of Orion work without explicit approval.
- Claiming hardware support before it has been tested.

## 7. Long-term success

Orion should run independently of its dashboard, accept text and voice objectives, manage multi-step tasks, use approved tools, assist with projects and games, delegate work, preserve useful memories and procedures, learn from corrections, create reviewed training data, and safely improve its model profiles over time.

The measure of success is reliable completion of useful objectives with transparent control, not the number of tools or autonomous actions.