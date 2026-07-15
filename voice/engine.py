"""
Main Voice Engine for JARVIS.

Orchestrates all voice components: STT, TTS, wake word detection,
and audio utilities into a unified voice processing pipeline.
"""

import asyncio
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from voice.audio_utils import AudioBuffer, AudioRecorder, calculate_energy
from voice.stt.whisper_stt import WhisperSTT
from voice.stt.vosk_stt import VoskSTT
from voice.tts.piper_tts import PiperTTS
from voice.tts.openai_tts import OpenAITTS
from voice.wakeword.porcupine_wakeword import WakeWordDetector

logger = logging.getLogger(__name__)


class EngineMode(enum.Enum):
    """Voice engine operating modes."""
    OFFLINE = "offline"
    ONLINE = "online"
    AUTO = "auto"


class EngineState(enum.Enum):
    """Current state of the voice engine."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class VoiceConfig:
    """Configuration for the voice engine."""
    mode: EngineMode = EngineMode.AUTO
    stt_engine: str = "whisper"
    tts_engine: str = "piper"
    language: str = "en"
    whisper_model: str = "base"
    vosk_model: str = "small"
    piper_voice: str = "en-us-lessac"
    openai_voice: str = "alloy"
    openai_api_key: Optional[str] = None
    picovoice_access_key: Optional[str] = None
    wake_words: List[str] = field(default_factory=lambda: ["jarvis"])
    sample_rate: int = 16000
    chunk_size: int = 1024
    energy_threshold: float = 500.0
    silence_duration: float = 1.5
    max_recording_seconds: float = 30.0
    speech_speed: float = 1.0
    auto_interrupt: bool = True
    enable_wake_word: bool = True
    enable_vad: bool = True


@dataclass
class VoiceStatus:
    """Current status of the voice engine."""
    state: EngineState = EngineState.IDLE
    mode: EngineMode = EngineMode.AUTO
    stt_engine: str = "whisper"
    tts_engine: str = "piper"
    language: str = "en"
    is_online: bool = False
    wake_word_active: bool = False
    uptime_seconds: float = 0.0
    total_transcriptions: int = 0
    total_syntheses: int = 0
    last_error: Optional[str] = None


class VoiceEngine:
    """
    Main orchestrator for the JARVIS voice system.

    Coordinates speech-to-text, text-to-speech, wake word detection,
    and audio recording into a seamless voice interaction pipeline.

    Supports online (Whisper/OpenAI) and offline (Vosk/Piper) modes
    with automatic fallback.
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        """
        Initialize the voice engine.

        Args:
            config: Voice configuration. Uses defaults if None.
        """
        self._config = config or VoiceConfig()
        self._state = EngineState.IDLE
        self._status = VoiceStatus()
        self._start_time = time.time()

        # STT engines
        self._whisper_stt = WhisperSTT()
        self._vosk_stt = VoskSTT()
        self._active_stt = None

        # TTS engines
        self._piper_tts = PiperTTS()
        self._openai_tts = OpenAITTS()
        self._active_tts = None

        # Wake word
        self._wake_detector = WakeWordDetector()

        # Audio
        self._recorder = AudioRecorder(
            sample_rate=self._config.sample_rate,
            chunk_size=self._config.chunk_size,
        )
        self._audio_buffer = AudioBuffer(
            max_duration_seconds=self._config.max_recording_seconds,
            sample_rate=self._config.sample_rate,
        )

        # State management
        self._listening = False
        self._speaking = False
        self._on_transcription: Optional[Callable[[str], None]] = None
        self._on_speech_start: Optional[Callable[[], None]] = None
        self._on_speech_end: Optional[Callable[[], None]] = None
        self._on_wake_word: Optional[Callable[[str], None]] = None

    @property
    def state(self) -> EngineState:
        """Return the current engine state."""
        return self._state

    @property
    def status(self) -> VoiceStatus:
        """Return the current engine status."""
        self._status.state = self._state
        self._status.mode = self._config.mode
        self._status.stt_engine = self._config.stt_engine
        self._status.tts_engine = self._config.tts_engine
        self._status.language = self._config.language
        self._status.uptime_seconds = time.time() - self._start_time
        return self._status

    async def initialize(self) -> None:
        """
        Initialize all configured voice components.

        Sets up STT, TTS, and optionally wake word detection.
        Automatically selects online or offline engines based on mode.
        """
        logger.info("Initializing voice engine (mode=%s)...", self._config.mode.value)

        # Initialize STT
        await self._init_stt()

        # Initialize TTS
        await self._init_tts()

        # Initialize wake word detection
        if self._config.enable_wake_word:
            try:
                await self._wake_detector.initialize(
                    access_key=self._config.picovoice_access_key,
                    keywords=self._config.wake_words,
                )
                self._status.wake_word_active = True
            except Exception as e:
                logger.warning("Wake word initialization failed: %s", e)
                self._status.wake_word_active = False

        self._recorder.set_energy_threshold(self._config.energy_threshold)
        self._recorder.set_silence_duration(self._config.silence_duration)
        self._status.is_online = self._config.mode != EngineMode.OFFLINE

        logger.info("Voice engine initialized successfully")

    async def _init_stt(self) -> None:
        """Initialize the appropriate STT engine."""
        mode = self._config.mode

        if mode in (EngineMode.ONLINE, EngineMode.AUTO):
            try:
                await self._whisper_stt.initialize(model_size=self._config.whisper_model)
                self._active_stt = self._whisper_stt
                logger.info("Whisper STT initialized")
                return
            except Exception as e:
                logger.warning("Whisper STT failed: %s", e)
                if mode == EngineMode.ONLINE:
                    raise

        if mode in (EngineMode.OFFLINE, EngineMode.AUTO):
            try:
                await self._vosk_stt.initialize(model_name=self._config.vosk_model)
                self._active_stt = self._vosk_stt
                logger.info("Vosk STT initialized")
                return
            except Exception as e:
                logger.warning("Vosk STT failed: %s", e)
                if mode == EngineMode.OFFLINE:
                    raise

        if self._active_stt is None:
            raise RuntimeError("No STT engine could be initialized")

    async def _init_tts(self) -> None:
        """Initialize the appropriate TTS engine."""
        mode = self._config.mode

        if mode in (EngineMode.ONLINE, EngineMode.AUTO):
            try:
                if self._config.openai_api_key:
                    await self._openai_tts.initialize(
                        api_key=self._config.openai_api_key,
                        voice=self._config.openai_voice,
                    )
                    self._active_tts = self._openai_tts
                    logger.info("OpenAI TTS initialized")
                    return
            except Exception as e:
                logger.warning("OpenAI TTS failed: %s", e)
                if mode == EngineMode.ONLINE:
                    raise

        if mode in (EngineMode.OFFLINE, EngineMode.AUTO):
            try:
                await self._piper_tts.initialize(voice_id=self._config.piper_voice)
                self._active_tts = self._piper_tts
                logger.info("Piper TTS initialized")
                return
            except Exception as e:
                logger.warning("Piper TTS failed: %s", e)
                if mode == EngineMode.OFFLINE:
                    raise

        if self._active_tts is None:
            raise RuntimeError("No TTS engine could be initialized")

    async def start_listening(self, continuous: bool = True) -> None:
        """
        Start listening for audio input.

        Args:
            continuous: If True, runs continuous listening with wake word.
                        If False, listens once and stops.
        """
        if self._listening:
            logger.warning("Already listening")
            return

        self._listening = True
        self._state = EngineState.LISTENING
        logger.info("Started listening (continuous=%s)", continuous)

        if continuous and self._config.enable_wake_word and self._status.wake_word_active:
            await self._wake_detector.start_detection(
                callback=self._on_wake_detected,
            )

    async def stop_listening(self) -> None:
        """Stop listening for audio input."""
        self._listening = False
        if self._status.wake_word_active:
            await self._wake_detector.stop_detection()
        self._state = EngineState.IDLE
        logger.info("Stopped listening")

    def _on_wake_detected(self, keyword: str, confidence: float) -> None:
        """Callback when wake word is detected."""
        logger.info("Wake word '%s' detected (confidence=%.2f)", keyword, confidence)
        if self._on_wake_word:
            self._on_wake_word(keyword)

        if self._listening:
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(
                    asyncio.ensure_future, self._listen_and_transcribe()
                )
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._listen_and_transcribe())
                loop.close()

    async def _listen_and_transcribe(self) -> Optional[str]:
        """Record audio after wake word and transcribe it."""
        self._state = EngineState.LISTENING
        self._recorder.start_recording()

        try:
            await asyncio.sleep(self._config.silence_duration + 0.5)

            start_time = time.time()
            while self._listening and (time.time() - start_time) < self._config.max_recording_seconds:
                await asyncio.sleep(0.1)
                if not self._recorder.is_recording:
                    break

            audio = self._recorder.stop_recording()
            if not audio or len(audio) < 100:
                return None

            self._state = EngineState.PROCESSING
            text = await self.process_audio(audio)
            if text and self._on_transcription:
                self._on_transcription(text)
            return text

        except Exception as e:
            logger.error("Listen and transcribe error: %s", e)
            self._state = EngineState.ERROR
            return None
        finally:
            if self._recorder.is_recording:
                self._recorder.stop_recording()

    async def process_audio(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw PCM audio bytes.
            language: Optional language code override.

        Returns:
            Transcribed text string.
        """
        if self._active_stt is None:
            raise RuntimeError("No STT engine available")

        self._state = EngineState.PROCESSING
        lang = language or self._config.language

        try:
            if hasattr(self._active_stt, 'transcribe'):
                text = await self._active_stt.transcribe(audio_data, language=lang)
            else:
                text = await self._active_stt.transcribe(audio_data)

            self._status.total_transcriptions += 1
            logger.debug("Transcribed: '%s'", text[:100] if text else "(empty)")
            return text

        except Exception as e:
            logger.error("Transcription failed: %s", e)
            self._state = EngineState.ERROR
            self._status.last_error = str(e)
            raise
        finally:
            self._state = EngineState.IDLE if not self._listening else EngineState.LISTENING

    async def process_audio_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        language: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Transcribe a streaming audio source.

        Args:
            audio_chunks: Async generator of raw PCM audio chunks.
            language: Optional language code override.

        Yields:
            Transcription text strings.
        """
        if self._active_stt is None:
            raise RuntimeError("No STT engine available")

        self._state = EngineState.PROCESSING
        lang = language or self._config.language

        try:
            async for text in self._active_stt.transcribe_stream(audio_chunks, language=lang):
                self._status.total_transcriptions += 1
                yield text
        except Exception as e:
            logger.error("Stream transcription failed: %s", e)
            self._state = EngineState.ERROR
            raise
        finally:
            self._state = EngineState.IDLE if not self._listening else EngineState.LISTENING

    async def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        interruptible: bool = True,
    ) -> bytes:
        """
        Synthesize text to speech and play it.

        Args:
            text: Text to speak.
            voice: Voice override.
            speed: Speed override.
            interruptible: Whether speech can be interrupted.

        Returns:
            The raw audio bytes that were played.
        """
        if self._active_tts is None:
            raise RuntimeError("No TTS engine available")
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        self._state = EngineState.SPEAKING
        self._speaking = True

        if self._on_speech_start:
            self._on_speech_start()

        try:
            if isinstance(self._active_tts, OpenAITTS):
                audio = await self._active_tts.synthesize(
                    text, voice=voice, speed=speed, response_format="wav"
                )
            elif isinstance(self._active_tts, PiperTTS):
                audio = await self._active_tts.synthesize(text, speed=speed)
            else:
                audio = await self._active_tts.synthesize(text)

            self._status.total_syntheses += 1
            await self._play_audio(audio, interruptible=interruptible)
            return audio

        except Exception as e:
            logger.error("Speech synthesis failed: %s", e)
            self._state = EngineState.ERROR
            self._status.last_error = str(e)
            raise
        finally:
            self._speaking = False
            if self._on_speech_end:
                self._on_speech_end()
            self._state = EngineState.IDLE

    async def speak_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> None:
        """
        Synthesize text and stream audio playback.

        Args:
            text: Text to speak.
            voice: Voice override.
            speed: Speed override.
        """
        if self._active_tts is None:
            raise RuntimeError("No TTS engine available")

        self._state = EngineState.SPEAKING
        self._speaking = True

        if self._on_speech_start:
            self._on_speech_start()

        try:
            async for chunk in self._active_tts.synthesize_stream(text, voice=voice, speed=speed):
                if not self._speaking and self._config.auto_interrupt:
                    break
                await self._play_audio_chunk(chunk)
                await asyncio.sleep(0)

            self._status.total_syntheses += 1
        except Exception as e:
            logger.error("Stream speech failed: %s", e)
            self._state = EngineState.ERROR
            raise
        finally:
            self._speaking = False
            if self._on_speech_end:
                self._on_speech_end()
            self._state = EngineState.IDLE

    async def _play_audio(self, audio: bytes, interruptible: bool = True) -> None:
        """Play audio bytes through the system output (runs blocking I/O in executor)."""
        try:
            import pyaudio

            def _play_blocking():
                pa = pyaudio.PyAudio()
                try:
                    stream = pa.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=self._active_tts.sample_rate if self._active_tts else 22050,
                        output=True,
                    )
                    pcm_start = 44 if audio[:4] == b"RIFF" else 0
                    pcm_data = audio[pcm_start:]
                    chunk_size = 4096
                    for i in range(0, len(pcm_data), chunk_size):
                        if not self._speaking and interruptible and self._config.auto_interrupt:
                            break
                        stream.write(pcm_data[i : i + chunk_size])
                    stream.stop_stream()
                    stream.close()
                finally:
                    pa.terminate()

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _play_blocking)

        except ImportError:
            logger.warning("PyAudio not available for audio playback")
        except Exception as e:
            logger.error("Audio playback error: %s", e)

    async def _play_audio_chunk(self, chunk: bytes) -> None:
        """Play a single audio chunk (for streaming)."""
        await self._play_audio(chunk, interruptible=True)

    def interrupt_speech(self) -> None:
        """Immediately stop any ongoing speech synthesis or playback."""
        if self._speaking:
            self._speaking = False
            logger.info("Speech interrupted")

    async def set_language(self, lang: str) -> None:
        """
        Change the active language for STT and TTS.

        Args:
            lang: ISO 639-1 language code (e.g. "en", "es", "fr").
        """
        self._config.language = lang
        self._status.language = lang
        logger.info("Language changed to '%s'", lang)

    def set_mode(self, mode: EngineMode) -> None:
        """
        Switch the engine operating mode.

        Args:
            mode: New operating mode (OFFLINE, ONLINE, AUTO).
        """
        self._config.mode = mode
        self._status.mode = mode
        self._status.is_online = mode != EngineMode.OFFLINE
        logger.info("Engine mode changed to '%s'", mode.value)

    def set_energy_threshold(self, threshold: float) -> None:
        """
        Adjust the voice activity detection energy threshold.

        Args:
            threshold: RMS energy threshold. Increase for louder environments.
        """
        self._config.energy_threshold = threshold
        self._recorder.set_energy_threshold(threshold)

    def on_transcription(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback for transcription results.

        Args:
            callback: Function receiving transcribed text.
        """
        self._on_transcription = callback

    def on_speech_start(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for when speech starts.

        Args:
            callback: Function called on speech start.
        """
        self._on_speech_start = callback

    def on_speech_end(self, callback: Callable[[], None]) -> None:
        """
        Register a callback for when speech ends.

        Args:
            callback: Function called on speech end.
        """
        self._on_speech_end = callback

    def on_wake_word(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback for wake word detection.

        Args:
            callback: Function receiving the detected keyword.
        """
        self._on_wake_word = callback

    async def record_command(self, max_seconds: Optional[float] = None) -> bytes:
        """
        Record a single voice command (blocking).

        Starts recording on voice activity and stops on silence.

        Args:
            max_seconds: Maximum recording duration. Uses config default if None.

        Returns:
            Raw PCM audio bytes.
        """
        duration = max_seconds or self._config.max_recording_seconds
        self._state = EngineState.LISTENING
        self._recorder.start_recording()

        start = time.time()
        last_voice = time.time()
        silence_threshold = self._config.silence_duration

        try:
            while (time.time() - start) < duration:
                await asyncio.sleep(0.1)
                peek = self._recorder.buffer.peek_audio()
                energy = calculate_energy(peek)
                if energy > self._config.energy_threshold:
                    last_voice = time.time()
                elif (time.time() - last_voice) > silence_threshold and peek:
                    break
        finally:
            audio = self._recorder.stop_recording()
            self._state = EngineState.IDLE

        return audio

    def get_status(self) -> Dict[str, Any]:
        """
        Get a dictionary representation of the engine status.

        Returns:
            Dictionary with all status information.
        """
        status = self.status
        return {
            "state": status.state.value,
            "mode": status.mode.value,
            "stt_engine": status.stt_engine,
            "tts_engine": status.tts_engine,
            "language": status.language,
            "is_online": status.is_online,
            "wake_word_active": status.wake_word_active,
            "uptime_seconds": round(status.uptime_seconds, 2),
            "total_transcriptions": status.total_transcriptions,
            "total_syntheses": status.total_syntheses,
            "last_error": status.last_error,
            "whisper_ready": self._whisper_stt.is_initialized,
            "vosk_ready": self._vosk_stt.is_initialized,
            "piper_ready": self._piper_tts.is_initialized,
            "openai_ready": self._openai_tts.is_initialized,
        }

    async def fallback_to_offline(self) -> None:
        """
        Force fallback to offline engines.

        Useful when network connectivity is lost.
        """
        logger.info("Falling back to offline engines")
        self._config.mode = EngineMode.OFFLINE

        if not self._vosk_stt.is_initialized:
            await self._vosk_stt.initialize(model_name=self._config.vosk_model)
        self._active_stt = self._vosk_stt

        if not self._piper_tts.is_initialized:
            await self._piper_tts.initialize(voice_id=self._config.piper_voice)
        self._active_tts = self._piper_tts

        self._status.is_online = False
        logger.info("Successfully switched to offline mode")

    async def switch_to_online(self) -> None:
        """
        Switch to online engines.

        Requires network connectivity.
        """
        logger.info("Switching to online engines")
        self._config.mode = EngineMode.ONLINE

        if self._whisper_stt.is_initialized:
            self._active_stt = self._whisper_stt
        else:
            await self._whisper_stt.initialize(model_size=self._config.whisper_model)
            self._active_stt = self._whisper_stt

        if self._openai_tts.is_initialized:
            self._active_tts = self._openai_tts
        elif self._config.openai_api_key:
            await self._openai_tts.initialize(
                api_key=self._config.openai_api_key,
                voice=self._config.openai_voice,
            )
            self._active_tts = self._openai_tts

        self._status.is_online = True
        logger.info("Successfully switched to online mode")

    async def cleanup(self) -> None:
        """Release all resources and shut down."""
        logger.info("Cleaning up voice engine...")
        await self.stop_listening()
        self._recorder.cleanup()
        self._whisper_stt.cleanup()
        self._vosk_stt.cleanup()
        self._piper_tts.cleanup()
        self._openai_tts.cleanup()
        self._wake_detector.cleanup()
        self._state = EngineState.IDLE
        logger.info("Voice engine cleaned up")
