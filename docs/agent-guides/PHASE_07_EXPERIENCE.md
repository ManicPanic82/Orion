# Agent Guide: Phase 7 — Experience Recorder

## Objective
Capture useful task episodes and corrections for review without indiscriminate monitoring.

## Prerequisites
Task engine, event IDs, memory capture controls, privacy policy.

## In scope
- Experience/episode schema.
- Task-to-experience linkage.
- Action/observation capture.
- Outcome classification.
- User feedback.
- Privacy and quality review state.
- Review UI and capture pause/exclusion.

## Implementation instructions
1. Capture only activity within explicit Orion task/capability boundaries.
2. Do not record unrelated keystrokes, whole desktop, or private messages by default.
3. Link every episode to objective/task and capability versions.
4. Distinguish planned, attempted, observed, and verified actions.
5. Use SUCCESS, PARTIAL, FAILURE, CORRECTED, ABANDONED, INCONCLUSIVE, NOT_ELIGIBLE.
6. Record user correction as feedback; do not overwrite original attempt history.
7. Mark privacy and quality eligibility independently.
8. Support pause, exclude, inspect, redact, delete, and export.
9. Keep large screenshots/video outside DB with scoped access and retention controls.
10. Ensure experience capture failure does not corrupt task execution; surface the capture failure.

## Forbidden shortcuts
- No automatic positive label on completion.
- No training eligibility without review.
- No secrets or raw credential-bearing tool output.
- No silent capture outside the user's configured scope.

## Acceptance tests
- Task episode records traceable steps.
- Failed attempt stays failure after correction.
- Capture pause/exclusion works.
- Redaction removes sensitive fields from export.
- Experience deletion removes future dataset eligibility.
- Capture subsystem failure is observable and non-fatal to unrelated task state.

## Handoff
Provide example episode schema and demonstrate a successful, failed, and corrected episode.