"""
Online Speech-to-Text using Faster-Whisper.

Provides high-quality speech recognition using optimized CTranslate2
Whisper implementation with GPU acceleration support.
"""

import asyncio
import io
import logging
import wave
from pathlib import Path
from typing import AsyncGenerator, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

SUPPORTED_MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"]


class WhisperSTT:
    """
    Online speech recognition engine using Faster-Whisper.

    Supports multiple model sizes, automatic GPU detection,
    and streaming transcription via chunked processing.
    """

    def __init__(self):
        self._model = None
        self._model_size: str = "base"
        self._device: str = "cpu"
        self._compute_type: str = "int8"
        self._initialized = False
        self._sample_rate: int = 16000

    @property
    def is_initialized(self) -> bool:
        """Return True if the model is loaded and ready."""
        return self._initialized

    @property
    def model_size(self) -> str:
        """Return the loaded model size name."""
        return self._model_size

    @property
    def device(self) -> str:
        """Return the device being used (cpu/cuda)."""
        return self._device

    async def initialize(
        self,
        model_size: str = "base",
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        download_root: Optional[str] = None,
        num_workers: int = 1,
    ) -> None:
        """
        Initialize the Faster-Whisper model.

        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3).
            device: Device to run on ("cpu", "cuda", "auto"). Auto-detects if None.
            compute_type: Compute type ("int8", "float16", "float32"). Auto-detects if None.
            download_root: Directory to cache downloaded models.
            num_workers: Number of workers for parallel decoding.

        Raises:
            ImportError: If faster_whisper is not installed.
            RuntimeError: If GPU is requested but unavailable.
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper is required for online STT. "
                "Install with: pip install faster-whisper"
            )

        if model_size not in SUPPORTED_MODEL_SIZES:
            logger.warning(
                "Model size '%s' not in known sizes %s. Proceeding anyway.",
                model_size,
                SUPPORTED_MODEL_SIZES,
            )

        if device is None:
            device = self._detect_device()
        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"

        self._device = device
        self._compute_type = compute_type
        self._model_size = model_size

        loop = asyncio.get_running_loop()

        def _load_model():
            return WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
                num_workers=num_workers,
            )

        logger.info("Loading Faster-Whisper model '%s' on %s (%s)...", model_size, device, compute_type)
        self._model = await loop.run_in_executor(None, _load_model)
        self._initialized = True
        logger.info("Faster-Whisper model loaded successfully")

    def _detect_device(self) -> str:
        """Auto-detect the best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    async def transcribe(
        self,
        audio_data: Union[bytes, np.ndarray],
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,
        compression_ratio_threshold: float = 2.4,
        no_speech_threshold: float = 0.6,
        initial_prompt: Optional[str] = None,
        word_timestamps: bool = False,
    ) -> str:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw PCM bytes or numpy float32 array.
            language: ISO 639-1 language code (e.g. "en"). None for auto-detect.
            task: "transcribe" or "translate" (to English).
            beam_size: Beam size for decoding.
            best_of: Number of candidates when sampling.
            temperature: Sampling temperature. 0 means greedy.
            compression_ratio_threshold: Threshold for compression ratio filtering.
            no_speech_threshold: Threshold for silence detection.
            initial_prompt: Optional prompt to guide transcription style.
            word_timestamps: If True, include word-level timestamps.

        Returns:
            Transcribed text string.

        Raises:
            RuntimeError: If the engine is not initialized.
        """
        if not self._initialized or self._model is None:
            raise RuntimeError("WhisperSTT is not initialized. Call initialize() first.")

        audio_array = self._prepare_audio(audio_data)
        loop = asyncio.get_running_loop()

        def _transcribe():
            segments, info = self._model.transcribe(
                audio_array,
                language=language,
                task=task,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                compression_ratio_threshold=compression_ratio_threshold,
                no_speech_threshold=no_speech_threshold,
                initial_prompt=initial_prompt,
                word_timestamps=word_timestamps,
            )
            texts = []
            for segment in segments:
                texts.append(segment.text.strip())
            return " ".join(texts), info

        result_text, info = await loop.run_in_executor(None, _transcribe)
        logger.debug(
            "Transcribed %.1fs audio, detected language=%s (prob=%.2f)",
            info.duration,
            info.language,
            info.language_probability,
        )
        return result_text

    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        language: Optional[str] = None,
        chunk_duration_seconds: float = 3.0,
        overlap_seconds: float = 0.5,
    ) -> AsyncGenerator[str, None]:
        """
        Transcribe streaming audio by accumulating and processing chunks.

        Collects audio into overlapping windows and transcribes each window,
        yielding new text as it becomes available.

        Args:
            audio_chunks: Async generator yielding raw PCM audio chunks.
            language: ISO 639-1 language code. None for auto-detect.
            chunk_duration_seconds: Duration of each transcription window.
            overlap_seconds: Overlap between consecutive windows.

        Yields:
            Transcribed text strings for each processed window.
        """
        if not self._initialized or self._model is None:
            raise RuntimeError("WhisperSTT is not initialized. Call initialize() first.")

        chunk_size_bytes = int(chunk_duration_seconds * self._sample_rate * 2)
        overlap_bytes = int(overlap_seconds * self._sample_rate * 2)
        buffer = bytearray()
        last_text = ""

        async for chunk in audio_chunks:
            buffer.extend(chunk)

            if len(buffer) >= chunk_size_bytes:
                audio_array = self._prepare_audio(bytes(buffer[:chunk_size_bytes]))
                loop = asyncio.get_running_loop()

                def _transcribe_chunk(arr):
                    segments, info = self._model.transcribe(
                        arr,
                        language=language,
                        beam_size=3,
                        best_of=1,
                        temperature=0.0,
                    )
                    return " ".join(s.text.strip() for s in segments)

                text = await loop.run_in_executor(None, _transcribe_chunk, audio_array)
                if text and text != last_text:
                    last_text = text
                    yield text

                if overlap_bytes > 0:
                    buffer = bytearray(buffer[-overlap_bytes:])
                else:
                    buffer.clear()

        if buffer:
            audio_array = self._prepare_audio(bytes(buffer))
            loop = asyncio.get_running_loop()

            def _transcribe_final(arr):
                segments, _ = self._model.transcribe(
                    arr,
                    language=language,
                    beam_size=3,
                    best_of=1,
                    temperature=0.0,
                )
                return " ".join(s.text.strip() for s in segments)

            text = await loop.run_in_executor(None, _transcribe_final, audio_array)
            if text and text != last_text:
                yield text

    async def detect_language(self, audio_data: Union[bytes, np.ndarray]) -> str:
        """
        Detect the language of audio data.

        Args:
            audio_data: Raw PCM bytes or numpy float32 array.

        Returns:
            ISO 639-1 language code string.
        """
        if not self._initialized or self._model is None:
            raise RuntimeError("WhisperSTT is not initialized. Call initialize() first.")

        audio_array = self._prepare_audio(audio_data)
        loop = asyncio.get_running_loop()

        def _detect():
            segment = self._model.transcribe(
                audio_array,
                beam_size=1,
                best_of=1,
            )
            for seg in segment:
                return seg.language
            return "en"

        return await loop.run_in_executor(None, _detect)

    def _prepare_audio(self, audio_data: Union[bytes, np.ndarray]) -> np.ndarray:
        """
        Prepare audio data for Whisper input format.

        Converts raw PCM bytes to float32 numpy array normalized to [-1, 1].

        Args:
            audio_data: Raw 16-bit PCM bytes or existing float32 array.

        Returns:
            Float32 numpy array suitable for Whisper.
        """
        if isinstance(audio_data, np.ndarray):
            if audio_data.dtype == np.float32:
                return audio_data
            if audio_data.dtype == np.int16:
                return audio_data.astype(np.float32) / 32768.0
            return audio_data.astype(np.float32)

        samples = np.frombuffer(audio_data, dtype=np.int16)
        return samples.astype(np.float32) / 32768.0

    def cleanup(self) -> None:
        """Release model resources."""
        self._model = None
        self._initialized = False
        logger.info("Whisper STT resources released")
