"""
Offline Speech-to-Text using Vosk.

Provides lightweight, offline speech recognition suitable for
local-only operation without internet connectivity.
"""

import asyncio
import json
import logging
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)

MODEL_URLS = {
    "small": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    "medium": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
    "large": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.42.zip",
    "small-cn": "https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip",
    "small-ru": "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip",
    "small-fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
    "small-de": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
    "small-es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
    "small-pt": "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip",
    "small-tr": "https://alphacephei.com/vosk/models/vosk-model-small-tr-0.3.zip",
    "small-vn": "https://alphacephei.com/vosk/models/vosk-model-small-vn-0.4.zip",
    "small-ir": "https://alphacephei.com/vosk/models/vosk-model-small-fa-0.5.zip",
    "small-it": "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip",
    "small-nl": "https://alphacephei.com/vosk/models/vosk-model-small-nl-0.22.zip",
    "small-uk": "https://alphacephei.com/vosk/models/vosk-model-small-uk-v3-small.zip",
    "small-kz": "https://alphacephei.com/vosk/models/vosk-model-small-kz-0.15.zip",
    "small-ja": "https://alphacephei.com/vosk/models/vosk-model-small-ja-0.22.zip",
    "small-hi": "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip",
    "small-ar": "https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip",
}


class VoskSTT:
    """
    Offline speech recognition engine using Vosk.

    Supports multiple languages with small model downloads.
    Runs entirely locally without network access after model download.
    """

    def __init__(self):
        self._model = None
        self._recognizer = None
        self._model_path: Optional[str] = None
        self._sample_rate: int = 16000
        self._initialized = False
        self._language: str = "en-us"

    @property
    def is_initialized(self) -> bool:
        """Return True if the model is loaded and ready."""
        return self._initialized

    @property
    def sample_rate(self) -> int:
        """Return the expected sample rate."""
        return self._sample_rate

    async def initialize(
        self,
        model_path: Optional[str] = None,
        model_name: str = "small",
        sample_rate: int = 16000,
    ) -> None:
        """
        Initialize Vosk with a specified model.

        Downloads the model if it doesn't exist locally.

        Args:
            model_path: Path to an existing Vosk model directory.
            model_name: Name of a built-in model to download (e.g. "small", "medium").
            sample_rate: Audio sample rate in Hz.

        Raises:
            ImportError: If vosk is not installed.
            RuntimeError: If model download or loading fails.
        """
        try:
            from vosk import Model, SetLogLevel
        except ImportError:
            raise ImportError(
                "vosk is required for offline STT. Install with: pip install vosk"
            )

        SetLogLevel(-1)
        self._sample_rate = sample_rate

        if model_path is None:
            models_dir = Path.home() / ".jarvis" / "models" / "vosk"
            models_dir.mkdir(parents=True, exist_ok=True)
            model_path = str(models_dir / model_name)

        if not os.path.exists(model_path):
            if model_name not in MODEL_URLS:
                raise ValueError(
                    f"Unknown model '{model_name}'. Available: {list(MODEL_URLS.keys())}"
                )
            logger.info("Downloading Vosk model '%s'...", model_name)
            await self._download_model(MODEL_URLS[model_name], model_path)
            logger.info("Model downloaded to %s", model_path)

        self._model = Model(model_path)
        self._model_path = model_path
        self._initialized = True
        logger.info("Vosk STT initialized with model at %s", model_path)

    async def _download_model(self, url: str, dest_path: str) -> None:
        """Download and extract a Vosk model archive."""
        zip_path = dest_path + ".zip"

        def _download():
            urllib.request.urlretrieve(url, zip_path)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _download)

        def _extract():
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(os.path.dirname(dest_path))
            os.remove(zip_path)

        await loop.run_in_executor(None, _extract)

    def _create_recognizer(self, model=None):
        """Create a new Vosk recognizer instance."""
        from vosk import KaldiRecognizer
        m = model or self._model
        return KaldiRecognizer(m, self._sample_rate)

    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe raw audio data to text.

        Args:
            audio_data: Raw 16-bit PCM audio bytes.
            language: Optional language override (not used in single-session Vosk).

        Returns:
            Transcribed text string.

        Raises:
            RuntimeError: If the engine is not initialized.
        """
        if not self._initialized or self._model is None:
            raise RuntimeError("VoskSTT is not initialized. Call initialize() first.")

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, audio_data)

    def _transcribe_sync(self, audio_data: bytes) -> str:
        """Synchronous transcription for executor usage."""
        recognizer = self._create_recognizer()

        chunk_size = 4000
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i : i + chunk_size]
            recognizer.AcceptWaveform(chunk)

        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        language: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Transcribe a stream of audio chunks incrementally.

        Yields partial transcription results as audio arrives.

        Args:
            audio_chunks: Async generator yielding raw PCM audio chunks.
            language: Optional language override.

        Yields:
            Partial or final transcription text strings.
        """
        if not self._initialized or self._model is None:
            raise RuntimeError("VoskSTT is not initialized. Call initialize() first.")

        recognizer = self._create_recognizer()

        async for chunk in audio_chunks:
            if recognizer.AcceptWaveform(chunk):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    yield text
            else:
                partial = json.loads(recognizer.PartialResult())
                partial_text = partial.get("partial", "").strip()
                if partial_text:
                    yield partial_text

        final_result = json.loads(recognizer.FinalResult())
        final_text = final_result.get("text", "").strip()
        if final_text:
            yield final_text

    async def detect_language(self, audio_data: bytes) -> str:
        """
        Detect the language of audio data.

        Vosk uses a single language per model, so this returns the
        model's language or attempts detection via word patterns.

        Args:
            audio_data: Raw 16-bit PCM audio bytes.

        Returns:
            Detected language code string.
        """
        if self._model_path:
            path_str = self._model_path.lower()
            for lang_code in ["en-us", "cn", "ru", "fr", "de", "es", "pt", "tr", "vn", "ja", "hi", "ar"]:
                if lang_code in path_str:
                    return lang_code
        return self._language

    def set_model(self, model_path: str) -> None:
        """
        Hot-swap to a different Vosk model.

        Args:
            model_path: Path to a Vosk model directory.

        Raises:
            ImportError: If vosk is not installed.
        """
        try:
            from vosk import Model
        except ImportError:
            raise ImportError("vosk is required. Install with: pip install vosk")

        self._model = Model(model_path)
        self._model_path = model_path
        self._initialized = True
        logger.info("Vosk model swapped to %s", model_path)

    def cleanup(self) -> None:
        """Release model resources."""
        self._model = None
        self._recognizer = None
        self._initialized = False
        logger.info("Vosk STT resources released")
