# Instructions for All Orion Coding Agents

These instructions apply to every coding agent, automation, and human contributor working in this repository. They are mandatory and take precedence over inferred conventions.

## 1. Before doing work

1. Read `README.md`, `VISION.md`, and `ARCHITECTURE.md`.
2. Read the current phase in `docs/implementation/ROADMAP.md`.
3. Read the relevant subsystem guide under `docs/agent-guides/`.
4. Inspect the repository state, current branch, working tree, and existing tests.
5. Identify the exact requested scope and acceptance criteria.
6. Ask before expanding scope or changing an approved architectural decision.

Do not assume prior chat context is available. This repository is the project source of truth.

## 2. Project boundaries

- Work only in this Orion repository unless the user explicitly authorises another location.
- Do not modify Simple HF Trainer or any other existing project.
- Integrate external projects through documented adapters/contracts.
- Do not copy secrets, private datasets, credentials, or unrelated project files into Orion.
- Do not claim external integrations work until they have been tested.

## 3. Git safety

- Inspect branch and working tree before changes.
- Preserve unrelated user modifications.
- Never use destructive cleanup to make the working tree appear clean.
- Do not force-push.
- Do not merge branches.
- Do not push or publish commits unless the user explicitly authorises it.
- Do not rewrite shared history.
- Do not change branch protection or repository settings.
- Do not commit generated model weights, datasets, logs, caches, virtual environments, or credentials.
- Before a commit, show/review the diff and run relevant tests. Commit only when requested or clearly authorised.

## 4. Implementation scope

- Implement only the current approved phase and its necessary prerequisites.
- Do not build speculative future functionality.
- Do not create large sets of empty placeholder modules.
- Do not replace an existing implementation without understanding its behaviour and tests.
- Keep changes small, cohesive, and reversible.
- Update documentation when interfaces, behaviour, configuration, or acceptance criteria change.
- Record significant architectural changes as a decision record.

## 5. Architecture rules

- One resident assistant identity and one central objective/task system.
- Capabilities are modular tools/procedures, not separate resident personalities.
- UI is a client; it does not own background task lifetime.
- The model proposes; deterministic application code authorises and executes.
- Every side-effecting capability must pass through the Permission Gateway.
- Autonomy level never grants a missing permission.
- Memory, experiences, and training datasets are distinct concepts.
- Model Profiles represent a validated base model + optional/required adapter + runtime configuration.
- A required adapter must not be silently omitted.
- Keep model runtime, UI, task engine, memory, and external adapters behind explicit interfaces.
- Use dependency injection; avoid global mutable singletons.
- Use structured, validated schemas and typed errors.
- Use migrations for persistent schema changes.
- Treat events as notifications, not the source of truth.

## 6. Safety and privacy

- Default-deny access to secrets and unrelated private content.
- Never log credentials, access tokens, passwords, or private prompt payloads unnecessarily.
- Redact sensitive values before logging or dataset export.
- Do not capture keystrokes, whole-desktop activity, or private messages by default.
- Respect capture pause, project exclusions, and memory deletion/exclusion.
- Never let model-generated text change permission policy.
- Restrict file writes to approved workspaces.
- Use timeouts, cancellation, and bounded retries.
- Destructive, irreversible, external, or security-sensitive actions require configured approval.
- Fail closed if the permission system is unavailable.
- Never blindly replay a non-idempotent action after a crash.

## 7. Windows development conventions

- Target Windows x64 first.
- Provide PowerShell commands, not Unix-only shell instructions.
- Use pathlib for filesystem paths.
- Use explicit executable paths where practical.
- Do not assume WSL, Bash, grep, sed, or GNU utilities exist.
- Keep environment-specific paths in configuration, never hard-code a developer's home directory.
- Test process creation, cancellation, and shutdown on Windows.
- Do not alter the user's existing Python/CUDA environments without explicit approval.

## 8. Mock discipline

Mocks must be explicit and visibly labelled. A mock model, mock telemetry provider, mock trainer, mock voice engine, or mock main-agent adapter must never report itself as a real connected component.

Keep mock and real implementations behind the same contract. Tests should verify that unavailable providers fail clearly.

## 9. Quality gates

For each change:

1. Add or update unit tests.
2. Add integration tests when component boundaries change.
3. Run relevant tests.
4. Run lint/type checks configured by the project.
5. Inspect the final diff.
6. Check for accidental secrets, local paths, generated files, and unrelated changes.
7. Update docs and examples.
8. Report exact commands and actual results.

Never claim a test, benchmark, or runtime check passed unless it was executed and its result observed.

## 10. Completion report

Every agent handoff must state:

- Scope completed.
- Files created/modified.
- Important design choices.
- Tests and exact results.
- Commands to run locally.
- Known limitations and unimplemented items.
- Any migration/configuration impact.
- Risks or decisions requiring user input.
- Confirmation that no unrelated project was modified.

## 11. Hardware and model constraints

The intended resident inference GPU is an ASUS GTX 980 4 GB, not yet validated. The GTX 1660 6 GB is the existing training/evaluation GPU. Do not assume VRAM pooling. Do not assume modern PyTorch, bitsandbytes, Unsloth, or CUDA packages support Maxwell compute capability 5.2. Preserve the known-working GTX 1660 environment. Benchmark and document actual support before claiming it.

## 12. User authority

The user owns the repository, hardware, data, and final product decisions. Agents may recommend improvements, but must not silently change the product vision, permission policy, repository boundaries, or approved architecture.