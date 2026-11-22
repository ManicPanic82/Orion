"""Voice manager for Orion."""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from typing import Any

from orion.voice.models import MicState, Transcription, TTSState, VoiceSettings
from orion.voice.providers import STTProvider, TTSProvider


class VoiceManager:
    def __init__(
        self,
        *,
        stt: STTProvider | None = None,
        tts: TTSProvider | None = None,
        settings: VoiceSettings | None = None,
        message_callback: Callable[[str], Any] | None = None,
    ) -> None:
        self.stt = stt
        self.tts = tts
        self.settings = settings or VoiceSettings()
        self.message_callback = message_callback
        self.mic_state = MicState.IDLE if self.settings.mic_enabled else MicState.DISABLED
        self.tts_state = TTSState.IDLE
        self._listening = False
        self._audio_buffer = bytearray()
        self._lock = threading.RLock()
        self.last_error: str | None = None

    # -- mic control -----------------------------------------------------

    @property
    def mic_enabled(self) -> bool:
        return self.settings.mic_enabled

    def enable_mic(self) -> None:
        self.settings.mic_enabled = True
        if self.mic_state is MicState.DISABLED:
            self.mic_state = MicState.IDLE

    def disable_mic(self) -> None:
        self.settings.mic_enabled = False
        self.mic_state = MicState.DISABLED
        self._listening = False

    def push_to_talk_start(self) -> bool:
        if not self.settings.mic_enabled or not self.settings.push_to_talk_enabled:
            self.last_error = "microphone disabled"
            return False
        self._listening = True
        self.mic_state = MicState.LISTENING
        self._audio_buffer.clear()
        return True

    def push_to_talk_stop(self) -> Transcription | None:
        if not self._listening:
            return None
        self._listening = False
        self.mic_state = MicState.IDLE
        audio = bytes(self._audio_buffer)
        self._audio_buffer.clear()
        if self.stt is None:
            self.last_error = "STT unavailable"
            return None
        try:
            transcript = self.stt.transcribe(audio)
        except Exception as exc:
            self.last_error = str(exc)
            self.mic_state = MicState.ERROR
            return None
        if transcript.requires_confirmation or (
            self.settings.confirm_low_confidence
            and transcript.confidence < self.settings.confidence_threshold
        ):
            transcript.requires_confirmation = True
        return transcript

    def capture_audio(self, chunk: bytes) -> None:
        if self._listening:
            self._audio_buffer.extend(chunk)

    @property
    def is_listening(self) -> bool:
        return self._listening

    # -- transcription submission ----------------------------------------

    def submit_transcription(self, transcript: Transcription, *, confirmed: bool = True) -> bool:
        if transcript.requires_confirmation and not confirmed:
            return False
        if self.message_callback is not None:
            try:
                self.message_callback(transcript.text)
            except Exception as exc:
                self.last_error = str(exc)
                return False
        return True

    # -- TTS -------------------------------------------------------------

    def speak(self, text: str, *, sensitive: bool = False) -> bool:
        if not self.settings.tts_enabled or self.tts is None:
            self.last_error = "TTS unavailable"
            return False
        if sensitive and not self.settings.speak_sensitive:
            self.last_error = "sensitive content not spoken"
            return False
        if self.settings.in_quiet_hours():
            self.last_error = "quiet hours"
            return False
        self.tts_state = TTSState.SPEAKING
        try:
            self.tts.speak(text)
        except Exception as exc:
            self.last_error = str(exc)
            self.tts_state = TTSState.IDLE
            return False
        self.tts_state = TTSState.IDLE
        return True

    def stop_speaking(self) -> None:
        if self.tts is not None:
            with contextlib.suppress(Exception):
                self.tts.stop()
        self.tts_state = TTSState.INTERRUPTED

    @property
    def is_speaking(self) -> bool:
        return self.tts is not None and self.tts.is_speaking

    # -- health ----------------------------------------------------------

    def health(self) -> dict[str, bool]:
        return {
            "stt": self.stt.health_check() if self.stt is not None else False,
            "tts": self.tts.health_check() if self.tts is not None else False,
            "mic_enabled": self.settings.mic_enabled,
        }
