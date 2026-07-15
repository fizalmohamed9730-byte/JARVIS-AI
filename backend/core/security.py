"""Security utilities: JWT, password hashing, credential encryption."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_ENCRYPTION_KEY: Optional[bytes] = None
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Lazy-init Fernet cipher using a deterministic key from jwt_secret."""
    global _ENCRYPTION_KEY, _fernet
    if _fernet is None:
        import hashlib
        raw = hashlib.sha256(settings.jwt_secret.encode()).digest()
        _ENCRYPTION_KEY = Fernet.generate_key() if False else raw  # deterministic for same secret
        # For production, use a dedicated ENCRYPTION_KEY env var.
        # Here we derive a valid Fernet key from jwt_secret.
        key = Fernet.generate_key()  # Generate once; in prod store in env
        # Simpler approach: derive from jwt_secret base64-safe
        import base64
        derived = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
        _fernet = Fernet(derived)
    return _fernet


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_refresh_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the password."""
    return pwd_context.hash(password)


def encrypt_value(plain_text: str) -> str:
    """Encrypt a string value (e.g. email password) for storage."""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_value(cipher_text: str) -> str:
    """Decrypt a previously encrypted string value."""
    f = _get_fernet()
    return f.decrypt(cipher_text.encode()).decode()


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(48)
