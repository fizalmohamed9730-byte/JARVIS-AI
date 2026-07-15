"""Central configuration for JARVIS using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "JARVIS"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./jarvis.db"
    postgres_url: Optional[str] = None
    sqlite_url: str = "sqlite+aiosqlite:///./jarvis.db"

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── OpenAI ───────────────────────────────────────────────────────────
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"

    # ── Ollama ───────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # ── JWT ──────────────────────────────────────────────────────────────
    jwt_secret: str = "CHANGE-ME-IN-PRODUCTION-USE-A-REAL-SECRET"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 10080

    # ── Email ────────────────────────────────────────────────────────────
    email_imap_server: str = "imap.gmail.com"
    email_imap_port: int = 993
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_address: Optional[str] = None
    email_password: Optional[str] = None

    # ── Google Calendar ──────────────────────────────────────────────────
    google_calendar_credentials_path: str = str(
        PROJECT_ROOT / "credentials" / "google_calendar.json"
    )
    google_calendar_id: str = "primary"

    # ── Whisper ──────────────────────────────────────────────────────────
    whisper_model_size: str = "base"

    # ── Piper TTS ────────────────────────────────────────────────────────
    piper_tts_model_path: str = str(
        PROJECT_ROOT / "models" / "piper" / "en_US-lessac-medium.onnx"
    )

    # ── Porcupine Wake Word ──────────────────────────────────────────────
    porcupine_access_key: Optional[str] = None

    # ── Vector Stores ────────────────────────────────────────────────────
    chromadb_persist_directory: str = str(PROJECT_ROOT / "data" / "chromadb")
    faiss_index_path: str = str(PROJECT_ROOT / "data" / "faiss")

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"]
    )

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_dir: str = str(PROJECT_ROOT / "logs")

    # ── Voice ────────────────────────────────────────────────────────────
    wake_word: str = "jarvis"
    voice_language: str = "en-US"
    energy_threshold: int = 300
    sample_rate: int = 16000

    # ── Paths ────────────────────────────────────────────────────────────
    models_dir: str = str(PROJECT_ROOT / "models")
    data_dir: str = str(PROJECT_ROOT / "data")
    static_dir: str = str(PROJECT_ROOT / "static")

    @field_validator("postgres_url", mode="before")
    @classmethod
    def resolve_database_url(cls, v: Optional[str], info) -> str:
        """Use PostgreSQL if provided, otherwise fall back to SQLite."""
        data = info.data
        if v:
            return v
        return data.get("sqlite_url", "sqlite+aiosqlite:///./jarvis.db")

    @property
    def effective_database_url(self) -> str:
        """Return the best available database URL."""
        if self.postgres_url:
            return self.postgres_url
        return self.database_url

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL."""
        return "postgresql" in self.effective_database_url


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


settings = get_settings()
