# Orion System Architecture

## 1. Architectural overview

Orion is a local desktop client plus an independently supervised agent runtime. The UI is not the agent. The language model is not the permission system. Tools are not directly callable outside policy enforcement.

Logical topology:

```text
┌─────────────────────────────── Windows workstation ──────────────────────────────┐
│                                                                                  │
│  Orion Workstation (PySide6)                                                     │
│  Pages / dialogs / console / tray client                                         │
│                │ authenticated localhost IPC/API + event stream                  │
│                ▼                                                                 │
│  Orion Core Supervisor                                                           │
│       ├── Resident Agent + Objective/Task Manager                                │
│       ├── Autonomy Policy + Permission Gateway                                   │
│       ├── Capability Registry and Tool Executor                                  │
│       ├── Model Manager ─────────────── Model Host adapter                       │
│       ├── Memory Manager ───────────── SQLite / retrieval index                  │
│       ├── Experience Recorder ───────── Experience store                         │
│       ├── Learning Pipeline ────────── Dataset / Trainer connector / Evaluator   │
│       ├── Voice adapters                                                        │
│       ├── Project Intelligence / Git adapters                                    │
│       └── Main-Agent Delegation adapter                                          │
│                                                                                  │
│  External boundaries: local model runtime, optional web, trainer, main agent     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

This is a logical decomposition, not a demand for dozens of processes. Start with a small number of well-separated Python packages and one supervised service process. Split processes only when isolation, reliability, or resource management justifies it.

## 2. Component responsibilities

### Workstation UI
Displays state and sends user commands. It must not own task execution, database truth, model lifetime, or permission decisions. It can disconnect and reconnect without losing work.

### Core supervisor
Owns service lifecycle, health monitoring, controlled component startup/shutdown, and recovery coordination. Avoid restart storms. Repeated failures must enter a degraded state and notify the user.

### Resident Agent
Interprets objectives, plans, chooses capabilities, reviews observations, and communicates with the user. It may request actions but cannot bypass the Permission Gateway.

### Objective and Task Manager
Persists objectives, task state, steps, dependencies, cancellation, and recovery checkpoints. State transitions are validated and transactional.

### Autonomy and Permission Gateway
Deterministic policy enforcement point for every side-effecting capability. It combines configured grants, risk classification, task context, approval state, and scope. Denials cannot be overridden by model output.

### Capability Engine
Discovers registered tools and procedures, validates schemas, checks capability health, and invokes them through controlled executors. Capability metadata never grants permissions by itself.

### Model Manager and Model Host
Model Manager validates profiles and owns load/unload transitions. Model Host adapters implement backend-specific inference. Keep runtime-specific code behind an interface.

### Memory Manager
Stores user-approved durable facts and preferences with provenance, confidence, validity, and sensitivity. Retrieval is scoped and relevance-based.

### Experience Recorder
Captures task episodes, tool interactions, outcomes, and corrections according to explicit capture settings. It is separate from personal memory.

### Learning Engine
Selects and curates experiences, builds versioned datasets, integrates with the external trainer, evaluates candidate adapters, and manages user-approved promotion.

### Voice subsystem
Converts speech to/from the same command/message interface used by text. Voice provider failure must not impair text operation.

### Project Intelligence
Maintains a project registry and gathers current evidence from local files, Git, and tests. Cached project knowledge must be labelled as cached, not current.

### Integration adapters
Connect to external research, main-agent, and training systems. Each adapter is replaceable, permission-scoped, observable, and mockable.

## 3. Dependency direction

Use dependency inversion. Domain/core packages define protocols and data contracts. Infrastructure packages implement them. UI depends on application-facing API clients, not database internals.

Preferred direction:

- UI → local API client / view models.
- API → application services.
- Application services → domain interfaces.
- Infrastructure → implements domain interfaces.
- Domain must not import UI, Qt, vendor SDKs, or concrete runtime packages.

Avoid circular imports and global service singletons. Use explicit composition at startup and dependency injection.

## 4. Runtime boundaries

Start with Orion Workstation and Orion Core as separate processes. The model host may initially be a library embedded in Core or a separate process depending on backend stability. Keep its protocol abstract so it can be isolated later.

The Core API must bind to loopback only by default. Use an authenticated local session or equivalent OS-protected mechanism. Do not expose a general-purpose shell endpoint.

Use request/response operations for commands and a structured event stream for updates. Events are notifications; database records remain authoritative.

## 5. Data flow: objective execution

1. UI submits an objective with a client-generated request ID.
2. API authenticates and validates the request.
3. Agent creates an objective and task record.
4. Planner proposes steps and required capabilities.
5. Policy gateway evaluates each side-effecting action.
6. Approval is requested if required.
7. Capability executor validates arguments and runs with timeout/cancellation.
8. Observations and outputs are recorded.
9. Agent verifies the result against the objective.
10. Task state and final response are persisted.
11. Experience recorder stores an eligible episode subject to capture policy.

Never treat a tool's zero exit code or HTTP success as proof that the overall objective succeeded.

## 6. Data flow: model profile loading

1. Read and schema-validate profile manifest.
2. Resolve base model, adapter, tokenizer, backend, and revision.
3. Verify paths, checksums where available, compatibility, and backend support.
4. Check memory/device budget.
5. Load base model.
6. Attach adapter using the selected backend's supported mechanism.
7. Apply generation/context settings.
8. Run health-check inference.
9. Publish READY only after all required checks pass.
10. On failure, clean up partial allocations and report a typed error.

A profile requiring an adapter must never silently fall back to base-only inference.

## 7. Data flow: learning

Experience → eligibility filter → privacy/quality review → dataset builder → immutable dataset version → training connector → candidate adapter → held-out evaluation → user approval → new Model Profile version.

The active profile remains unchanged until explicit promotion. Retain rollback metadata and previous artifacts.

## 8. Persistence

SQLite is the initial authoritative store. Use migrations, foreign keys, transactions, indexes, and repository interfaces. Keep large weights, datasets, recordings, and logs outside SQLite; store metadata and controlled paths.

Task state, approval state, profile state, and learning promotion state must be persisted transactionally. Use JSONL only for append-oriented export/event archives, not as a second conflicting source of truth.

## 9. Failure and degraded operation

- UI unavailable: Core continues and records events.
- Model unavailable: memory/project inspection and non-model services may remain available; report degraded capability.
- Voice unavailable: text remains available.
- Main-agent unavailable: local tasks continue; delegation is marked unavailable.
- Trainer unavailable: curated datasets remain exportable and queued.
- Database unavailable: stop new stateful execution safely; do not pretend work was recorded.
- Permission service unavailable: fail closed for side-effecting actions.
- Event stream unavailable: UI reconnects and reloads authoritative state.

## 10. Design constraints

- Windows-first, PowerShell-first.
- Python and PySide6 for the initial desktop implementation.
- Mock-first for external systems.
- Typed request/response models and versioned schemas.
- Structured logs with redaction.
- Timeouts and cancellation for external operations.
- Idempotency keys for retryable API operations.
- No implicit retries of destructive/non-idempotent actions.
- No secrets in prompts, logs, memory, or datasets.
- No hard-coded GPU/runtime assumptions.
- No fake telemetry or simulated success presented as real.

## 11. Implementation rule

Do not create all planned modules as empty placeholders. Implement a small vertical slice in each roadmap phase, with tests and real UI state transitions. Keep future interfaces documented but defer unused complexity.