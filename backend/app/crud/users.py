"""User and auth-provider CRUD operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuthProvider, Session, User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_provider(db: AsyncSession, provider: str, provider_uid: str) -> User | None:
    result = await db.execute(
        select(User)
        .join(AuthProvider)
        .where(AuthProvider.provider == provider, AuthProvider.provider_uid == provider_uid)
    )
    return result.scalar_one_or_none()


async def create_user_from_firebase(
    db: AsyncSession,
    *,
    email: str,
    display_name: str,
    photo_url: str | None,
    provider: str,
    provider_uid: str,
) -> User:
    user = User(
        email=email,
        display_name=display_name,
        photo_url=photo_url,
    )
    db.add(user)
    await db.flush()

    auth_provider = AuthProvider(
        user_id=user.id,
        provider=provider,
        provider_uid=provider_uid,
    )
    db.add(auth_provider)
    await db.flush()
    return user


async def create_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    refresh_token_hash: str,
    expires_at: datetime,
) -> Session:
    session = Session(
        user_id=user_id,
        refresh_token_hash=refresh_token_hash,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    return session


async def get_active_session_by_hash(db: AsyncSession, token_hash: str) -> Session | None:
    result = await db.execute(
        select(Session).where(
            Session.refresh_token_hash == token_hash,
            Session.revoked_at.is_(None),
            Session.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def revoke_session(db: AsyncSession, session: Session) -> None:
    session.revoked_at = datetime.now(UTC)
    await db.flush()


async def revoke_all_user_sessions(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    )
    for session in result.scalars().all():
        session.revoked_at = datetime.now(UTC)
    await db.flush()
