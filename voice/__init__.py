"""
JARVIS Voice System
===================

Complete voice processing pipeline including speech-to-text, text-to-speech,
wake word detection, and audio utilities.

Usage:
    from voice import VoiceEngine

    engine = VoiceEngine()
    await engine.start_listening()
"""

from voice.engine import VoiceEngine
from voice.audio_utils import AudioBuffer, AudioRecorder

__all__ = ["VoiceEngine", "AudioBuffer", "AudioRecorder"]
__version__ = "1.0.0"
