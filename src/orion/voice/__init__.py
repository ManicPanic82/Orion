"""Voice subsystem for Orion."""

from orion.voice.manager import VoiceManager
from orion.voice.models import AudioRetention, MicState, Transcription, TTSState, VoiceSettings
from orion.voice.providers import MockSTTProvider, MockTTSProvider, STTProvider, TTSProvider

__all__ = [
    "AudioRetention",
    "MicState",
    "MockSTTProvider",
    "MockTTSProvider",
    "STTProvider",
    "TTSProvider",
    "TTSState",
    "Transcription",
    "VoiceManager",
    "VoiceSettings",
]
# Aliases
VoiceEngine = VoiceManager
