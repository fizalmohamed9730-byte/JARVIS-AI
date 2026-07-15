"""Health check routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends

from config.settings import settings
from backend.schemas.schemas import DetailedHealthResponse, HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


async def _check_database() -> str:
    """Ping the database."""
    try:
        import sqlalchemy
        from database.connection import engine

        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        return "healthy"
    except Exception as exc:
        return f"unhealthy: {exc}"


async def _check_redis() -> str:
    """Ping Redis."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_timeout=3)
        await r.ping()
        await r.aclose()
        return "healthy"
    except Exception as exc:
        return f"unhealthy: {exc}"


async def _check_ai_services() -> Dict[str, str]:
    """Check AI service availability."""
    results: Dict[str, str] = {}
    # Check Ollama
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            results["ollama"] = "healthy" if resp.status_code == 200 else f"status {resp.status_code}"
    except Exception as exc:
        results["ollama"] = f"unhealthy: {exc}"

    # Check OpenAI key presence
    if settings.openai_api_key:
        results["openai"] = "configured"
    else:
        results["openai"] = "not_configured"

    return results


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check including database, Redis, and AI services."""
    db_status = await _check_database()
    redis_status = await _check_redis()
    ai_status = await _check_ai_services()

    overall = "healthy"
    if "unhealthy" in db_status or "unhealthy" in redis_status:
        overall = "degraded"

    return DetailedHealthResponse(
        status=overall,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
        database=db_status,
        redis=redis_status,
        ai_services=ai_status,
    )
