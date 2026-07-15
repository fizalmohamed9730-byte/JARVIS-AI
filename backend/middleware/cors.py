"""CORS middleware setup."""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from config.settings import settings


def setup_cors(app: FastAPI) -> None:
    """Add CORS middleware to the FastAPI application."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )
