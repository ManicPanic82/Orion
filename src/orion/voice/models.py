"""Voice subsystem domain models for Orion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from enum import StrEnum
from typing import Any


class MicState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    DISABLED = "disabled"
    ERROR = "error"


class TTSState(StrEnum):
    IDLE = "idle"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


class AudioRetention(StrEnum):
    NONE = "none"
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"


@dataclass(slots=True)
class Transcription:
    text: str = ""
    confidence: float = 1.0
    requires_confirmation: bool = False
    language: str = "en"

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "requires_confirmation": self.requires_confirmation,
            "language": self.language,
        }


@dataclass(slots=True)
class VoiceSettings:
    push_to_talk_enabled: bool = True
    mic_enabled: bool = True
    tts_enabled: bool = True
    confirm_low_confidence: bool = True
    confidence_threshold: float = 0.7
    quiet_hours_start: time | None = None
    quiet_hours_end: time | None = None
    retention: AudioRetention = AudioRetention.NONE
    speak_sensitive: bool = False

    def in_quiet_hours(self, now: datetime | None = None) -> bool:
        if self.quiet_hours_start is None or self.quiet_hours_end is None:
            return False
        now = (now or datetime.now(UTC)).timetz().replace(tzinfo=None)
        start = self.quiet_hours_start
        end = self.quiet_hours_end
        if start <= end:
            return start <= now <= end
        return now >= start or now <= end
