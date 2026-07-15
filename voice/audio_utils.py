"""
Audio Utilities for JARVIS Voice System.

Provides audio buffer management, format conversion, normalization,
silence removal, energy calculation, and microphone recording.
"""

import io
import threading
import time
import wave
from collections import deque
from enum import Enum
from typing import Callable, Optional

import numpy as np


class AudioFormat(Enum):
    """Supported audio formats."""
    PCM = "pcm"
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"


class AudioBuffer:
    """
    Thread-safe circular buffer for managing audio chunks.

    Accumulates audio data from streaming sources and provides
    methods to retrieve the buffered content or convert formats.
    """

    def __init__(self, max_duration_seconds: float = 30.0, sample_rate: int = 16000):
        """
        Initialize the audio buffer.

        Args:
            max_duration_seconds: Maximum audio duration to retain in seconds.
            sample_rate: Expected sample rate of incoming audio in Hz.
        """
        self._sample_rate = sample_rate
        self._max_samples = int(max_duration_seconds * sample_rate)
        self._buffer: deque[bytes] = deque()
        self._current_size = 0
        self._lock = threading.Lock()
        self._chunk_size_samples = 0

    @property
    def sample_rate(self) -> int:
        """Return the sample rate of the buffer."""
        return self._sample_rate

    @property
    def duration_seconds(self) -> float:
        """Return the current duration of buffered audio in seconds."""
        with self._lock:
            return self._current_size / (self._sample_rate * 2)  # 16-bit = 2 bytes/sample

    def add_chunk(self, chunk: bytes) -> None:
        """
        Add an audio chunk to the buffer.

        Args:
            chunk: Raw audio bytes to append.
        """
        chunk_samples = len(chunk) // 2  # 16-bit audio
        with self._lock:
            self._buffer.append(chunk)
            self._current_size += chunk_samples
            while self._current_size > self._max_samples and self._buffer:
                removed = self._buffer.popleft()
                self._current_size -= len(removed) // 2

    def get_audio(self) -> bytes:
        """
        Retrieve all buffered audio data and clear the buffer.

        Returns:
            Concatenated raw audio bytes.
        """
        with self._lock:
            audio = b"".join(self._buffer)
            self._buffer.clear()
            self._current_size = 0
            return audio

    def peek_audio(self) -> bytes:
        """
        Retrieve all buffered audio without clearing.

        Returns:
            Concatenated raw audio bytes.
        """
        with self._lock:
            return b"".join(self._buffer)

    def clear(self) -> None:
        """Clear the buffer completely."""
        with self._lock:
            self._buffer.clear()
            self._current_size = 0

    def is_empty(self) -> bool:
        """Return True if the buffer has no data."""
        with self._lock:
            return self._current_size == 0

    def to_wav(self, audio: Optional[bytes] = None) -> bytes:
        """
        Convert raw PCM audio to WAV format.

        Args:
            audio: Raw PCM bytes. If None, uses buffered audio.

        Returns:
            WAV-formatted bytes.
        """
        if audio is None:
            audio = self.peek_audio()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self._sample_rate)
            wf.writeframes(audio)
        return buf.getvalue()


class AudioRecorder:
    """
    Microphone audio recorder using PyAudio.

    Provides blocking and callback-based recording with
    automatic level monitoring.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        format_bits: int = 16,
    ):
        """
        Initialize the audio recorder.

        Args:
            sample_rate: Recording sample rate in Hz.
            channels: Number of audio channels.
            chunk_size: Number of frames per buffer.
            format_bits: Bit depth (8, 16, or 32).
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        self._format_bits = format_bits
        self._pyaudio = None
        self._stream = None
        self._is_recording = False
        self._callback: Optional[Callable[[bytes], None]] = None
        self._record_thread: Optional[threading.Thread] = None
        self._buffer = AudioBuffer(max_duration_seconds=60.0, sample_rate=sample_rate)
        self._energy_threshold = 500.0
        self._silence_duration = 1.5
        self._last_voice_time = 0.0

    @property
    def is_recording(self) -> bool:
        """Return True if currently recording."""
        return self._is_recording

    @property
    def buffer(self) -> AudioBuffer:
        """Return the internal audio buffer."""
        return self._buffer

    def _get_pyaudio(self):
        """Lazy-load PyAudio instance."""
        if self._pyaudio is None:
            try:
                import pyaudio
                self._pyaudio = pyaudio.PyAudio()
            except ImportError:
                raise RuntimeError(
                    "PyAudio is required for microphone recording. "
                    "Install with: pip install pyaudio"
                )
        return self._pyaudio

    def _get_format(self):
        """Return the PyAudio format constant."""
        pa = self._get_pyaudio()
        if self._format_bits == 8:
            return pa.get_format_from_width(1)
        elif self._format_bits == 16:
            return pa.get_format_from_width(2)
        elif self._format_bits == 32:
            return pa.get_format_from_width(4)
        raise ValueError(f"Unsupported bit depth: {self._format_bits}")

    def start_recording(self, callback: Optional[Callable[[bytes], None]] = None) -> None:
        """
        Start recording audio from the microphone.

        Args:
            callback: Optional function called with each audio chunk.
        """
        if self._is_recording:
            return

        self._callback = callback
        self._buffer.clear()
        pa = self._get_pyaudio()

        self._stream = pa.open(
            format=self._get_format(),
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            frames_per_buffer=self._chunk_size,
        )
        self._is_recording = True
        self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self._record_thread.start()

    def _record_loop(self) -> None:
        """Internal recording loop running in a background thread."""
        try:
            while self._is_recording and self._stream:
                data = self._stream.read(self._chunk_size, exception_on_overflow=False)
                self._buffer.add_chunk(data)
                if self._callback:
                    self._callback(data)
        except Exception:
            self._is_recording = False

    def stop_recording(self) -> bytes:
        """
        Stop recording and return all captured audio.

        Returns:
            Raw PCM audio bytes.
        """
        self._is_recording = False
        if self._record_thread:
            self._record_thread.join(timeout=2.0)
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        return self._buffer.get_audio()

    def record_chunk(self, duration_seconds: float) -> bytes:
        """
        Record a fixed-duration audio chunk (blocking).

        Args:
            duration_seconds: How long to record in seconds.

        Returns:
            Raw PCM audio bytes.
        """
        pa = self._get_pyaudio()
        stream = pa.open(
            format=self._get_format(),
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            frames_per_buffer=self._chunk_size,
        )
        frames = []
        num_chunks = int(duration_seconds * self._sample_rate / self._chunk_size)
        try:
            for _ in range(num_chunks):
                data = stream.read(self._chunk_size, exception_on_overflow=False)
                frames.append(data)
        finally:
            stream.stop_stream()
            stream.close()
        return b"".join(frames)

    def set_energy_threshold(self, threshold: float) -> None:
        """
        Set the energy threshold for voice activity detection.

        Args:
            threshold: RMS energy threshold. Speech above this is considered voice.
        """
        self._energy_threshold = threshold

    def set_silence_duration(self, duration: float) -> None:
        """
        Set the silence duration to wait before stopping VAD recording.

        Args:
            duration: Seconds of silence before auto-stop.
        """
        self._silence_duration = duration

    def cleanup(self) -> None:
        """Release all PyAudio resources."""
        self.stop_recording()
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None


def convert_format(
    audio: bytes,
    from_format: AudioFormat,
    to_format: AudioFormat,
    sample_rate: int = 16000,
    channels: int = 1,
) -> bytes:
    """
    Convert audio data between formats.

    Args:
        audio: Raw audio bytes.
        from_format: Source audio format.
        to_format: Target audio format.
        sample_rate: Sample rate for PCM/WAV.
        channels: Number of channels for PCM/WAV.

    Returns:
        Converted audio bytes.

    Raises:
        ValueError: If conversion path is not supported.
    """
    if from_format == to_format:
        return audio

    pcm_data: Optional[bytes] = None

    # Decode source to PCM
    if from_format == AudioFormat.PCM:
        pcm_data = audio
    elif from_format == AudioFormat.WAV:
        pcm_data = _wav_to_pcm(audio)
    else:
        raise ValueError(f"Decoding from {from_format.value} is not supported without ffmpeg.")

    # Encode PCM to target
    if to_format == AudioFormat.PCM:
        return pcm_data
    elif to_format == AudioFormat.WAV:
        return _pcm_to_wav(pcm_data, sample_rate, channels)
    else:
        raise ValueError(f"Encoding to {to_format.value} is not supported without ffmpeg.")


def _wav_to_pcm(wav_data: bytes) -> bytes:
    """Extract raw PCM frames from WAV bytes."""
    buf = io.BytesIO(wav_data)
    with wave.open(buf, "rb") as wf:
        return wf.readframes(wf.getnframes())


def _pcm_to_wav(pcm_data: bytes, sample_rate: int, channels: int) -> bytes:
    """Wrap raw PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def normalize_audio(audio: bytes, target_amplitude: float = 0.8) -> bytes:
    """
    Normalize audio amplitude to a target level.

    Args:
        audio: Raw 16-bit PCM audio bytes.
        target_amplitude: Target peak amplitude as a fraction of max (0.0-1.0).

    Returns:
        Normalized audio bytes.
    """
    if len(audio) < 2:
        return audio

    samples = np.frombuffer(audio, dtype=np.int16)
    if samples.size == 0:
        return audio

    peak = np.max(np.abs(samples.astype(np.float64)))
    if peak == 0:
        return audio

    target_peak = 32767.0 * target_amplitude
    gain = target_peak / peak
    normalized = np.clip(samples.astype(np.float64) * gain, -32768, 32767).astype(np.int16)
    return normalized.tobytes()


def remove_silence(
    audio: bytes,
    sample_rate: int = 16000,
    energy_threshold: float = 200.0,
    min_silence_ms: int = 300,
) -> bytes:
    """
    Remove silence segments from audio, keeping non-silent parts.

    Args:
        audio: Raw 16-bit PCM audio bytes.
        sample_rate: Sample rate in Hz.
        energy_threshold: RMS energy below which is considered silence.
        min_silence_ms: Minimum silence duration in milliseconds to remove.

    Returns:
        Audio with long silence segments removed.
    """
    if len(audio) < 2:
        return audio

    samples = np.frombuffer(audio, dtype=np.int16).astype(np.float64)
    chunk_size = int(sample_rate * min_silence_ms / 1000)
    if chunk_size < 1:
        chunk_size = 1

    result_chunks = []
    in_silence = False
    silence_start = 0
    current_speech_start = 0

    for i in range(0, len(samples), chunk_size):
        chunk = samples[i : i + chunk_size]
        if chunk.size == 0:
            break
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        is_silent = rms < energy_threshold

        if is_silent and not in_silence:
            in_silence = True
            silence_start = i
            result_chunks.append(samples[current_speech_start:i].astype(np.int16))
        elif not is_silent and in_silence:
            in_silence = False
            silence_len = i - silence_start
            if silence_len < chunk_size * 3:
                result_chunks.append(samples[silence_start:i].astype(np.int16))
            current_speech_start = i

    if not in_silence and len(samples) > current_speech_start:
        result_chunks.append(samples[current_speech_start:].astype(np.int16))
    elif in_silence:
        silence_len = len(samples) - silence_start
        if silence_len < chunk_size * 3:
            result_chunks.append(samples[silence_start:].astype(np.int16))

    if not result_chunks:
        return audio

    return np.concatenate(result_chunks).tobytes()


def calculate_energy(audio: bytes) -> float:
    """
    Calculate the RMS energy of audio data.

    Args:
        audio: Raw 16-bit PCM audio bytes.

    Returns:
        RMS energy value.
    """
    if len(audio) < 2:
        return 0.0
    samples = np.frombuffer(audio, dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples ** 2)))
