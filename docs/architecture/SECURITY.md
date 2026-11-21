# Security and Permission Architecture

## 1. Threat model

Orion processes untrusted natural-language input, model output, tool results, project files, external web content, and optional delegated-agent responses. Any of these may contain incorrect, malicious, or instruction-like content.

Treat model output and external content as data, not trusted policy or executable instructions.

Primary risks:
- Unauthorised file/process/system changes.
- Prompt injection through documents, websites, repositories, or tool output.
- Data leakage to external services.
- Credential exposure in logs, memory, prompts, or datasets.
- Duplicate/destructive actions after retries or crashes.
- Local API misuse by another local process.
- Unsafe model/capability/plugin installation.
- Compromised or incorrect external-agent output.

## 2. Security architecture

All side effects flow through:

`Agent proposal → validated capability request → Permission Gateway → approval if needed → constrained executor → audit record`

No capability may create its own bypass path. No model response can modify policy. If the gateway is unavailable, side effects fail closed.

## 3. Permission model

Permissions are explicit grants scoped by:
- Capability/action.
- Resource/path/application.
- Project/workspace.
- Operation type.
- Optional time window or expiry.
- User-defined constraints.

Autonomy modes (Assist, Supervised, Independent, Restricted) influence approval thresholds but do not create grants.

Initial default posture:
- Read approved project files: allowed within scope.
- Inspect Git: allowed within scope.
- Run approved tests: allowed within configured command profile.
- Create files in approved workspace: configurable/allowed only within scope.
- Modify existing files: configurable.
- Install packages, delete files, kill processes, change system settings, push/merge Git, publish externally: approval by default.
- Credentials and unrelated private content: denied by default.

## 4. Risk assessment

Assess reversibility, impact radius, sensitivity, external visibility, target confidence, verification availability, and recovery options.

Risk classification is advisory input to policy, not a substitute for explicit permission. A low-risk classification cannot override a denied action.

## 5. Approval UX

Show:
- Exact action and target.
- Reason and expected outcome.
- Files/processes/resources affected.
- Reversibility and recovery.
- Data sent externally, if any.
- Scope and duration of approval.

Approval should be specific and time-bounded. Avoid broad “always allow everything” grants. Persistent grants must be explicit, inspectable, and revocable.

## 6. Tool execution isolation

- Use approved working directories.
- Validate paths after canonicalisation.
- Guard against path traversal and unexpected reparse/symlink targets.
- Use argument arrays where possible; avoid shell-string concatenation.
- Apply process timeouts and cancellation.
- Capture exit code and bounded stdout/stderr.
- Limit output size and redact secrets.
- Use retry policies based on idempotency.
- Do not run as administrator by default.
- Do not expose unrestricted PowerShell to the model.

## 7. Prompt injection and untrusted content

External pages, files, repository contents, tool output, and delegated results can contain hostile instructions. They must not alter system policy, reveal secrets, or cause tool execution solely because they contain imperative text.

Keep system policy and user intent separate from retrieved content. Tool outputs are quoted/labelled as observations. Require explicit planning and policy checks before action.

## 8. Secrets

- Never place credentials in ordinary memory.
- Never include secrets in training datasets.
- Redact logs and diagnostics.
- Prefer Windows Credential Manager/DPAPI-backed storage or another OS-protected store.
- Store references/credential IDs, not plaintext secrets, in configuration.
- Do not send secrets to external services unless explicitly authorised for a specific purpose.

## 9. Local API

- Bind loopback only by default.
- Authenticate local sessions/clients.
- Protect administrative operations.
- Validate payload size and schema.
- Use request IDs and rate limits.
- Do not offer arbitrary file read/write or command execution endpoints.
- Consider same-user local process threat and document residual limitations.

## 10. Audit and emergency controls

Record policy decisions, approvals, execution start/end, result, and actor/source. Redact payloads. Provide pause, cancel, stop, and revoke controls. Emergency stop should prevent new side effects and request cancellation of active work; document operations that cannot be interrupted safely.

## 11. Security testing

Test denied actions, gateway outage, expired approval, wrong resource scope, path traversal, symlink/reparse escape, prompt injection in tool output, oversized tool output, secret redaction, duplicate requests, cancellation, and crash recovery. Security tests are release gates, not optional quality improvements.