# Agent Guide: Phase 14 — Gaming and Visual Interaction

## Objective
Add a controlled visual observation/action capability for games and other selected interactive applications.

## Prerequisites
Capability framework, task lifecycle, permission gateway, experience recorder, Windows automation foundations.

## In scope
- Selected-window capture provider.
- Frame sampling and image preprocessing.
- Observation representation.
- Game/application session selection.
- Input action adapter.
- Foreground-window enforcement.
- Episode/reward/progress recording.
- Demonstration and self-attempt data paths.

## Implementation instructions
1. Start with one explicitly selected application/window. Do not capture the entire desktop by default.
2. Show capture state and provide immediate stop.
3. Ensure input is directed only to the selected target; revalidate foreground/window identity before each action.
4. Define action schemas and bounds (keys/buttons, duration, rate, allowed coordinates).
5. Add action rate limits, session time limits, and emergency interruption.
6. Record observation/action/result transitions with timestamps and task linkage.
7. Separate human demonstration, autonomous attempt, and evaluation episodes.
8. Define game-specific success/progress signals; do not assume a generic reward function.
9. Respect game terms, anti-cheat rules, and user permission. Do not implement bypasses or stealth interaction.
10. Visual model and control backend must be replaceable.

## Forbidden shortcuts
- No input injection into unrelated windows.
- No hidden screen recording.
- No uncontrolled high-frequency input.
- No claiming a game is learned based only on text conversation.
- No bypass of anti-cheat or access controls.

## Acceptance tests
- Selected window capture only.
- Stop halts capture and input.
- Foreground change prevents action.
- Input bounds/rate limits enforced.
- Episode records frame/action/outcome.
- Capture privacy controls work.
- Evaluation reports actual task success metrics.

## Handoff
Document capture API, action schema, rate limits, privacy controls, and first supported application acceptance results.