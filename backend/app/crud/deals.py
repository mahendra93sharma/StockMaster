"""CRUD operations for deals (bulk + block)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BulkDeal, Instrument, NotableInvestor


async def get_shark_deals(
    db: AsyncSession,
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    investor: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Fetch bulk + block deals with optional filters.

    Returns dicts with deal info + instrument name/exchange for the API response.
    """
    # Query bulk deals
    query = (
        select(BulkDeal, Instrument.name, Instrument.symbol, Instrument.exchange)
        .join(Instrument, BulkDeal.instrument_id == Instrument.id)
        .order_by(BulkDeal.ts.desc(), BulkDeal.created_at.desc())
    )

    if from_date:
        query = query.where(BulkDeal.ts >= from_date)
    if to_date:
        query = query.where(BulkDeal.ts <= to_date)
    if investor:
        query = query.where(BulkDeal.party_name.ilike(f"%{investor}%"))
    if cursor:
        query = query.where(BulkDeal.created_at < cursor)

    query = query.limit(limit)
    result = await db.execute(query)

    deals = []
    for row in result.all():
        deal = row[0]
        inst_name = row[1]
        inst_symbol = row[2]
        inst_exchange = row[3]

        # Check if this investor is a notable investor
        notable = await _check_notable_investor(db, deal.party_name)

        deals.append({
            "id": str(deal.id),
            "instrument_name": inst_name,
            "symbol": inst_symbol,
            "exchange": inst_exchange.value,
            "party_name": deal.party_name,
            "side": deal.side.value,
            "qty": deal.qty,
            "avg_price": deal.avg_price,
            "pct_equity": deal.pct_equity,
            "ts": deal.ts.isoformat(),
            "deal_type": "bulk",
            "is_notable": notable is not None,
            "notable_tags": notable.tags if notable else None,
        })

    return deals


async def _check_notable_investor(db: AsyncSession, party_name: str) -> NotableInvestor | None:
    """Check if a party name matches a notable investor (exact or alias)."""
    normalized = party_name.strip().upper()
    result = await db.execute(
        select(NotableInvestor).where(
            func.upper(NotableInvestor.normalized_name) == normalized
        )
    )
    return result.scalar_one_or_none()
