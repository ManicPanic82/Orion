# Configuration Policy

## 1. Principles

Configuration is user-owned, validated, versioned, and separate from source code. Defaults must be safe. Environment-specific values must not be hard-coded.

## 2. Configuration categories

- Application/UI preferences.
- Core service settings.
- API binding/session settings.
- Data and model roots.
- Model runtime/profile defaults.
- Autonomy and permission policy.
- Capture/privacy settings.
- Voice providers and devices.
- Project registrations.
- External integration endpoints and credential references.
- Logging and diagnostics.

## 3. Precedence

Define and document a deterministic precedence order when implemented. Recommended order:
1. Compiled safe defaults.
2. Application configuration file.
3. User settings database.
4. Explicit per-run overrides for non-security-sensitive values.

Security-sensitive permissions must not be widened by environment variables or model-generated configuration. Credentials are stored in OS-protected credential storage, not plain config files.

## 4. Validation

- Validate schema and types at startup.
- Reject unknown security-sensitive keys.
- Validate paths and endpoint schemes.
- Validate numeric ranges and resource budgets.
- Report invalid settings with actionable messages.
- Do not silently replace invalid permission settings with permissive defaults.

## 5. Secrets

Store only credential references in ordinary configuration. Use Windows Credential Manager/DPAPI-backed storage or another reviewed secure mechanism. Never commit local config containing secrets.

## 6. Portability

Use configurable data roots and relative references where practical. Do not embed the developer's username, drive letter, home path, GPU index, or local model path in tracked files.

## 7. Migration

Version user configuration. Migrations must preserve user values, create a backup before risky changes, and report any values that cannot be migrated safely.