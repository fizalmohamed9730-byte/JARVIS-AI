"""
Wake Word Detection using Picovoice Porcupine.

Provides efficient, always-on wake word detection with support
for built-in and custom wake words.
"""

import asyncio
import logging
import struct
import threading
from collections.abc import Callable
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BUILTIN_KEYWORDS = [
    "alexa", "americano", "blueberry", "bumblebee", "computer",
    "grapefruit", "grasshopper", "hey google", "hey siri",
    "jarvis", "ok google", "porcupine", "terminator",
]

DEFAULT_SENSITIVITY = 0.5


class WakeWordEngine(Enum):
    """Available wake word detection engines."""
    PORCUPINE = "porcupine"


class WakeWordDetector:
    """
    Wake word detector using Picovoice Porcupine.

    Supports built-in keywords and custom-trained wake words.
    Runs a continuous audio stream and fires callbacks on detection.
    """

    def __init__(self):
        self._access_key: Optional[str] = None
        self._porcupine = None
        self._is_running = False
        self._callback: Optional[Callable[[str, float], None]] = None
        self._detection_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._keyword_indices: Dict[int, str] = {}
        self._sensitivity: float = DEFAULT_SENSITIVITY
        self._custom_keywords: List[str] = []
        self._sample_rate: int = 16000
        self._frame_length: int = 512
        self._audio_stream = None

    @property
    def is_running(self) -> bool:
        """Return True if detection is active."""
        return self._is_running

    @property
    def sample_rate(self) -> int:
        """Return the expected audio sample rate."""
        return self._sample_rate

    @property
    def frame_length(self) -> int:
        """Return the number of samples per frame."""
        return self._frame_length

    async def initialize(
        self,
        access_key: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        sensitivities: Optional[Dict[str, float]] = None,
        model_path: Optional[str] = None,
    ) -> None:
        """
        Initialize the Porcupine wake word engine.

        Args:
            access_key: Picovoice access key. Falls back to PICOVOICE_ACCESS_KEY env var.
            keywords: List of built-in keyword names to detect. Default: ["jarvis"].
            sensitivities: Per-keyword sensitivity values (0.0-1.0). Default: 0.5.
            model_path: Path to a custom Porcupine keyword model file.

        Raises:
            ImportError: If pvporcupine is not installed.
            ValueError: If no access key is provided or found.
        """
        try:
            import pvporcupine
        except ImportError:
            raise ImportError(
                "pvporcupine is required for wake word detection. "
                "Install with: pip install pvporcupine"
            )

        import os
        self._access_key = access_key or os.environ.get("PICOVOICE_ACCESS_KEY")
        if not self._access_key:
            raise ValueError(
                "Picovoice access key is required. Provide via access_key parameter "
                "or set the PICOVOICE_ACCESS_KEY environment variable. "
                "Get a free key at https://console.picovoice.ai/"
            )

        if keywords is None:
            keywords = ["jarvis"]

        self._custom_keywords = keywords
        self._sensivities = sensitivities or {}

        loop = asyncio.get_event_loop()

        def _init_porcupine():
            keyword_configs = []
            keyword_indices = {}
            idx = 0

            for kw in keywords:
                kw_lower = kw.lower().replace(" ", "_")
                if kw_lower in [k.replace(" ", "_") for k in BUILTIN_KEYWORDS]:
                    keyword_configs.append(kw_lower)
                    keyword_indices[idx] = kw
                    idx += 1

            sens_list = []
            for i in range(len(keyword_configs)):
                kw_name = keyword_indices.get(i, keyword_configs[i])
                sens_list.append(self._sensivities.get(kw_name, DEFAULT_SENSITIVITY))

            if model_path:
                return pvporcupine.create(
                    access_key=self._access_key,
                    model_path=model_path,
                    sensitivities=sens_list,
                )
            elif keyword_configs:
                return pvporcupine.create(
                    access_key=self._access_key,
                    keywords=keyword_configs,
                    sensitivities=sens_list,
                )
            else:
                raise ValueError("No valid keywords provided for wake word detection")

        self._porcupine = await loop.run_in_executor(None, _init_porcupine)
        self._sample_rate = self._porcupine.sample_rate
        self._frame_length = self._porcupine.frame_length
        self._keyword_indices = keyword_indices
        logger.info(
            "Wake word detector initialized (keywords=%s, sensitivity=%.2f)",
            keywords,
            self._sensitivity,
        )

    async def start_detection(
        self,
        callback: Callable[[str, float], None],
        audio_stream=None,
    ) -> None:
        """
        Start continuous wake word detection.

        Args:
            callback: Function called with (keyword, confidence) on detection.
            audio_stream: Optional PyAudio stream. If None, uses system microphone.

        Raises:
            RuntimeError: If the engine is not initialized.
        """
        if self._porcupine is None:
            raise RuntimeError("WakeWordDetector is not initialized. Call initialize() first.")
        if self._is_running:
            logger.warning("Detection is already running")
            return

        self._callback = callback
        self._stop_event.clear()
        self._audio_stream = audio_stream
        self._is_running = True

        self._detection_thread = threading.Thread(
            target=self._detection_loop,
            daemon=True,
            name="wake-word-detection",
        )
        self._detection_thread.start()
        logger.info("Wake word detection started")

    def _detection_loop(self) -> None:
        """Internal detection loop running in a background thread."""
        import pyaudio

        pa = None
        stream = None

        try:
            if self._audio_stream is not None:
                stream = self._audio_stream
            else:
                pa = pyaudio.PyAudio()
                stream = pa.open(
                    rate=self._sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=self._frame_length,
                )

            while not self._stop_event.is_set():
                pcm = stream.read(self._frame_length, exception_on_overflow=False)
                pcm_array = struct.unpack_from("h" * self._frame_length, pcm)

                keyword_index = self._porcupine.process(pcm_array)
                if keyword_index >= 0:
                    keyword_name = self._keyword_indices.get(keyword_index, f"keyword_{keyword_index}")
                    logger.info("Wake word detected: '%s'", keyword_name)
                    if self._callback:
                        try:
                            self._callback(keyword_name, self._sensitivity)
                        except Exception as e:
                            logger.error("Wake word callback error: %s", e)

        except Exception as e:
            if not self._stop_event.is_set():
                logger.error("Wake word detection error: %s", e)
        finally:
            if stream and stream != self._audio_stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if pa:
                try:
                    pa.terminate()
                except Exception:
                    pass

    async def stop_detection(self) -> None:
        """Stop continuous wake word detection."""
        if not self._is_running:
            return

        self._stop_event.set()
        self._is_running = False

        if self._detection_thread:
            self._detection_thread.join(timeout=3.0)
            self._detection_thread = None

        logger.info("Wake word detection stopped")

    async def add_custom_wake_word(
        self,
        keyword: str,
        sensitivity: float = DEFAULT_SENSITIVITY,
        model_path: Optional[str] = None,
    ) -> None:
        """
        Add a custom wake word to the detection list.

        Requires restarting detection to take effect.

        Args:
            keyword: Keyword string to add.
            sensitivity: Detection sensitivity (0.0-1.0).
            model_path: Path to custom .ppn keyword model file.

        Raises:
            ValueError: If no access key is set or model_path is missing for custom words.
        """
        if not self._access_key:
            raise ValueError("Access key must be set before adding custom wake words.")

        was_running = self._is_running
        if was_running:
            await self.stop_detection()

        if keyword not in self._custom_keywords:
            self._custom_keywords.append(keyword)
            self._sensivities[keyword] = sensitivity

        if model_path:
            import pvporcupine

            loop = asyncio.get_event_loop()
            keywords_list = [k.lower().replace(" ", "_") for k in self._custom_keywords]
            sens_list = [self._sensivities.get(k, DEFAULT_SENSITIVITY) for k in self._custom_keywords]

            def _recreate():
                return pvporcupine.create(
                    access_key=self._access_key,
                    keywords=keywords_list,
                    sensitivities=sens_list,
                )

            if self._porcupine:
                self._porcupine.delete()
            self._porcupine = await loop.run_in_executor(None, _recreate)
            self._sample_rate = self._porcupine.sample_rate
            self._frame_length = self._porcupine.frame_length

        logger.info("Custom wake word '%s' added (sensitivity=%.2f)", keyword, sensitivity)

        if was_running:
            await self.start_detection(self._callback)

    def set_sensitivity(self, keyword: str, sensitivity: float) -> None:
        """
        Set the sensitivity for a specific keyword.

        Args:
            keyword: Keyword to configure.
            sensitivity: Sensitivity value (0.0 to 1.0).
        """
        self._sensivities[keyword] = max(0.0, min(1.0, sensitivity))
        logger.info("Sensitivity for '%s' set to %.2f", keyword, self._sensivities[keyword])

    def set_global_sensitivity(self, sensitivity: float) -> None:
        """
        Set the default sensitivity for all keywords.

        Args:
            sensitivity: Sensitivity value (0.0 to 1.0).
        """
        self._sensitivity = max(0.0, min(1.0, sensitivity))
        logger.info("Global sensitivity set to %.2f", self._sensitivity)

    def list_keywords(self) -> List[str]:
        """
        List all available built-in keywords.

        Returns:
            List of keyword name strings.
        """
        return list(BUILTIN_KEYWORDS)

    def get_active_keywords(self) -> List[str]:
        """
        Get the currently configured active keywords.

        Returns:
            List of active keyword strings.
        """
        return list(self._custom_keywords)

    def _stop_detection_sync(self) -> None:
        """Stop wake word detection synchronously."""
        if not self._is_running:
            return

        self._stop_event.set()
        self._is_running = False

        if self._detection_thread:
            self._detection_thread.join(timeout=3.0)
            self._detection_thread = None

        logger.info("Wake word detection stopped")

    def cleanup(self) -> None:
        """Release all resources."""
        self._stop_detection_sync()

        if self._porcupine:
            try:
                self._porcupine.delete()
            except Exception:
                pass
            self._porcupine = None

        self._callback = None
        self._keyword_indices.clear()
        logger.info("Wake word detector resources released")
