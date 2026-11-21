# Agent Guide: Phase 1 — Operations Centre Shell

## Objective
Create the first runnable Orion Workstation desktop shell. This phase establishes visual language, navigation, configuration, and test conventions. It does not create the resident agent or real integrations.

## Prerequisites
Read root AGENTS.md, VISION.md, ARCHITECTURE.md, ROADMAP.md, and WINDOWS_DEVELOPMENT.md.

## In scope
- Python package metadata, supported Python version, dependency groups, lock strategy.
- PySide6 entry point and main window.
- Dark workstation theme with restrained blue/teal accents.
- Left navigation for Command Centre, Resident AI, Agent Activity, Projects, Automation, Experience & Learning, Model Manager, System Monitor, Settings.
- Command Centre layout: agent/model status, active tasks, recent events, command composer.
- Expandable persistent bottom console.
- Reusable cards, status indicators, navigation items, and spacing/typography tokens.
- Configuration persistence for UI preferences.
- Mock state provider with explicit MOCK labels.
- Unit and Qt-level tests appropriate to the chosen test setup.

## Implementation instructions
1. Inspect repository and choose a supported Python version compatible with Windows and PySide6. Record the decision.
2. Create a minimal installable package and a single documented launch entry point.
3. Keep UI code in presentation modules. Use view models/state objects so rendering is not the source of truth.
4. Build reusable components; avoid duplicating styling constants.
5. Make every inactive/future page clearly marked as planned or unavailable. Do not create fake working controls.
6. The command composer may submit to a local mock handler only. It must say the response is simulated.
7. Keep the console bounded, filterable where practical, and redact sensitive values.
8. Persist only UI settings in this phase. Do not create speculative domain tables.
9. Ensure the application exits cleanly and does not spawn an unmanaged background process.

## Forbidden shortcuts
- No real model inference, shell execution, filesystem agent, voice, learning, or network calls.
- No fake CPU/GPU values or fabricated task success.
- No business logic inside widgets beyond presentation and user input.
- No hard-coded user-specific paths.

## Acceptance tests
- Launches on target Windows environment using documented PowerShell command.
- All navigation destinations open.
- Layout remains usable at supported window sizes.
- Console expand/collapse works.
- Settings persist after restart.
- Mock status is visible and unmistakable.
- Unit/Qt tests pass.

## Handoff
Report Python version, dependencies, startup command, files, screenshots if available, exact test results, and known UI limitations.