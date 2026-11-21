# Agent Guide: Phase 9 — Voice Subsystem

## Objective
Add push-to-talk voice as an alternative transport for the existing agent command interface.

## Prerequisites
Stable Core API, session/conversation handling, settings, notification controls.

## In scope
- Global push-to-talk shortcut.
- Microphone capture lifecycle.
- Local STT provider interface.
- Local TTS provider interface.
- Transcription confirmation/edit option.
- Spoken response and notification.
- Stop-speaking/interrupt.
- Quiet hours and microphone privacy indicator.

## Implementation instructions
1. Voice input produces the same normalized user message used by typed input.
2. Keep STT/TTS providers replaceable and separately health-checked.
3. Keep audio capture off unless push-to-talk is actively held or explicitly configured.
4. Make microphone state visible and provide immediate mute/disable control.
5. Allow transcription review before submission where confidence is low or configurable.
6. TTS must be cancellable; interruption must stop queued and active speech.
7. Avoid speaking sensitive content in quiet/private contexts unless explicitly requested.
8. Voice subsystem failure must not block typed interaction.
9. Store audio only when explicitly enabled; define retention and deletion controls.
10. Wake word/always-listening is out of scope for this phase.

## Forbidden shortcuts
- No hidden always-on microphone.
- No hard dependency on a cloud STT/TTS service.
- No separate voice agent identity.
- No audio recording without clear consent and controls.

## Acceptance tests
- Push-to-talk captures only during activation.
- STT transcript reaches normal message endpoint.
- TTS response plays and can be interrupted.
- Quiet hours suppress non-critical speech.
- Mic disable prevents capture.
- STT/TTS failure leaves text usable.

## Handoff
Document provider selection, audio retention, shortcut configuration, privacy states, and tests.