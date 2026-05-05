"""All SQLAlchemy ORM models for StockMaster."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# ─── Enums ───────────────────────────────────────────────────────────────────


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class Exchange(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"


class DealSide(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Horizon(str, enum.Enum):
    short = "short"
    mid = "mid"
    long = "long"


class RecommendationAction(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class RecommendationStatus(str, enum.Enum):
    active = "active"
    superseded = "superseded"
    closed = "closed"


class SchedulerRunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"


class CorporateActionType(str, enum.Enum):
    merger = "merger"
    demerger = "demerger"
    split = "split"
    dividend = "dividend"
    bonus = "bonus"


class InvestorTag(str, enum.Enum):
    HNI = "HNI"
    promoter = "promoter"
    FII = "FII"


# ─── Models ──────────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(2048))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)

    auth_providers: Mapped[list[AuthProvider]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list[Session]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthProvider(Base):
    __tablename__ = "auth_providers"
    __table_args__ = (
        UniqueConstraint("provider", "provider_uid", name="uq_auth_provider_uid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_uid: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped[User] = relationship(back_populates="auth_providers")


class Session(Base):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_instrument_symbol_exchange"),
    )

    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    exchange: Mapped[Exchange] = mapped_column(Enum(Exchange), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12))
    sector: Mapped[str | None] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(300), nullable=False)

    price_ticks: Mapped[list[PriceTick]] = relationship(back_populates="instrument")
    bulk_deals: Mapped[list[BulkDeal]] = relationship(back_populates="instrument")
    block_deals: Mapped[list[BlockDeal]] = relationship(back_populates="instrument")
    news: Mapped[list[News]] = relationship(back_populates="instrument")
    corporate_actions: Mapped[list[CorporateAction]] = relationship(back_populates="instrument")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="instrument")


class PriceTick(Base):
    __tablename__ = "price_ticks"
    __table_args__ = (
        Index("ix_price_ticks_instrument_ts", "instrument_id", "ts", postgresql_using="btree"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)

    instrument: Mapped[Instrument] = relationship(back_populates="price_ticks")


class BulkDeal(Base):
    __tablename__ = "bulk_deals"
    __table_args__ = (
        Index("ix_bulk_deals_ts", "ts", postgresql_using="btree"),
        Index("ix_bulk_deals_party", "party_name", postgresql_using="btree"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    party_name: Mapped[str] = mapped_column(String(500), nullable=False)
    side: Mapped[DealSide] = mapped_column(Enum(DealSide), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    pct_equity: Mapped[float | None] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    instrument: Mapped[Instrument] = relationship(back_populates="bulk_deals")


class BlockDeal(Base):
    __tablename__ = "block_deals"
    __table_args__ = (
        Index("ix_block_deals_ts", "ts", postgresql_using="btree"),
        Index("ix_block_deals_party", "party_name", postgresql_using="btree"),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    party_name: Mapped[str] = mapped_column(String(500), nullable=False)
    side: Mapped[DealSide] = mapped_column(Enum(DealSide), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    pct_equity: Mapped[float | None] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    instrument: Mapped[Instrument] = relationship(back_populates="block_deals")


class NotableInvestor(Base):
    __tablename__ = "notable_investors"

    normalized_name: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    aliases: Mapped[dict | None] = mapped_column(JSONB)
    tags: Mapped[list | None] = mapped_column(JSONB)  # list of InvestorTag values


class News(Base):
    __tablename__ = "news"
    __table_args__ = (
        Index("ix_news_ts", "ts", postgresql_using="btree"),
    )

    instrument_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    instrument: Mapped[Instrument | None] = relationship(back_populates="news")


class CorporateAction(Base):
    __tablename__ = "corporate_actions"

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    type: Mapped[CorporateActionType] = mapped_column(Enum(CorporateActionType), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    instrument: Mapped[Instrument] = relationship(back_populates="corporate_actions")


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index(
            "ix_recommendations_active",
            "status",
            "horizon",
            "created_at",
            postgresql_using="btree",
        ),
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False
    )
    horizon: Mapped[Horizon] = mapped_column(Enum(Horizon), nullable=False)
    action: Mapped[RecommendationAction] = mapped_column(Enum(RecommendationAction), nullable=False)
    entry: Mapped[float] = mapped_column(Float, nullable=False)
    target: Mapped[float] = mapped_column(Float, nullable=False)
    stoploss: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 – 1.0
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    risk_factors: Mapped[list | None] = mapped_column(JSONB)
    llm_meta: Mapped[dict | None] = mapped_column(JSONB)  # model, prompt_hash, tokens, cost
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus), default=RecommendationStatus.active, nullable=False
    )

    instrument: Mapped[Instrument] = relationship(back_populates="recommendations")
    closed_trade: Mapped[ClosedTrade | None] = relationship(back_populates="recommendation", uselist=False)


class ClosedTrade(Base):
    __tablename__ = "closed_trades"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pnl_pct: Mapped[float] = mapped_column(Float, nullable=False)
    close_reason: Mapped[str] = mapped_column(String(500), nullable=False)

    recommendation: Mapped[Recommendation] = relationship(back_populates="closed_trade")


class SchedulerRun(Base):
    __tablename__ = "scheduler_runs"
    __table_args__ = (
        Index("ix_scheduler_runs_job_started", "job_name", "started_at", postgresql_using="btree"),
    )

    job_name: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SchedulerRunStatus] = mapped_column(Enum(SchedulerRunStatus), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    items_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RawPayload(Base):
    __tablename__ = "raw_payloads"

    source: Mapped[str] = mapped_column(String(200), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[str | None] = mapped_column(Text)  # or blob ref
