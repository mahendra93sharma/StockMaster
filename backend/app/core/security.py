"""Security utilities: JWT creation/verification, password hashing, Firebase token verification."""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = settings.jwt_algorithm


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a short-lived access token."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    """Create a refresh token and return (raw_token, token_hash)."""
    raw_token = uuid.uuid4().hex + uuid.uuid4().hex  # 64-char random
    token_hash = hash_token(raw_token)
    return raw_token, token_hash


def hash_token(token: str) -> str:
    """HMAC-SHA256 hash a token for storage."""
    return hmac.HMAC(
        key=settings.jwt_secret_key.encode(),
        msg=token.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def decode_access_token(token: str) -> dict:
    """Decode and verify an access token. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def get_refresh_token_expires_at() -> datetime:
    """Get the expiry datetime for a new refresh token."""
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)


async def verify_firebase_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return decoded claims.

    Returns dict with keys: uid, email, name, picture, etc.
    """
    from firebase_admin import auth as firebase_auth

    decoded = firebase_auth.verify_id_token(id_token)
    return decoded
