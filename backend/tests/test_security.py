"""Tests for security utilities."""

import uuid
from datetime import UTC

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_refresh_token_expires_at,
)


def test_create_access_token_valid():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"
    assert "exp" in payload


def test_decode_access_token_valid():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)


def test_decode_access_token_invalid():
    from jose import JWTError

    with pytest.raises(JWTError):
        decode_access_token("not.a.valid.token")


def test_decode_access_token_wrong_type():
    from datetime import datetime, timedelta

    from jose import JWTError

    expire = datetime.now(UTC) + timedelta(minutes=15)
    payload = {"sub": str(uuid.uuid4()), "exp": expire, "type": "refresh"}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(JWTError):
        decode_access_token(token)


def test_refresh_token_expiry():
    from datetime import datetime

    expiry = get_refresh_token_expires_at()
    now = datetime.now(UTC)
    delta = expiry - now
    assert 29 <= delta.days <= 30
