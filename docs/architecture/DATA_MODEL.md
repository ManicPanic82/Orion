# Initial Persistent Data Model

## 1. Storage strategy

SQLite is the authoritative store for Orion's structured state. Use migrations from the first implementation phase that requires persistence. Store large model weights, adapters, datasets, recordings, and logs as files; database rows hold metadata and controlled references.

All timestamps use UTC ISO-8601 strings or a consistently chosen integer epoch representation. Choose one representation and document it in code. IDs should be opaque stable identifiers (UUID/ULID acceptable); do not expose sequential database IDs as public API identity.

## 2. Initial entities

### settings
Key/value or typed settings records with schema version, scope, updated timestamp, and sensitivity classification. Secrets do not belong here unless protected by OS credential storage and referenced indirectly.

### projects
Project ID, display name, local root, repository URL, purpose, technology tags, configured commands, access scope, status, created/updated/last-inspected timestamps.

### objectives
Objective ID, user/session origin, request text or protected reference, status, created/updated timestamps, success criteria, privacy/capture policy.

### tasks
Task ID, objective ID, parent task ID, status, priority, autonomy context, current checkpoint, created/started/finished timestamps, result summary, failure code.

### task_steps
Step ID, task ID, sequence, capability ID/version, status, idempotency class, input/output references, permission decision ID, start/end timestamps, attempt count.

### events
Event ID, type, schema version, severity, source, correlation/task ID, timestamp, redacted structured payload.

### permission_policies
Policy ID/version, scope, action/resource matcher, decision rule, enabled state, timestamps. Policy editing is a privileged user operation.

### approval_requests
Approval ID, task/step, action summary, resource scope, risk, rationale, expiry, status, approver, decision timestamp.

### model_profiles
Profile ID, name, current version ID, description, created/updated timestamps.

### model_profile_versions
Version ID, profile ID, manifest JSON, checksum, compatibility status, created timestamp, source/candidate references.

### memories
Memory ID, category, content or protected content reference, provenance, project scope, confidence, sensitivity, validity dates, review state, created/verified timestamps, superseded/deleted state.

### experiences
Experience ID, task/objective references, episode metadata, outcome class, provenance, capture policy, privacy state, quality state, created timestamp.

### experience_reviews
Review ID, experience ID, reviewer decision, notes, redaction status, dataset eligibility, timestamp.

### datasets
Dataset ID/version, format, builder version, path, checksum, split metadata, source IDs manifest, review state, created timestamp.

### training_runs
Run ID, dataset version, base model revision, trainer adapter/version, config reference, status, output path, metrics reference, timestamps.

### model_evaluations
Evaluation ID, candidate profile/version, benchmark version, results, comparison baseline, pass/fail decision, evaluator version, timestamp.

### capabilities
Capability ID/version, manifest, availability, health, enabled state, last check.

### procedures
Procedure ID/version, purpose, preconditions, steps, capability dependencies, permission requirements, verification criteria, review state.

### automations
Automation ID, trigger/schedule, goal, scope, budgets, permission references, enabled state, next/last run, failure state.

### delegations
Delegation ID, parent task, provider, external task reference, status, submitted/result references, permission context, timestamps.

## 3. Relationships and constraints

- A task belongs to an objective and may have a parent task.
- Task steps belong to one task and have unique sequence numbers within that task.
- Approval requests reference the exact task step/action they approve.
- Model profile versions belong to one profile and are immutable.
- Experience records reference their originating task/objective.
- Dataset manifests reference exact reviewed experience IDs.
- Training runs reference immutable dataset versions and exact base model revisions.
- Evaluations reference candidate versions and benchmark versions.
- Delegations reference a parent task.
- Foreign keys are enabled and tested.

Use transactions for state changes that must remain consistent, especially approval decisions, task transitions, profile promotion, and dataset finalisation.

## 4. State and deletion

Prefer tombstone/supersession states for audit-sensitive records, but provide user-facing deletion controls for personal memory and capture data. Document retention and cascading behaviour. Deleting a memory must remove it from normal retrieval and future dataset selection. If the content has already entered a dataset or training artifact, surface the provenance and explain the required dataset rebuild/retraining path.

Do not promise cryptographic erasure unless implemented and tested.

## 5. Migration requirements

- Every migration has a monotonic version.
- Migrations run transactionally where SQLite permits.
- Backup before risky schema changes.
- Test fresh database creation and upgrade from the previous schema.
- Never silently discard columns or records.
- Keep migrations in source control.
- Add a rollback or recovery strategy; if down-migrations are unsafe, document restore-from-backup as the recovery route.

## 6. Indexing and performance

Index common lookup paths: task status/updated time, event timestamp/type/correlation ID, memory category/project/validity, experience outcome/review state, dataset version, and profile active version.

Avoid premature vector database dependencies. Define a retrieval interface; start with SQLite full-text/searchable metadata and add an embedding index only when measured retrieval needs justify it.

## 7. File storage

Use an application data directory resolved through Windows known-folder APIs or a configurable data root. Never assume a fixed username or drive letter. Keep paths relative to a configured managed root where practical. Validate paths before reading/writing and prevent path traversal outside approved roots.