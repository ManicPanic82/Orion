# ADR-008: Windows-First Development

- **Status:** Accepted
- **Decision:** Initial development and operations target Windows x64, with PowerShell-first documentation.

## Context
The target machine and workflows are Windows-based.

## Consequences
- Avoid Unix-only setup assumptions.
- Use pathlib and configurable Windows paths.
- Test process lifecycle and automation on Windows.
- Preserve the existing training environment.
- Cross-platform support is not promised until separately designed and tested.