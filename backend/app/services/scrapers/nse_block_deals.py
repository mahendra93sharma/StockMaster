"""NSE block deals scraper.

Fetches block deal data from NSE's public API endpoint.
"""

import contextlib
import hashlib
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BlockDeal, DealSide, Exchange, Instrument, RawPayload

logger = logging.getLogger(__name__)

NSE_BLOCK_DEALS_URL = "https://www.nseindia.com/api/block-deal"
NSE_BASE_URL = "https://www.nseindia.com"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30.0


async def _get_nse_session(client: httpx.AsyncClient) -> None:
    """Hit NSE homepage first to establish cookies (required by NSE's API)."""
    with contextlib.suppress(httpx.HTTPError):
        await client.get(
            NSE_BASE_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )


def parse_nse_block_deals(data: list[dict]) -> list[dict]:
    """Parse NSE block deals JSON response.

    Expected fields per record:
    - BD_DT_DATE: "05-May-2026"
    - BD_SYMBOL: "RELIANCE"
    - BD_SCRIP_NAME: "Reliance Industries Limited"
    - BD_CLIENT_NAME: "MORGAN STANLEY ..."
    - BD_BUY_SELL: "Buy" / "Sell"
    - BD_QTY_TRD: "500000"
    - BD_TP_WATP: "2450.50"
    """
    deals: list[dict] = []

    for record in data:
        try:
            symbol = record.get("BD_SYMBOL", "").strip()
            name = record.get("BD_SCRIP_NAME", "").strip()
            party = record.get("BD_CLIENT_NAME", "").strip()
            buy_sell = record.get("BD_BUY_SELL", "").strip().upper()
            qty_str = str(record.get("BD_QTY_TRD", "0")).replace(",", "")
            price_str = str(record.get("BD_TP_WATP", "0")).replace(",", "")
            date_str = record.get("BD_DT_DATE", "")

            qty = int(float(qty_str))
            price = float(price_str)

            # Parse date
            deal_date = None
            for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    deal_date = datetime.strptime(date_str, fmt).replace(tzinfo=UTC)
                    break
                except ValueError:
                    continue
            if deal_date is None:
                deal_date = datetime.now(UTC)

            side = DealSide.BUY if buy_sell in ("BUY", "B") else DealSide.SELL

            deals.append({
                "symbol": symbol,
                "name": name or symbol,
                "party_name": party,
                "side": side,
                "qty": qty,
                "avg_price": price,
                "ts": deal_date,
            })
        except (ValueError, KeyError) as e:
            logger.debug("Skipping NSE block deal record: %s", e)
            continue

    return deals


async def _get_or_create_nse_instrument(
    db: AsyncSession, symbol: str, name: str
) -> Instrument:
    """Find or create an NSE instrument."""
    result = await db.execute(
        select(Instrument).where(
            Instrument.symbol == symbol,
            Instrument.exchange == Exchange.NSE,
        )
    )
    instrument = result.scalar_one_or_none()
    if instrument is None:
        instrument = Instrument(
            symbol=symbol,
            exchange=Exchange.NSE,
            name=name,
        )
        db.add(instrument)
        await db.flush()
    return instrument


async def scrape_nse_block_deals(db: AsyncSession) -> int:
    """Main NSE block deals scraper. Returns number of deals ingested."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Establish session cookies
        await _get_nse_session(client)

        try:
            response = await client.get(
                NSE_BLOCK_DEALS_URL,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Referer": "https://www.nseindia.com/market-data/block-deals",
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("NSE block deals API failed: %s", e)
            return 0

    raw_text = response.text

    # Persist raw payload
    payload_hash = hashlib.sha256(raw_text.encode()).hexdigest()
    raw_payload = RawPayload(
        source="nse_block_deals",
        fetched_at=datetime.now(UTC),
        url=NSE_BLOCK_DEALS_URL,
        sha256=payload_hash,
        payload=raw_text,
    )
    db.add(raw_payload)
    await db.flush()

    # Parse JSON
    try:
        data = response.json()
        if isinstance(data, dict):
            data = data.get("data", [])
    except Exception as e:
        logger.error("Failed to parse NSE response JSON: %s", e)
        return 0

    deals = parse_nse_block_deals(data)
    logger.info("Parsed %d block deals from NSE", len(deals))

    # Persist
    ingested = 0
    for deal_data in deals:
        instrument = await _get_or_create_nse_instrument(
            db, symbol=deal_data["symbol"], name=deal_data["name"]
        )
        deal = BlockDeal(
            instrument_id=instrument.id,
            party_name=deal_data["party_name"],
            side=deal_data["side"],
            qty=deal_data["qty"],
            avg_price=deal_data["avg_price"],
            ts=deal_data["ts"],
        )
        db.add(deal)
        ingested += 1

    await db.flush()
    return ingested
