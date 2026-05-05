"""Recommendation engine — orchestrates LLM calls + DB persistence.

Workflow:
1. Pick instruments that need fresh recommendations (based on age or deal activity).
2. Gather context (recent deals, price, news).
3. Call Claude for structured recommendations.
4. Supersede old active recommendations.
5. Persist new recommendations.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BulkDeal,
    Horizon,
    Instrument,
    News,
    PriceTick,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
)
from app.services.llm import generate_recommendations

logger = logging.getLogger(__name__)


async def _get_recent_price(db: AsyncSession, instrument_id) -> float | None:
    """Get most recent close price for an instrument."""
    result = await db.execute(
        select(PriceTick.close)
        .where(PriceTick.instrument_id == instrument_id)
        .order_by(PriceTick.ts.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row else None


async def _get_deals_context(db: AsyncSession, instrument_id, days: int = 30) -> str:
    """Build a text summary of recent bulk/block deals for the instrument."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(
        select(BulkDeal)
        .where(BulkDeal.instrument_id == instrument_id)
        .where(BulkDeal.ts >= cutoff)
        .order_by(BulkDeal.ts.desc())
        .limit(10)
    )
    deals = result.scalars().all()

    if not deals:
        return ""

    lines = []
    for d in deals:
        lines.append(
            f"- {d.ts.strftime('%Y-%m-%d')} | {d.party_name} | {d.side.value} | "
            f"Qty: {d.qty:,} | ₹{d.avg_price:.2f}"
        )
    return "\n".join(lines)


async def _get_news_context(db: AsyncSession, instrument_id, days: int = 14) -> str:
    """Build a text summary of recent news for the instrument."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(
        select(News)
        .where(News.instrument_id == instrument_id)
        .where(News.ts >= cutoff)
        .order_by(News.ts.desc())
        .limit(5)
    )
    news_items = result.scalars().all()

    if not news_items:
        return ""

    lines = []
    for n in news_items:
        summary = n.summary[:200] if n.summary else n.title
        lines.append(f"- [{n.ts.strftime('%Y-%m-%d')}] {summary} (Source: {n.source})")
    return "\n".join(lines)


async def _instruments_needing_refresh(
    db: AsyncSession, max_age_hours: int = 24, limit: int = 5
) -> list[Instrument]:
    """Find instruments whose recommendations are stale or missing.

    Priority:
    1. Instruments with no active recommendations
    2. Instruments whose latest recommendation is older than max_age_hours
    3. Instruments with recent deal activity
    """
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

    # All instruments
    all_instruments = await db.execute(select(Instrument).limit(50))
    instruments = all_instruments.scalars().all()

    needs_refresh = []
    for inst in instruments:
        # Check latest active recommendation
        latest = await db.execute(
            select(Recommendation.created_at)
            .where(Recommendation.instrument_id == inst.id)
            .where(Recommendation.status == RecommendationStatus.active)
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        latest_ts = latest.scalar_one_or_none()

        if latest_ts is None or latest_ts < cutoff:
            needs_refresh.append(inst)

        if len(needs_refresh) >= limit:
            break

    return needs_refresh


async def _supersede_active_recommendations(
    db: AsyncSession, instrument_id, horizon: str
) -> None:
    """Mark existing active recommendations as superseded."""
    await db.execute(
        update(Recommendation)
        .where(Recommendation.instrument_id == instrument_id)
        .where(Recommendation.horizon == horizon)
        .where(Recommendation.status == RecommendationStatus.active)
        .values(status=RecommendationStatus.superseded)
    )


async def generate_for_instrument(db: AsyncSession, instrument: Instrument) -> int:
    """Generate and persist recommendations for one instrument. Returns count persisted."""
    recent_price = await _get_recent_price(db, instrument.id)
    deals_context = await _get_deals_context(db, instrument.id)
    news_context = await _get_news_context(db, instrument.id)

    # If no price data, use avg_price from recent deals as estimate
    if recent_price is None:
        result = await db.execute(
            select(BulkDeal.avg_price)
            .where(BulkDeal.instrument_id == instrument.id)
            .order_by(BulkDeal.ts.desc())
            .limit(1)
        )
        deal_price = result.scalar_one_or_none()
        if deal_price:
            recent_price = float(deal_price)

    logger.info(
        "Generating recommendations for %s (price=%.2f)",
        instrument.symbol,
        recent_price or 0,
    )

    result = await generate_recommendations(
        instrument_name=instrument.name,
        symbol=instrument.symbol,
        sector=instrument.sector,
        recent_price=recent_price,
        deals_context=deals_context,
        news_context=news_context,
    )

    recommendations = result["recommendations"]
    meta = result["meta"]
    count = 0

    for rec_data in recommendations:
        horizon = rec_data["horizon"]

        # Supersede existing active recs for this instrument+horizon
        await _supersede_active_recommendations(db, instrument.id, horizon)

        rec = Recommendation(
            instrument_id=instrument.id,
            horizon=Horizon(horizon),
            action=RecommendationAction(rec_data["action"]),
            entry=rec_data["entry"],
            target=rec_data["target"],
            stoploss=rec_data["stoploss"],
            confidence=max(0.0, min(1.0, rec_data["confidence"])),
            rationale=rec_data["rationale"],
            risk_factors=rec_data.get("risk_factors", []),
            llm_meta=meta,
            status=RecommendationStatus.active,
        )
        db.add(rec)
        count += 1

    await db.flush()
    logger.info(
        "Persisted %d recommendations for %s (cost=$%.5f)",
        count,
        instrument.symbol,
        meta["cost_usd"],
    )
    return count


async def run_recommendation_pipeline(db: AsyncSession) -> int:
    """Main pipeline entry point. Returns total recommendations generated."""
    instruments = await _instruments_needing_refresh(db)

    if not instruments:
        logger.info("No instruments need recommendation refresh")
        return 0

    logger.info(
        "Generating recommendations for %d instruments: %s",
        len(instruments),
        [i.symbol for i in instruments],
    )

    total = 0
    for inst in instruments:
        try:
            count = await generate_for_instrument(db, inst)
            total += count
        except Exception as exc:
            logger.exception("Failed to generate recommendations for %s: %s", inst.symbol, exc)
            continue

    await db.commit()
    logger.info("Recommendation pipeline complete: %d total recommendations", total)
    return total
