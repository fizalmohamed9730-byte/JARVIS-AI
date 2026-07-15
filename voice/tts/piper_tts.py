"""
Offline Text-to-Speech using Piper.

Provides high-quality local TTS using Piper neural voice synthesis.
"""

import asyncio
import io
import logging
import os
import subprocess
import wave
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)

AVAILABLE_VOICES = {
    "en-us-amy": {"language": "en-us", "quality": "medium", "speaker": "amy"},
    "en-us-lessac": {"language": "en-us", "quality": "high", "speaker": "lessac"},
    "en-us-libritts": {"language": "en-us", "quality": "high", "speaker": "libritts"},
    "en-gb-alba": {"language": "en-gb", "quality": "medium", "speaker": "alba"},
    "de-thorsten": {"language": "de", "quality": "medium", "speaker": "thorsten"},
    "fr-siwis": {"language": "fr", "quality": "medium", "speaker": "siwis"},
    "es-sharvard": {"language": "es", "quality": "medium", "speaker": "sharvard"},
    "it-lisa": {"language": "it", "quality": "medium", "speaker": "lisa"},
    "nl-nathalie": {"language": "nl", "quality": "medium", "speaker": "nathalie"},
    "ru-irina": {"language": "ru", "quality": "medium", "speaker": "irina"},
    "pt-br-faber": {"language": "pt-br", "quality": "medium", "speaker": "faber"},
}


class PiperTTS:
    """
    Offline text-to-speech engine using Piper.

    Uses pre-trained neural models for high-quality local TTS.
    Requires the piper binary or piper-tts Python package.
    """

    def __init__(self):
        self._model_path: Optional[str] = None
        self._config_path: Optional[str] = None
        self._voice_id: str = "en-us-lessac"
        self._speed: float = 1.0
        self._sample_rate: int = 22050
        self._channels: int = 1
        self._initialized = False
        self._piper_binary: Optional[str] = None
        self._use_python_api: bool = False

    @property
    def is_initialized(self) -> bool:
        """Return True if Piper is ready for synthesis."""
        return self._initialized

    @property
    def voice_id(self) -> str:
        """Return the current voice identifier."""
        return self._voice_id

    @property
    def sample_rate(self) -> int:
        """Return the output sample rate in Hz."""
        return self._sample_rate

    async def initialize(
        self,
        model_path: Optional[str] = None,
        voice_id: str = "en-us-lessac",
        piper_binary: Optional[str] = None,
    ) -> None:
        """
        Initialize Piper TTS with a voice model.

        Args:
            model_path: Path to a Piper .onnx model file.
            voice_id: Built-in voice identifier if model_path is None.
            piper_binary: Path to the piper command-line binary.

        Raises:
            FileNotFoundError: If the specified model does not exist.
            RuntimeError: If neither the binary nor Python API is available.
        """
        self._voice_id = voice_id

        if model_path is not None:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Piper model not found: {model_path}")
            self._model_path = model_path
            config_path = model_path.replace(".onnx", ".onnx.json")
            if os.path.exists(config_path):
                self._config_path = config_path
        else:
            models_dir = Path.home() / ".jarvis" / "models" / "piper"
            models_dir.mkdir(parents=True, exist_ok=True)
            self._model_path = str(models_dir / f"{voice_id}.onnx")
            self._config_path = str(models_dir / f"{voice_id}.onnx.json")
            if not os.path.exists(self._model_path):
                logger.info("Downloading Piper voice model '%s'...", voice_id)
                await self._download_voice(voice_id, models_dir)

        if piper_binary and os.path.isfile(piper_binary):
            self._piper_binary = piper_binary
        else:
            self._piper_binary = self._find_piper_binary()

        if self._piper_binary is None:
            try:
                import piper  # noqa: F401
                self._use_python_api = True
                self._initialized = True
            except ImportError:
                logger.warning(
                    "Neither piper binary nor piper-tts package found. "
                    "TTS will not be available."
                )
                self._initialized = False
                return
        else:
            self._initialized = True
        logger.info(
            "Piper TTS initialized with voice '%s' (model=%s)",
            self._voice_id,
            self._model_path,
        )

    async def _download_voice(self, voice_id: str, dest_dir: Path) -> None:
        """Download a Piper voice model."""
        import urllib.request

        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
        parts = voice_id.split("-")
        lang = parts[0]
        if len(parts) > 2:
            lang_region = f"{parts[0]}-{parts[1]}"
            speaker = parts[2]
        else:
            lang_region = parts[0]
            speaker = parts[1]

        onnx_url = f"{base_url}/{lang}/{lang_region}/{speaker}/{lang_region}-{speaker}.onnx"
        json_url = f"{base_url}/{lang}/{lang_region}/{speaker}/{lang_region}-{speaker}.onnx.json"

        onnx_path = dest_dir / f"{voice_id}.onnx"
        json_path = dest_dir / f"{voice_id}.onnx.json"

        loop = asyncio.get_running_loop()

        def _download():
            try:
                urllib.request.urlretrieve(onnx_url, str(onnx_path))
                urllib.request.urlretrieve(json_url, str(json_path))
            except Exception as e:
                logger.error("Failed to download voice '%s': %s", voice_id, e)
                raise

        await loop.run_in_executor(None, _download)

    def _find_piper_binary(self) -> Optional[str]:
        """Search for the piper binary on the system."""
        import shutil
        binary = shutil.which("piper")
        if binary:
            return binary

        common_paths = [
            Path.home() / "piper" / "piper",
            Path("/usr/local/bin/piper"),
            Path("/opt/piper/piper"),
            Path.home() / ".local" / "bin" / "piper",
        ]
        for p in common_paths:
            if p.is_file():
                return str(p)
        return None

    async def synthesize(
        self,
        text: str,
        speed: Optional[float] = None,
    ) -> bytes:
        """
        Synthesize text to audio bytes.

        Args:
            text: Text to synthesize.
            speed: Playback speed multiplier (0.5-2.0). Uses instance default if None.

        Returns:
            Raw WAV audio bytes.

        Raises:
            RuntimeError: If the engine is not initialized.
            ValueError: If text is empty.
        """
        if not self._initialized:
            raise RuntimeError("PiperTTS is not initialized. Call initialize() first.")
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        effective_speed = speed if speed is not None else self._speed

        if self._use_python_api:
            return await self._synthesize_python(text, effective_speed)
        elif self._piper_binary:
            return await self._synthesize_binary(text, effective_speed)
        else:
            raise RuntimeError("No Piper synthesis backend available")

    async def _synthesize_python(self, text: str, speed: float) -> bytes:
        """Synthesize using the piper Python package."""
        import piper

        loop = asyncio.get_running_loop()

        def _run():
            tts = piper.PiperVoice.load(self._model_path, config_path=self._config_path)
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, "wb") as wav_file:
                tts.synthesize(text, wav_file, length_scale=1.0 / speed)
            return wav_buf.getvalue()

        return await loop.run_in_executor(None, _run)

    async def _synthesize_binary(self, text: str, speed: float) -> bytes:
        """Synthesize using the piper command-line binary."""
        cmd = [self._piper_binary, "--model", self._model_path]
        if self._config_path and os.path.exists(self._config_path):
            cmd.extend(["--config", self._config_path])
        cmd.extend(["--length-scale", str(1.0 / speed)])

        loop = asyncio.get_running_loop()

        def _run():
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Piper failed: {proc.stderr.decode('utf-8', errors='replace')}")
            return proc.stdout

        return await loop.run_in_executor(None, _run)

    async def synthesize_stream(
        self,
        text: str,
        chunk_size: int = 4096,
        speed: Optional[float] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text and stream audio in chunks.

        Args:
            text: Text to synthesize.
            chunk_size: Size of each audio chunk in bytes.
            speed: Playback speed multiplier.

        Yields:
            Audio byte chunks.
        """
        audio = await self.synthesize(text, speed=speed)

        # Skip WAV header (44 bytes) to stream raw PCM
        pcm_start = 44
        pcm_data = audio[pcm_start:] if len(audio) > pcm_start else audio

        for i in range(0, len(pcm_data), chunk_size):
            yield pcm_data[i : i + chunk_size]

    async def synthesize_stream_text(
        self,
        text_stream: AsyncGenerator[str, None],
        chunk_size: int = 4096,
        speed: Optional[float] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize from a stream of text chunks.

        Accumulates text until sentence boundaries, then synthesizes and streams.

        Args:
            text_stream: Async generator of text chunks.
            chunk_size: Size of each audio chunk in bytes.
            speed: Playback speed multiplier.

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
                    audio = await self.synthesize(sentence, speed=speed)
                    pcm_data = audio[44:] if len(audio) > 44 else audio
                    for i in range(0, len(pcm_data), chunk_size):
                        yield pcm_data[i : i + chunk_size]

        if buffer.strip():
            audio = await self.synthesize(buffer.strip(), speed=speed)
            pcm_data = audio[44:] if len(audio) > 44 else audio
            for i in range(0, len(pcm_data), chunk_size):
                yield pcm_data[i : i + chunk_size]

    async def set_voice(self, voice_id: str) -> None:
        """
        Change the active voice.

        Args:
            voice_id: Voice identifier to switch to.

        Raises:
            FileNotFoundError: If the voice model cannot be found or downloaded.
        """
        old_voice = self._voice_id
        self._voice_id = voice_id

        models_dir = Path.home() / ".jarvis" / "models" / "piper"
        model_path = models_dir / f"{voice_id}.onnx"

        if not model_path.exists():
            logger.info("Downloading new voice model '%s'...", voice_id)
            await self._download_voice(voice_id, models_dir)

        self._model_path = str(model_path)
        config_path = str(models_dir / f"{voice_id}.onnx.json")
        if os.path.exists(config_path):
            self._config_path = config_path

        logger.info("Voice changed from '%s' to '%s'", old_voice, voice_id)

    def set_speed(self, speed: float) -> None:
        """
        Set the synthesis speed.

        Args:
            speed: Speed multiplier (0.5 to 2.0).
        """
        self._speed = max(0.5, min(2.0, speed))
        logger.info("Speech speed set to %.2f", self._speed)

    def list_voices(self) -> Dict[str, dict]:
        """
        List available built-in voices.

        Returns:
            Dictionary mapping voice IDs to their metadata.
        """
        return dict(AVAILABLE_VOICES)

    def cleanup(self) -> None:
        """Release resources."""
        self._model_path = None
        self._config_path = None
        self._piper_binary = None
        self._initialized = False
        logger.info("Piper TTS resources released")
