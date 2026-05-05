"""Stocks router — recommendations, shark deals, instrument details."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.crud.deals import get_shark_deals
from app.db.models import Instrument, Recommendation, User
from app.db.session import get_db
from app.schemas.stocks import (
    ClosedTradeResponse,
    PaginatedClosedTrades,
    PaginatedDeals,
    PaginatedRecommendations,
    RecommendationResponse,
    SharkDealResponse,
)
from app.services.closed_trades import get_closed_trades

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/recommendations", response_model=PaginatedRecommendations)
async def list_recommendations(
    horizon: str = Query(..., pattern="^(short|mid|long)$"),
    status: str = Query("active", pattern="^(active|superseded|closed)$"),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedRecommendations:
    """List recommendations filtered by horizon and status."""
    query = (
        select(Recommendation, Instrument.name, Instrument.exchange)
        .join(Instrument, Recommendation.instrument_id == Instrument.id)
        .where(Recommendation.horizon == horizon)
        .where(Recommendation.status == status)
        .order_by(Recommendation.created_at.desc())
    )

    if cursor:
        query = query.where(Recommendation.created_at < cursor)

    query = query.limit(limit)
    result = await db.execute(query)

    items = []
    for row in result.all():
        rec = row[0]
        inst_name = row[1]
        inst_exchange = row[2]
        items.append(RecommendationResponse(
            id=str(rec.id),
            instrument_name=inst_name,
            exchange=inst_exchange.value,
            action=rec.action.value,
            entry=rec.entry,
            target=rec.target,
            stoploss=rec.stoploss,
            confidence=rec.confidence,
            rationale=rec.rationale,
            risk_factors=rec.risk_factors or [],
            horizon=rec.horizon.value,
            created_at=rec.created_at.isoformat(),
        ))

    next_cursor = None
    if len(items) == limit and items:
        next_cursor = items[-1].created_at

    return PaginatedRecommendations(items=items, cursor=next_cursor)


@router.get("/shark-deals", response_model=PaginatedDeals)
async def list_shark_deals(
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    investor: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedDeals:
    """List bulk/block deals (shark activity). Supports pagination and filtering."""
    deals = await get_shark_deals(
        db,
        from_date=from_date,
        to_date=to_date,
        investor=investor,
        cursor=cursor,
        limit=limit,
    )

    next_cursor = None
    if len(deals) == limit and deals:
        next_cursor = deals[-1]["ts"]

    return PaginatedDeals(
        items=[SharkDealResponse(**d) for d in deals],
        cursor=next_cursor,
    )


@router.get("/closed-trades", response_model=PaginatedClosedTrades)
async def list_closed_trades(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedClosedTrades:
    """List closed trades with PnL information."""
    trades = await get_closed_trades(db, cursor=cursor, limit=limit)

    next_cursor = None
    if len(trades) == limit and trades:
        next_cursor = trades[-1]["closed_at"]

    return PaginatedClosedTrades(
        items=[ClosedTradeResponse(**t) for t in trades],
        cursor=next_cursor,
    )
