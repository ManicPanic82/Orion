"""Tests for voice subsystem."""

from __future__ import annotations

from orion.voice import (
    MockSTTProvider,
    MockTTSProvider,
    VoiceManager,
    VoiceSettings,
)


def test_push_to_talk_captures_only_during_activation() -> None:
    stt = MockSTTProvider(transcript="hello")
    mgr = VoiceManager(stt=stt, tts=MockTTSProvider())
    assert mgr.push_to_talk_start() is True
    mgr.capture_audio(b"abc")
    assert mgr.is_listening is True
    transcript = mgr.push_to_talk_stop()
    assert transcript is not None
    assert transcript.text == "hello"
    assert mgr.is_listening is False


def test_mic_disable_prevents_capture() -> None:
    mgr = VoiceManager(stt=MockSTTProvider(), tts=MockTTSProvider())
    mgr.disable_mic()
    assert mgr.push_to_talk_start() is False


def test_stt_transcript_reaches_message_endpoint() -> None:
    received = []

    def cb(text: str) -> None:
        received.append(text)

    stt = MockSTTProvider(transcript="typed by voice")
    mgr = VoiceManager(stt=stt, tts=MockTTSProvider(), message_callback=cb)
    mgr.push_to_talk_start()
    transcript = mgr.push_to_talk_stop()
    assert mgr.submit_transcription(transcript) is True
    assert received == ["typed by voice"]


def test_tts_plays_and_interrupts() -> None:
    tts = MockTTSProvider()
    mgr = VoiceManager(stt=MockSTTProvider(), tts=tts)
    assert mgr.speak("hello") is True
    mgr.stop_speaking()
    assert mgr.tts_state.value == "interrupted"


def test_quiet_hours_suppress_speech() -> None:
    from datetime import time

    settings = VoiceSettings(quiet_hours_start=time(0, 0), quiet_hours_end=time(23, 59))
    mgr = VoiceManager(stt=MockSTTProvider(), tts=MockTTSProvider(), settings=settings)
    assert mgr.speak("hello") is False
    assert mgr.last_error == "quiet hours"


def test_stt_failure_leaves_text_usable() -> None:
    stt = MockSTTProvider(fail=True)
    mgr = VoiceManager(stt=stt, tts=MockTTSProvider())
    mgr.push_to_talk_start()
    transcript = mgr.push_to_talk_stop()
    assert transcript is None
    assert mgr.last_error is not None


def test_tts_failure_leaves_text_usable() -> None:
    tts = MockTTSProvider(fail=True)
    mgr = VoiceManager(stt=MockSTTProvider(), tts=tts)
    assert mgr.speak("hello") is False
    assert mgr.last_error == "TTS failure"
