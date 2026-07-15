"""Text-to-Speech modules for JARVIS."""

from voice.tts.piper_tts import PiperTTS
from voice.tts.openai_tts import OpenAITTS

__all__ = ["PiperTTS", "OpenAITTS"]
