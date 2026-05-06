"""JWT auth dependency for FastAPI routes."""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.models import User, UserRole
from app.db.session import get_db

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT, return the authenticated User.

    Also supports a static API_AUTH_TOKEN for dev/test usage.
    """
    if credentials is None:
        raise UnauthorizedError("Missing authorization header")

    token = credentials.credentials

    # Static token bypass (dev/test)
    if settings.api_auth_token and token == settings.api_auth_token:
        result = await db.execute(
            select(User).where(User.role == UserRole.admin).limit(1)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UnauthorizedError("No admin user found for token-based auth")
        return user

    # Standard JWT flow
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise UnauthorizedError() from None

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError()

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("User no longer exists")

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Ensure the current user has admin role."""
    if user.role != UserRole.admin:
        raise ForbiddenError()
    return user
