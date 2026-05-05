"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("photo_url", sa.String(2048)),
        sa.Column("role", sa.Enum("user", "admin", name="userrole"), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- auth_providers ---
    op.create_table(
        "auth_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_uid", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_uid", name="uq_auth_provider_uid"),
    )

    # --- sessions ---
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- instruments ---
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.Enum("NSE", "BSE", name="exchange"), nullable=False),
        sa.Column("isin", sa.String(12)),
        sa.Column("sector", sa.String(200)),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("symbol", "exchange", name="uq_instrument_symbol_exchange"),
    )

    # --- price_ticks ---
    op.create_table(
        "price_ticks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("volume", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_price_ticks_instrument_ts", "price_ticks", ["instrument_id", "ts"])

    # --- bulk_deals ---
    op.create_table(
        "bulk_deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("party_name", sa.String(500), nullable=False),
        sa.Column("side", sa.Enum("BUY", "SELL", name="dealside"), nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("avg_price", sa.Float, nullable=False),
        sa.Column("pct_equity", sa.Float),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bulk_deals_ts", "bulk_deals", ["ts"])
    op.create_index("ix_bulk_deals_party", "bulk_deals", ["party_name"])

    # --- block_deals ---
    op.create_table(
        "block_deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("party_name", sa.String(500), nullable=False),
        sa.Column("side", sa.Enum("BUY", "SELL", name="dealside"), nullable=False),
        sa.Column("qty", sa.Integer, nullable=False),
        sa.Column("avg_price", sa.Float, nullable=False),
        sa.Column("pct_equity", sa.Float),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_block_deals_ts", "block_deals", ["ts"])
    op.create_index("ix_block_deals_party", "block_deals", ["party_name"])

    # --- notable_investors ---
    op.create_table(
        "notable_investors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("normalized_name", sa.String(500), unique=True, nullable=False),
        sa.Column("aliases", postgresql.JSONB),
        sa.Column("tags", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- news ---
    op.create_table(
        "news",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id", ondelete="RESTRICT")),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_news_ts", "news", ["ts"])

    # --- corporate_actions ---
    op.create_table(
        "corporate_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("type", sa.Enum("merger", "demerger", "split", "dividend", "bonus", name="corporateactiontype"), nullable=False),
        sa.Column("details", postgresql.JSONB),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- recommendations ---
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("horizon", sa.Enum("short", "mid", "long", name="horizon"), nullable=False),
        sa.Column("action", sa.Enum("BUY", "SELL", "HOLD", name="recommendationaction"), nullable=False),
        sa.Column("entry", sa.Float, nullable=False),
        sa.Column("target", sa.Float, nullable=False),
        sa.Column("stoploss", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("risk_factors", postgresql.JSONB),
        sa.Column("llm_meta", postgresql.JSONB),
        sa.Column("status", sa.Enum("active", "superseded", "closed", name="recommendationstatus"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recommendations_active", "recommendations", ["status", "horizon", "created_at"])

    # --- closed_trades ---
    op.create_table(
        "closed_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recommendations.id", ondelete="RESTRICT"), unique=True, nullable=False),
        sa.Column("exit_price", sa.Float, nullable=False),
        sa.Column("exit_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pnl_pct", sa.Float, nullable=False),
        sa.Column("close_reason", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- scheduler_runs ---
    op.create_table(
        "scheduler_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.String(200), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Enum("running", "success", "failed", name="schedulerrunstatus"), nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("items_ingested", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scheduler_runs_job_started", "scheduler_runs", ["job_name", "started_at"])

    # --- raw_payloads ---
    op.create_table(
        "raw_payloads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, index=True),
        sa.Column("payload", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("raw_payloads")
    op.drop_table("scheduler_runs")
    op.drop_table("closed_trades")
    op.drop_table("recommendations")
    op.drop_table("corporate_actions")
    op.drop_table("news")
    op.drop_table("notable_investors")
    op.drop_table("block_deals")
    op.drop_table("bulk_deals")
    op.drop_table("price_ticks")
    op.drop_table("instruments")
    op.drop_table("sessions")
    op.drop_table("auth_providers")
    op.drop_table("users")

    # Drop enums
    for enum_name in [
        "userrole", "exchange", "dealside", "horizon",
        "recommendationaction", "recommendationstatus",
        "schedulerrunstatus", "corporateactiontype",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
