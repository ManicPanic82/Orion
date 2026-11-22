"""STT/TTS provider interfaces and mock implementations."""

from __future__ import annotations

import threading
from typing import Protocol

from orion.voice.models import Transcription


class STTProvider(Protocol):
    def transcribe(self, audio: bytes) -> Transcription: ...
    def health_check(self) -> bool: ...


class TTSProvider(Protocol):
    def speak(self, text: str) -> None: ...
    def stop(self) -> None: ...
    @property
    def is_speaking(self) -> bool: ...
    def health_check(self) -> bool: ...


class MockSTTProvider:
    def __init__(
        self, *, transcript: str = "mock transcript", confidence: float = 0.95, fail: bool = False
    ) -> None:
        self.transcript = transcript
        self.confidence = confidence
        self.fail = fail
        self.is_mock = True

    def transcribe(self, audio: bytes) -> Transcription:
        if self.fail:
            raise RuntimeError("STT failure")
        return Transcription(text=self.transcript, confidence=self.confidence)

    def health_check(self) -> bool:
        return not self.fail


class MockTTSProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self._speaking = False
        self._stop_event = threading.Event()
        self.spoken: list[str] = []
        self.is_mock = True

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def speak(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("TTS failure")
        self._speaking = True
        self._stop_event.clear()
        self.spoken.append(text)
        # Simulate short speech; allow interruption via stop.
        self._stop_event.wait(timeout=0.01)
        self._speaking = False

    def stop(self) -> None:
        self._stop_event.set()
        self._speaking = False

    def health_check(self) -> bool:
        return not self.fail
