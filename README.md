# Orion

**An intelligence that evolves.**

Orion is a local-first, persistent personal AI workstation: one integrated assistant that accepts objectives, plans and performs permitted work, uses modular capabilities, remembers useful context, learns from reviewed experience, and improves through evaluated model updates.

This repository is the source of truth for Orion's product vision, architecture, engineering rules, subsystem contracts, implementation roadmap, and operational guidance.

## Project status

**Stage:** Phases 1–15 have implementation foundations; integration and acceptance validation outstanding
**Application implementation:** Phases 1–15 present as subsystem implementation foundations; integration between subsystems and end-to-end acceptance validation outstanding
**Platform target:** Windows 10/11 x64, with Windows 10 compatibility treated as an explicit constraint  
**Desktop UI:** PySide6  
**Persistent store:** SQLite, with migrations  
**Initial development strategy:** Mock-first, incremental, test-driven  
**Primary interaction:** Text, followed by push-to-talk voice  
**Agent design:** One integrated resident assistant with modular capabilities

Do not interpret planned functionality as implemented functionality. UI and diagnostics must distinguish mock, unavailable, degraded, and operational states.

## Start here

Read these documents in order before changing the architecture or implementing a subsystem:

1. [VISION.md](VISION.md) — product intent, principles, scope, and non-goals.
2. [ARCHITECTURE.md](ARCHITECTURE.md) — system boundaries, runtime topology, and major data flows.
3. [AGENTS.md](AGENTS.md) — mandatory instructions for every coding agent.
4. [Implementation roadmap](docs/implementation/ROADMAP.md) — phases, dependencies, and exit criteria.
5. [Architecture decisions](docs/decisions/README.md) — decisions and their rationale.
6. [Subsystem guides](docs/agent-guides/README.md) — implementation instructions for individual components.

## Running Orion Workstation (Phase 1)

Verified on Windows 11 x64 with Python 3.12.10 and PySide6 6.12.0.

```powershell
Set-Location <OrionRepository>
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m orion
```

Lifecycle behaviour:

- Closing the window minimises Orion to the notification area; the process keeps running (ADR-009).
- Quit from the tray menu, or press `Ctrl+Q` while the window is open.
- Launching Orion again raises the existing window instead of opening a duplicate, so a
  hidden window is always recoverable.
- `--minimised` starts with no visible window; this is what the login entry uses.
- Login autostart is offered once, with *Yes* pre-selected, and can be changed in Settings (ADR-010).

Checks:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe scripts\smoke_launch.py
```

Mutable state lives in `%APPDATA%\Orion\settings.json` (versioned JSON). Phase 1 has
no model runtime, agent, task engine, automation, voice, learning, or network access.
Every piece of assistant state is labelled `MOCK`.

## Repository map

```text
.
├── README.md
├── VISION.md
├── ARCHITECTURE.md
├── AGENTS.md
└── docs/
    ├── architecture/       # contracts, data model, event and security design
    ├── agent-guides/       # task-ready instructions for implementation agents
    ├── decisions/          # architecture decision records
    ├── implementation/     # roadmap, phase gates, testing strategy
    └── operations/         # Windows setup, configuration, diagnostics, recovery
```

The initial documentation tree is intentionally established before application code. Implementation should add code and tests phase by phase rather than scaffolding every future subsystem at once.

## Non-negotiable project principles

- One assistant identity, one central objective manager, and one coherent memory/learning history.
- Capabilities are modular tools and procedures, not separate resident personalities.
- The model proposes actions; deterministic application code enforces permissions.
- Autonomy never grants permission.
- The UI is a client of the background agent, not its process owner.
- Memory and experience survive model replacement.
- Base model and adapter are loaded as one validated Model Profile.
- Training examples are curated; conversations are never indiscriminately used as training data.
- Candidate adapters are evaluated and require user approval before promotion.
- External agents and integrations inherit Orion's permission boundaries.
- No fake telemetry, fake training results, or mock functionality presented as real.
- No destructive, externally visible, or irreversible action without the configured approval.
- Windows-first development and PowerShell-first instructions.

## Initial development target

The first implementation phase is limited to a polished PySide6 Operations Centre shell using clearly labelled mock state. The background service, model runtime, automation, voice, and learning engine are later phases. See the roadmap and Phase 1 agent guide.

## Hardware context

The initial target machine is a Windows workstation with an Intel i7-6700K, 32 GB RAM, a GTX 1660 6 GB, and an intended secondary ASUS ROG STRIX GTX 980 4 GB for resident inference. The GTX 980 installation and runtime compatibility are not yet validated. Do not assume Maxwell support in current PyTorch, bitsandbytes, or other CUDA-dependent packages. Keep the known-working GTX 1660 training environment unchanged during hardware validation.

Hardware details are planning context, not permission to hard-code device assumptions. Runtime discovery and capability reporting must be implemented.

## Contribution and agent workflow

Every change must be scoped to an approved roadmap phase, tested, reviewed as a diff, and documented. Agents must not modify other repositories or projects. Do not merge, force-push, or publish changes without explicit user approval. See [AGENTS.md](AGENTS.md).

## Naming

- Product and assistant identity: **Orion**
- Desktop application: **Orion Workstation**
- Background supervisor/service: **Orion Core**
- Central assistant runtime: **Orion Agent**
- Persistent knowledge subsystem: **Orion Memory**
- Reviewed improvement pipeline: **Orion Evolution**
- Capability framework: **Orion Skills**

The name Orion is independent of the model, inference backend, and hardware used to run it.
