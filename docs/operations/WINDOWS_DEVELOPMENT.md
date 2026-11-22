# Windows Development and Operations Guide

## 1. Platform policy

Orion is developed Windows-first. Documentation and scripts should use PowerShell and Windows-compatible paths. Do not require Bash, WSL, or Unix utilities for ordinary development.

The initial target environment is Windows 10/11 x64. Confirm the actual supported Python and Qt versions during Phase 1 and pin tested dependency ranges.

## 2. Development environment

**Confirmed Phase 1 environment** (Windows 11 x64, 2026-11-22):

| Component | Version |
|---|---|
| Python | 3.12.10 (`py -3.12`) |
| PySide6 | 6.12.0 |
| pytest / pytest-qt | 9.2.0 / 4.5.0 |
| ruff | 0.17.6 |

The project requires `>=3.12,<3.13`. The upper bound is a deliberate Phase 1 policy
statement: 3.12 is the version Orion has been tested on, and widening it later is a
decision to be made deliberately rather than inherited by accident.

The implementation agent must:
1. Inspect installed Python versions.
2. Choose and document one supported Python version.
3. Create a repository-local virtual environment.
4. Install dependencies from the project lock/configuration.
5. Verify PySide6 imports and launches.
6. Run tests and lint tools through the virtual environment's Python executable.

Expected command pattern (adjust only after the project configuration exists):

```powershell
Set-Location <OrionRepository>
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .[dev]
.\.venv\Scripts\python.exe -m pytest
```

Do not assume Python 3.12 without checking: it is now confirmed for Phase 1 (see the
table above). If a later phase changes the supported version, update this guide and
`pyproject.toml` together.

## 3. Configuration and paths

- Resolve application data using Windows known-folder APIs or a configurable data root.
- Do not hard-code a user profile, drive letter, or machine-specific path.
- Keep repository source separate from mutable application data.
- Store logs, SQLite, profiles, datasets, and caches under a documented user data directory.
- Allow a user-configured model/data root.
- Validate managed paths before file operations.

## 4. Process lifecycle

Core should initially run as a normal supervised process. Define start, stop, health, and restart semantics before considering Windows Service registration.

- Use graceful shutdown signals.
- Persist task checkpoints before shutdown when safe.
- Terminate child processes only when Orion owns them and policy permits.
- Avoid killing unrelated processes by name.
- Detect restart loops and enter degraded state.
- Keep UI closure separate from Core shutdown.

## 5. GPU and model environment

Known planning hardware:
- GTX 1660 6 GB for training/evaluation.
- Intended GTX 980 4 GB for resident inference, installation/runtime unverified.

Do not merge VRAM assumptions. The GTX 980 is Maxwell compute capability 5.2; modern packages may not support it. Use runtime discovery and measured validation. Keep the existing GTX 1660 training environment unchanged. Prefer an inference backend proven to support the actual GPU/driver combination; do not assume the training stack is suitable.

Benchmark base and fine-tuned versions of Qwen3-0.6B and Qwen2.5-1.5B-Instruct only after runtime compatibility is confirmed. Measure load time, VRAM, RAM, first-token latency, generation speed, and sustained stability.

## 6. Logging and diagnostics

Use rotating structured logs. Redact secrets and sensitive payloads. Include component, severity, timestamp, correlation ID, and task ID where relevant. Provide a diagnostics export that excludes credentials and private content.

## 7. Backup and recovery

Document:
- Database location.
- Backup procedure.
- Restore procedure.
- Model/profile metadata backup.
- Dataset and adapter backup.
- Log retention.
- Recovery after interrupted upgrade.

Test restore regularly. A backup that has never been restored is not a verified recovery mechanism.

## 8. User-facing run instructions

Once implementation exists, README must contain exact PowerShell commands for:
- Environment setup.
- Launching the UI.
- Starting/stopping Core.
- Running tests.
- Lint/type checks.
- Creating a diagnostic bundle.
- Backing up/restoring data.

Do not publish guessed commands before the corresponding entry points exist.