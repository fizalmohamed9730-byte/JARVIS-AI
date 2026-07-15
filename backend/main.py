"""JARVIS – main FastAPI application."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.logging_config import setup_logging
from config.settings import settings
from database.connection import close_db, init_db
from backend.middleware.cors import setup_cors
from backend.middleware.rate_limiter import RateLimiterMiddleware
from backend.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    setup_logging()
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Database
    await init_db()
    logger.info("Database initialized.")

    # Redis (optional – don't crash if unavailable)
    try:
        import redis.asyncio as aioredis
        app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await app.state.redis.ping()
        logger.info("Redis connected at %s", settings.redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) – running without cache.", exc)
        app.state.redis = None

    # Background tasks
    bg_task = asyncio.create_task(_background_reminder_checker())

    # Ensure data dirs exist
    for d in [settings.data_dir, settings.chromadb_persist_directory, settings.log_dir]:
        Path(d).mkdir(parents=True, exist_ok=True)

    # Warm up ChromaDB in background so first memory request isn't slow
    def _warm_chroma():
        try:
            from backend.api.memory_routes import _get_chroma
            _get_chroma()
            logger.info("ChromaDB initialized.")
        except Exception as exc:
            logger.warning("ChromaDB warm-up skipped: %s", exc)
    import concurrent.futures
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _warm_chroma)

    logger.info("JARVIS is ready.")
    yield

    # Shutdown
    bg_task.cancel()
    try:
        await bg_task
    except asyncio.CancelledError:
        pass
    if app.state.redis:
        await app.state.redis.aclose()
    await close_db()
    logger.info("JARVIS shutdown complete.")


async def _background_reminder_checker() -> None:
    """Periodically check for due reminders and log them."""
    while True:
        try:
            from database.connection import async_session_factory
            from database.models import Reminder
            from sqlalchemy import select

            now = datetime.now(timezone.utc)
            async with async_session_factory() as session:
                q = select(Reminder).where(
                    Reminder.is_completed.is_(False),
                    Reminder.trigger_at <= now,
                )
                result = await session.execute(q)
                due = result.scalars().all()
                for r in due:
                    logger.info("⏰ Reminder due: '%s' (user %s)", r.title, r.user_id)
                    r.is_completed = True
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Reminder checker error: %s", exc)
        await asyncio.sleep(30)


# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="JARVIS – Your personal AI assistant backend.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Middleware
setup_cors(app)
app.add_middleware(RateLimiterMiddleware, requests_per_window=120, window_seconds=60)

# Static files
static_dir = Path(settings.static_dir)
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Routers ──────────────────────────────────────────────────────────────

from backend.api.auth import router as auth_router
from backend.api.conversations import router as conversations_router
from backend.api.tasks import router as tasks_router
from backend.api.notes import router as notes_router
from backend.api.reminders import router as reminders_router
from backend.api.email_routes import router as email_router
from backend.api.calendar_routes import router as calendar_router
from backend.api.memory_routes import router as memory_router
from backend.api.voice_routes import router as voice_router
from backend.api.automation_routes import router as automation_router
from backend.api.health import router as health_router
from backend.api.settings import router as settings_router
from backend.api.files_routes import router as files_router
from backend.api.image_routes import router as image_router
from backend.api.website_routes import router as website_router
from backend.api.video_routes import router as video_router

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(conversations_router, prefix=API_PREFIX)
app.include_router(tasks_router, prefix=API_PREFIX)
app.include_router(notes_router, prefix=API_PREFIX)
app.include_router(reminders_router, prefix=API_PREFIX)
app.include_router(email_router, prefix=API_PREFIX)
app.include_router(calendar_router, prefix=API_PREFIX)
app.include_router(memory_router, prefix=API_PREFIX)
app.include_router(voice_router, prefix=API_PREFIX)
app.include_router(automation_router, prefix=API_PREFIX)
app.include_router(health_router)
app.include_router(settings_router, prefix=API_PREFIX)
app.include_router(files_router, prefix=API_PREFIX)
app.include_router(image_router, prefix=API_PREFIX)
app.include_router(website_router, prefix=API_PREFIX)
app.include_router(video_router, prefix=API_PREFIX)


# ── WebSocket ────────────────────────────────────────────────────────────

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """General-purpose WebSocket endpoint for real-time updates."""
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            if msg_type == "ping":
                await ws_manager.send_to_user(user_id, {"type": "pong"})
            elif msg_type == "join_room":
                room = data.get("room", "general")
                ws_manager.join_room(user_id, room)
                await ws_manager.send_to_user(user_id, {"type": "joined_room", "room": room})
            elif msg_type == "leave_room":
                room = data.get("room", "general")
                ws_manager.leave_room(user_id, room)
                await ws_manager.send_to_user(user_id, {"type": "left_room", "room": room})
            elif msg_type == "room_message":
                room = data.get("room", "general")
                message = data.get("message", "")
                await ws_manager.broadcast_to_room(
                    room,
                    {"type": "room_message", "room": room, "user_id": user_id, "message": message},
                    exclude=user_id,
                )
            elif msg_type == "broadcast":
                await ws_manager.broadcast(
                    {"type": "broadcast", "user_id": user_id, "message": data.get("message", "")},
                    exclude=user_id,
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)
    except Exception as exc:
        logger.error("WebSocket error for user %s: %s", user_id, exc)
        ws_manager.disconnect(user_id)


# ── Root ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
