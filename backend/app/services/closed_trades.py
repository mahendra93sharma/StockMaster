"""Closed trades service — monitors active recommendations and closes positions.

Logic:
- For each active recommendation, check if current price hit target or stoploss.
- If target hit → close with profit, record PnL.
- If stoploss hit → close with loss, record PnL.
- Recommendations can also be manually closed by admin.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ClosedTrade,
    Instrument,
    PriceTick,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
)

logger = logging.getLogger(__name__)


async def _get_latest_price(db: AsyncSession, instrument_id) -> float | None:
    """Get the most recent price for an instrument."""
    result = await db.execute(
        select(PriceTick.close)
        .where(PriceTick.instrument_id == instrument_id)
        .order_by(PriceTick.ts.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row else None


def _calculate_pnl(action: RecommendationAction, entry: float, exit_price: float) -> float:
    """Calculate PnL percentage based on action direction."""
    if action == RecommendationAction.BUY:
        return round(((exit_price - entry) / entry) * 100, 2)
    elif action == RecommendationAction.SELL:
        return round(((entry - exit_price) / entry) * 100, 2)
    return 0.0


async def close_recommendation(
    db: AsyncSession,
    recommendation: Recommendation,
    exit_price: float,
    reason: str,
) -> ClosedTrade:
    """Close a recommendation and record the trade."""
    pnl = _calculate_pnl(recommendation.action, recommendation.entry, exit_price)

    closed_trade = ClosedTrade(
        recommendation_id=recommendation.id,
        exit_price=exit_price,
        exit_ts=datetime.now(UTC),
        pnl_pct=pnl,
        close_reason=reason,
    )
    db.add(closed_trade)

    recommendation.status = RecommendationStatus.closed
    await db.flush()

    logger.info(
        "Closed recommendation %s: %s @ %.2f → %.2f (PnL: %.2f%%)",
        recommendation.id,
        reason,
        recommendation.entry,
        exit_price,
        pnl,
    )
    return closed_trade


async def check_and_close_positions(db: AsyncSession) -> int:
    """Check all active recommendations against current prices.

    Returns count of positions closed.
    """
    result = await db.execute(
        select(Recommendation)
        .where(Recommendation.status == RecommendationStatus.active)
    )
    active_recs = result.scalars().all()

    closed_count = 0
    for rec in active_recs:
        price = await _get_latest_price(db, rec.instrument_id)
        if price is None:
            continue

        # Check target hit
        if rec.action == RecommendationAction.BUY and price >= rec.target or rec.action == RecommendationAction.SELL and price <= rec.target:
            await close_recommendation(db, rec, price, "Target price reached")
            closed_count += 1
        # Check stoploss hit
        elif rec.action == RecommendationAction.BUY and price <= rec.stoploss or rec.action == RecommendationAction.SELL and price >= rec.stoploss:
            await close_recommendation(db, rec, price, "Stop-loss triggered")
            closed_count += 1

    if closed_count > 0:
        await db.flush()

    return closed_count


async def get_closed_trades(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Fetch closed trades with recommendation + instrument details."""
    query = (
        select(ClosedTrade, Recommendation, Instrument.name, Instrument.exchange)
        .join(Recommendation, ClosedTrade.recommendation_id == Recommendation.id)
        .join(Instrument, Recommendation.instrument_id == Instrument.id)
        .order_by(ClosedTrade.exit_ts.desc())
    )

    if cursor:
        query = query.where(ClosedTrade.exit_ts < cursor)

    query = query.limit(limit)
    result = await db.execute(query)

    trades = []
    for row in result.all():
        ct = row[0]
        rec = row[1]
        inst_name = row[2]
        inst_exchange = row[3]

        trades.append({
            "id": str(ct.id),
            "instrument_name": inst_name,
            "exchange": inst_exchange.value,
            "action": rec.action.value,
            "entry": rec.entry,
            "exit_price": ct.exit_price,
            "pnl_pct": ct.pnl_pct,
            "close_reason": ct.close_reason,
            "horizon": rec.horizon.value,
            "closed_at": ct.exit_ts.isoformat(),
        })

    return trades
