"""Rate limiting middleware using Redis or in-memory fallback."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config.settings import settings

logger = logging.getLogger(__name__)

_memory_hits: Dict[str, list[float]] = defaultdict(list)
_last_cleanup: float = time.time()
_CLEANUP_INTERVAL = 300  # seconds


def _cleanup_memory_hits() -> None:
    """Evict stale entries from the in-memory rate limiter to prevent memory leaks."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < _CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    stale_keys = [
        key for key, timestamps in _memory_hits.items()
        if not timestamps or timestamps[-1] < now - 600
    ]
    for key in stale_keys:
        del _memory_hits[key]
    if stale_keys:
        logger.debug("Cleaned up %d stale rate-limit entries", len(stale_keys))


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter.

    Configure via ``rate_limit_requests`` and ``rate_limit_window`` (seconds).
    """

    def __init__(
        self,
        app,
        requests_per_window: int = 100,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._redis = None

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(settings.redis_url, socket_timeout=3)
                await self._redis.ping()
            except Exception:
                self._redis = False
        return self._redis if self._redis is not False else None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in ("/health", "/health/detailed", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"
        now = time.time()
        window_start = now - self.window_seconds

        redis = await self._get_redis()
        if redis:
            try:
                pipe = redis.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, self.window_seconds)
                results = await pipe.execute()
                request_count = results[2]
            except Exception:
                request_count = self._check_memory(key, window_start, now)
        else:
            _cleanup_memory_hits()
            request_count = self._check_memory(key, window_start, now)

        remaining = max(0, self.requests_per_window - request_count)
        if request_count > self.requests_per_window:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(self.window_seconds),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _check_memory(self, key: str, window_start: float, now: float) -> int:
        _memory_hits[key] = [t for t in _memory_hits[key] if t > window_start]
        _memory_hits[key].append(now)
        return len(_memory_hits[key])
