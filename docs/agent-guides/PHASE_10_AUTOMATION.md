# Agent Guide: Phase 10 — Windows Automation

## Objective
Provide scoped, observable Windows operations through controlled executors.

## Prerequisites
Permission Gateway, task cancellation/timeouts, audit trail, approved workspace model.

## In scope
- Process execution service.
- PowerShell adapter.
- Approved command profiles.
- Workspace/file operation controls.
- Timeouts, cancellation, output limits.
- Exit-code and result capture.
- Audit records and recovery metadata.

## Implementation instructions
1. Define typed execution requests: executable, argument list, working directory, environment allowlist, timeout, output cap, and task/correlation ID.
2. Prefer direct process invocation with argument arrays. If PowerShell is required, use a controlled PowerShell executable and safely encoded script input; never concatenate untrusted strings into a shell command.
3. Restrict file writes to approved roots and canonicalise paths.
4. Guard against traversal and reparse/symlink escapes.
5. Require permission decision immediately before execution.
6. Capture bounded stdout/stderr and exit code; redact sensitive output.
7. Implement cancellation and process-tree ownership carefully. Do not kill unrelated processes.
8. Classify commands by idempotency and retry safety.
9. Use approved command profiles for tests/build tasks.
10. Provide dry-run/preview for risky file operations where practical.

## Forbidden shortcuts
- No unrestricted model-facing terminal.
- No administrator elevation by default.
- No arbitrary package installation without policy.
- No silent file deletion.
- No shell-string interpolation of model content.

## Acceptance tests
- Approved command executes.
- Denied command never starts.
- Working-directory escape blocked.
- Reparse/symlink escape test.
- Timeout terminates owned process tree.
- Cancellation works.
- Output cap and redaction work.
- Non-idempotent command is not blindly retried.

## Handoff
Document process launch semantics, PowerShell handling, path policy, timeout model, and security test results.