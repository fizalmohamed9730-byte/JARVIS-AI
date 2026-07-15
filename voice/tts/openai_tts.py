"""
Online Text-to-Speech using OpenAI API.

Provides cloud-based TTS with multiple voice options and
high-quality neural speech synthesis.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

AVAILABLE_VOICES = {
    "alloy": {"description": "Neutral, balanced voice", "gender": "neutral"},
    "echo": {"description": "Warm, conversational male voice", "gender": "male"},
    "fable": {"description": "Expressive, storytelling voice", "gender": "neutral"},
    "onyx": {"description": "Deep, authoritative male voice", "gender": "male"},
    "nova": {"description": "Friendly, upbeat female voice", "gender": "female"},
    "shimmer": {"description": "Soft, calm female voice", "gender": "female"},
    "coral": {"description": "Warm, approachable voice", "gender": "female"},
    "sage": {"description": "Wise, thoughtful voice", "gender": "neutral"},
    "ash": {"description": "Clear, articulate voice", "gender": "male"},
    "ballad": {"description": "Melodic, expressive voice", "gender": "neutral"},
}

SUPPORTED_MODELS = {
    "tts-1": {"description": "Standard quality, fastest", "latency": "low"},
    "tts-1-hd": {"description": "High definition, best quality", "latency": "high"},
}

SUPPORTED_FORMATS = ["mp3", "opus", "aac", "flac", "wav", "pcm"]
SUPPORTED_SPEEDS = {"slow": 0.75, "normal": 1.0, "fast": 1.25}


class OpenAITTS:
    """
    Cloud-based text-to-speech engine using OpenAI API.

    Provides high-quality neural speech synthesis with multiple voices,
    speed control, and streaming support.
    """

    def __init__(self):
        self._api_key: Optional[str] = None
        self._client = None
        self._model: str = "tts-1"
        self._voice: str = "alloy"
        self._speed: float = 1.0
        self._response_format: str = "mp3"
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Return True if the client is ready for synthesis."""
        return self._initialized

    @property
    def voice(self) -> str:
        """Return the current voice name."""
        return self._voice

    @property
    def model(self) -> str:
        """Return the current model name."""
        return self._model

    async def initialize(
        self,
        api_key: Optional[str] = None,
        model: str = "tts-1",
        voice: str = "alloy",
        base_url: Optional[str] = None,
    ) -> None:
        """
        Initialize the OpenAI TTS client.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model: Model to use ("tts-1" or "tts-1-hd").
            voice: Default voice name.
            base_url: Custom API base URL for compatible providers.

        Raises:
            ImportError: If the openai package is not installed.
            ValueError: If no API key is provided or found.
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai is required for OpenAI TTS. "
                "Install with: pip install openai"
            )

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key is required. Provide via api_key parameter "
                "or set the OPENAI_API_KEY environment variable."
            )

        client_kwargs = {"api_key": self._api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = AsyncOpenAI(**client_kwargs)
        self._model = model
        self._voice = voice
        self._initialized = True
        logger.info("OpenAI TTS initialized (model=%s, voice=%s)", model, voice)

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        speed: Optional[float] = None,
        response_format: str = "wav",
    ) -> bytes:
        """
        Synthesize text to audio.

        Args:
            text: Text to synthesize (max 4096 characters).
            voice: Voice name override. Uses instance default if None.
            model: Model override ("tts-1" or "tts-1-hd").
            speed: Speed multiplier (0.25 to 4.0). Uses instance default if None.
            response_format: Audio format ("mp3", "opus", "aac", "flac", "wav", "pcm").

        Returns:
            Audio bytes in the requested format.

        Raises:
            RuntimeError: If the client is not initialized.
            ValueError: If text is empty or too long.
        """
        if not self._initialized or self._client is None:
            raise RuntimeError("OpenAITTS is not initialized. Call initialize() first.")
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        if len(text) > 4096:
            raise ValueError(f"Text exceeds maximum length of 4096 characters ({len(text)} given)")

        effective_voice = voice or self._voice
        effective_model = model or self._model
        effective_speed = speed if speed is not None else self._speed

        effective_speed = max(0.25, min(4.0, effective_speed))

        response = await self._client.audio.speech.create(
            model=effective_model,
            voice=effective_voice,
            input=text.strip(),
            speed=effective_speed,
            response_format=response_format,
        )
        audio_buffer = bytearray()
        async for chunk in response.iter_bytes():
            audio_buffer.extend(chunk)
        audio_bytes = bytes(audio_buffer)

        logger.debug(
            "Synthesized %d chars -> %d bytes (%s, %s, speed=%.2f)",
            len(text),
            len(audio_bytes),
            effective_voice,
            response_format,
            effective_speed,
        )
        return audio_bytes

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        speed: Optional[float] = None,
        response_format: str = "pcm",
        chunk_size: int = 4096,
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text and stream audio chunks.

        Uses PCM format internally for efficient streaming.

        Args:
            text: Text to synthesize.
            voice: Voice name override.
            model: Model override.
            speed: Speed multiplier.
            response_format: Audio format for output chunks.
            chunk_size: Bytes per streamed chunk.

        Yields:
            Audio byte chunks.
        """
        if not self._initialized or self._client is None:
            raise RuntimeError("OpenAITTS is not initialized. Call initialize() first.")

        effective_voice = voice or self._voice
        effective_model = model or self._model
        effective_speed = speed if speed is not None else self._speed
        effective_speed = max(0.25, min(4.0, effective_speed))

        response = await self._client.audio.speech.create(
            model=effective_model,
            voice=effective_voice,
            input=text.strip(),
            speed=effective_speed,
            response_format=response_format,
        )

        buffer = bytearray()
        async for chunk in response.iter_bytes():
            buffer.extend(chunk)
            while len(buffer) >= chunk_size:
                yield bytes(buffer[:chunk_size])
                buffer = buffer[chunk_size:]

        if buffer:
            yield bytes(buffer)

    async def synthesize_stream_text(
        self,
        text_stream: AsyncGenerator[str, None],
        voice: Optional[str] = None,
        model: Optional[str] = None,
        speed: Optional[float] = None,
        response_format: str = "pcm",
        chunk_size: int = 4096,
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize from a text stream, batching at sentence boundaries.

        Args:
            text_stream: Async generator yielding text chunks.
            voice: Voice name override.
            model: Model override.
            speed: Speed multiplier.
            response_format: Audio format.
            chunk_size: Bytes per streamed chunk.

        Yields:
            Audio byte chunks.
        """
        import re

        buffer = ""
        sentence_endings = re.compile(r"[.!?]+[\s$]")

        async for text_chunk in text_stream:
            buffer += text_chunk
            while True:
                match = sentence_endings.search(buffer)
                if match is None:
                    break
                split_pos = match.end()
                sentence = buffer[:split_pos].strip()
                buffer = buffer[split_pos:]
                if sentence:
                    async for audio_chunk in self.synthesize_stream(
                        sentence,
                        voice=voice,
                        model=model,
                        speed=speed,
                        response_format=response_format,
                        chunk_size=chunk_size,
                    ):
                        yield audio_chunk

        if buffer.strip():
            async for audio_chunk in self.synthesize_stream(
                buffer.strip(),
                voice=voice,
                model=model,
                speed=speed,
                response_format=response_format,
                chunk_size=chunk_size,
            ):
                yield audio_chunk

    async def set_voice(self, voice: str) -> None:
        """
        Change the active voice.

        Args:
            voice: Voice name (alloy, echo, fable, onyx, nova, shimmer, coral, sage, ash, ballad).

        Raises:
            ValueError: If the voice name is not recognized.
        """
        if voice not in AVAILABLE_VOICES:
            logger.warning("Voice '%s' not in known voices. Proceeding anyway.", voice)
        self._voice = voice
        logger.info("Voice changed to '%s'", voice)

    def set_speed(self, speed: float) -> None:
        """
        Set the synthesis speed.

        Args:
            speed: Speed multiplier (0.25 to 4.0).
        """
        self._speed = max(0.25, min(4.0, speed))
        logger.info("Speech speed set to %.2f", self._speed)

    def set_model(self, model: str) -> None:
        """
        Switch between TTS models.

        Args:
            model: Model name ("tts-1" or "tts-1-hd").
        """
        self._model = model
        logger.info("TTS model changed to '%s'", model)

    def list_voices(self) -> Dict[str, dict]:
        """
        List all available voices and their descriptions.

        Returns:
            Dictionary mapping voice names to metadata.
        """
        return dict(AVAILABLE_VOICES)

    def list_models(self) -> Dict[str, dict]:
        """
        List all available TTS models.

        Returns:
            Dictionary mapping model names to metadata.
        """
        return dict(SUPPORTED_MODELS)

    def cleanup(self) -> None:
        """Release resources."""
        self._client = None
        self._api_key = None
        self._initialized = False
        logger.info("OpenAI TTS resources released")
