"""Home feed router — aggregated recent activity for the app's Home tab."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.models import (
    BlockDeal,
    BulkDeal,
    CorporateAction,
    Instrument,
    News,
    Recommendation,
    RecommendationStatus,
    User,
)
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/home")
async def home_feed(
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregated home feed: latest deals, news, recommendations, and corporate actions.

    Returns items sorted by timestamp (most recent first).
    """
    cutoff = datetime.now(UTC) - timedelta(days=7)
    items: list[dict] = []

    # Latest bulk deals (top notable ones)
    bulk_result = await db.execute(
        select(BulkDeal, Instrument.name, Instrument.symbol)
        .join(Instrument, BulkDeal.instrument_id == Instrument.id)
        .where(BulkDeal.ts >= cutoff)
        .order_by(BulkDeal.ts.desc())
        .limit(10)
    )
    for row in bulk_result.all():
        deal = row[0]
        items.append({
            "type": "bulk_deal",
            "ts": deal.ts.isoformat(),
            "title": f"{deal.party_name} {'bought' if deal.side.value == 'BUY' else 'sold'} {deal.qty:,} shares",
            "subtitle": f"{row[1]} ({row[2]})",
            "meta": {
                "side": deal.side.value,
                "qty": deal.qty,
                "price": deal.avg_price,
                "party": deal.party_name,
            },
        })

    # Latest block deals
    block_result = await db.execute(
        select(BlockDeal, Instrument.name, Instrument.symbol)
        .join(Instrument, BlockDeal.instrument_id == Instrument.id)
        .where(BlockDeal.ts >= cutoff)
        .order_by(BlockDeal.ts.desc())
        .limit(10)
    )
    for row in block_result.all():
        deal = row[0]
        items.append({
            "type": "block_deal",
            "ts": deal.ts.isoformat(),
            "title": f"{deal.party_name} {'bought' if deal.side.value == 'BUY' else 'sold'} {deal.qty:,} shares",
            "subtitle": f"{row[1]} ({row[2]})",
            "meta": {
                "side": deal.side.value,
                "qty": deal.qty,
                "price": deal.avg_price,
                "party": deal.party_name,
            },
        })

    # Latest news
    news_result = await db.execute(
        select(News)
        .where(News.ts >= cutoff)
        .order_by(News.ts.desc())
        .limit(10)
    )
    for news in news_result.scalars().all():
        items.append({
            "type": "news",
            "ts": news.ts.isoformat(),
            "title": news.title,
            "subtitle": news.source,
            "meta": {"url": news.url},
        })

    # Latest recommendations
    rec_result = await db.execute(
        select(Recommendation, Instrument.name, Instrument.symbol)
        .join(Instrument, Recommendation.instrument_id == Instrument.id)
        .where(Recommendation.status == RecommendationStatus.active)
        .where(Recommendation.created_at >= cutoff)
        .order_by(Recommendation.created_at.desc())
        .limit(10)
    )
    for row in rec_result.all():
        rec = row[0]
        items.append({
            "type": "recommendation",
            "ts": rec.created_at.isoformat(),
            "title": f"{rec.action.value} {row[1]} ({rec.horizon.value}-term)",
            "subtitle": f"Target ₹{rec.target:.0f} | Confidence {rec.confidence * 100:.0f}%",
            "meta": {
                "action": rec.action.value,
                "horizon": rec.horizon.value,
                "confidence": rec.confidence,
                "entry": rec.entry,
                "target": rec.target,
            },
        })

    # Corporate actions
    ca_result = await db.execute(
        select(CorporateAction, Instrument.name, Instrument.symbol)
        .join(Instrument, CorporateAction.instrument_id == Instrument.id)
        .order_by(CorporateAction.effective_date.desc())
        .limit(5)
    )
    for row in ca_result.all():
        ca = row[0]
        items.append({
            "type": "corporate_action",
            "ts": datetime.combine(ca.effective_date, datetime.min.time(), tzinfo=UTC).isoformat(),
            "title": f"{ca.type.value.title()}: {row[1]}",
            "subtitle": ca.details.get("purpose", "") if ca.details else "",
            "meta": {"type": ca.type.value, "effective_date": ca.effective_date.isoformat()},
        })

    # Sort all items by timestamp (most recent first), take top N
    items.sort(key=lambda x: x["ts"], reverse=True)
    items = items[:limit]

    return {"items": items, "count": len(items)}
