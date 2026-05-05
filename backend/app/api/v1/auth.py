"""Auth router: Google sign-in exchange, refresh, logout, me."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_expires_at,
    hash_token,
    verify_firebase_id_token,
)
from app.crud.users import (
    create_session,
    create_user_from_firebase,
    get_active_session_by_hash,
    get_user_by_provider,
    revoke_all_user_sessions,
    revoke_session,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    GoogleAuthRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
async def auth_google(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Exchange a Firebase ID token for backend JWT tokens."""
    try:
        claims = await verify_firebase_id_token(body.id_token)
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        raise UnauthorizedError("Invalid Firebase ID token") from None

    firebase_uid: str = claims["uid"]
    email: str = claims.get("email", "")
    display_name: str = claims.get("name", email.split("@")[0])
    photo_url: str | None = claims.get("picture")

    # Find or create user
    user = await get_user_by_provider(db, provider="google", provider_uid=firebase_uid)
    if user is None:
        user = await create_user_from_firebase(
            db,
            email=email,
            display_name=display_name,
            photo_url=photo_url,
            provider="google",
            provider_uid=firebase_uid,
        )

    # Issue tokens
    access_token = create_access_token(user.id)
    raw_refresh, refresh_hash = create_refresh_token(user.id)
    await create_session(
        db,
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        expires_at=get_refresh_token_expires_at(),
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            photo_url=user.photo_url,
            role=user.role.value,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def auth_refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Exchange a refresh token for new access + refresh tokens (rotation)."""
    token_hash = hash_token(body.refresh_token)
    session = await get_active_session_by_hash(db, token_hash)
    if session is None:
        raise UnauthorizedError("Invalid or expired refresh token")

    # Revoke old session (rotation)
    await revoke_session(db, session)

    # Issue new tokens
    access_token = create_access_token(session.user_id)
    raw_refresh, new_hash = create_refresh_token(session.user_id)
    await create_session(
        db,
        user_id=session.user_id,
        refresh_token_hash=new_hash,
        expires_at=get_refresh_token_expires_at(),
    )
    await db.commit()

    # Fetch user for response
    from sqlalchemy import select

    from app.db.models import User as UserModel
    result = await db.execute(select(UserModel).where(UserModel.id == session.user_id))
    user = result.scalar_one()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            display_name=user.display_name,
            photo_url=user.photo_url,
            role=user.role.value,
        ),
    )


@router.post("/logout", status_code=204)
async def auth_logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke all sessions for the current user."""
    await revoke_all_user_sessions(db, user.id)
    await db.commit()


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the current authenticated user."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        photo_url=user.photo_url,
        role=user.role.value,
    )
