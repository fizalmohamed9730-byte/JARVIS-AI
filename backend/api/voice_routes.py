"""Voice routes for speech-to-text, text-to-speech, and real-time streaming."""

from __future__ import annotations

import io
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.schemas.schemas import VoiceCommand, VoiceResponse
from config.settings import settings
from database.connection import get_db
from database.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])


# ── Speech-to-Text ───────────────────────────────────────────────────────

async def _transcribe_audio(audio_bytes: bytes, language: str = "en") -> str:
    """Transcribe audio bytes using faster-whisper."""
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        segments, info = model.transcribe(tmp_path, language=language)
        text = " ".join(seg.text for seg in segments)
        Path(tmp_path).unlink(missing_ok=True)
        return text.strip()
    except ImportError:
        logger.warning("faster-whisper not installed, falling back to stub")
        return "[transcription unavailable – install faster-whisper]"
    except Exception as exc:
        logger.error("Transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")


# ── Text-to-Speech ──────────────────────────────────────────────────────

async def _synthesize_speech(text: str) -> bytes:
    """Convert text to speech using Piper TTS."""
    try:
        from piper import PiperVoice

        voice = PiperVoice.load(settings.piper_tts_model_path)
        wav_buffer = io.BytesIO()
        voice.synthesize(text, wav_buffer)
        return wav_buffer.getvalue()
    except ImportError:
        logger.warning("piper-tts not installed")
        return b""
    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        return b""


# ── Routes ───────────────────────────────────────────────────────────────

@router.post("/command", response_model=VoiceResponse)
async def process_voice_command(
    body: VoiceCommand,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process a voice command: transcribe intent and return AI response."""
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty voice command")

    # Route the command through AI service
    try:
        from backend.services.ai_service import ai_service

        messages = [
            {"role": "system", "content": "You are JARVIS, an AI assistant. Process the user's voice command and respond concisely."},
            {"role": "user", "content": text},
        ]
        response_text = ""
        async for chunk in ai_service.stream_chat(messages):
            response_text += chunk

        # Synthesize speech response
        audio_bytes = await _synthesize_speech(response_text)
        audio_path = None
        if audio_bytes:
            audio_dir = Path(settings.data_dir) / "voice_responses"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = str(audio_dir / f"response_{current_user.id}.wav")
            Path(audio_path).write_bytes(audio_bytes)

        return VoiceResponse(
            text=response_text,
            action="voice_response",
            audio_path=audio_path,
        )
    except Exception as exc:
        logger.error("Voice command processing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transcribe", response_model=Dict[str, str])
async def transcribe_audio_file(
    file: UploadFile,
    language: str = "en",
    current_user: User = Depends(get_current_user),
):
    """Transcribe an uploaded audio file to text."""
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    audio_bytes = await file.read()
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large (max 25 MB)")
    text = await _transcribe_audio(audio_bytes, language)
    return {"transcription": text}


@router.get("/status")
async def voice_status():
    """Return status of voice subsystems."""
    whisper_ok = False
    piper_ok = False
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        whisper_ok = True
    except ImportError:
        pass
    try:
        from piper import PiperVoice  # noqa: F401
        piper_ok = True
    except ImportError:
        pass
    return {
        "whisper_available": whisper_ok,
        "whisper_model": settings.whisper_model_size,
        "piper_available": piper_ok,
        "wake_word": settings.wake_word,
        "language": settings.voice_language,
    }


# ── WebSocket Streaming ─────────────────────────────────────────────────

@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    """Real-time voice streaming via WebSocket.

    Client sends audio chunks as binary frames; server replies with
    transcribed text and AI response as JSON text frames.
    """
    await websocket.accept()
    logger.info("Voice WebSocket connected")
    audio_buffer = bytearray()
    try:
        while True:
            data = await websocket.receive()
            if data["type"] == "websocket.receive":
                if "bytes" in data and data["bytes"]:
                    audio_buffer.extend(data["bytes"])
                elif "text" in data:
                    msg = json.loads(data["text"])
                    command = msg.get("command", "")
                    if command == "transcribe":
                        text = await _transcribe_audio(bytes(audio_buffer))
                        audio_buffer.clear()
                        await websocket.send_json({"type": "transcription", "text": text})
                    elif command == "process":
                        user_text = msg.get("text", "")
                        try:
                            from backend.services.ai_service import ai_service

                            messages = [{"role": "user", "content": user_text}]
                            response = ""
                            async for chunk in ai_service.stream_chat(messages):
                                response += chunk
                                await websocket.send_json({"type": "stream", "chunk": chunk})
                            await websocket.send_json({"type": "done", "full_response": response})
                        except Exception as exc:
                            await websocket.send_json({"type": "error", "detail": str(exc)})
                    elif command == "ping":
                        await websocket.send_json({"type": "pong"})
            elif data["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as exc:
        logger.error("Voice WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
