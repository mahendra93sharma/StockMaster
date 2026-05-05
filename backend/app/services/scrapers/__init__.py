"""BSE bulk deals scraper.

Fetches bulk deal data from BSE's official CSV download endpoint.
Falls back to HTML scraping if CSV feed is unavailable.
"""

import hashlib
import logging
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BulkDeal, DealSide, Exchange, Instrument, RawPayload

logger = logging.getLogger(__name__)

BSE_BULK_DEALS_URL = "https://www.bseindia.com/markets/equity/EQReports/BulkDeals.aspx"
BSE_BULK_DEALS_CSV_URL = "https://www.bseindia.com/download/BhsV/BulkDeals_BSE.csv"

USER_AGENT = "StockMaster/1.0 (+https://stockmaster.app; contact@stockmaster.app)"
REQUEST_TIMEOUT = 30.0


async def fetch_bse_bulk_deals_csv(client: httpx.AsyncClient) -> str | None:
    """Try to fetch bulk deals from BSE's official CSV endpoint."""
    try:
        response = await client.get(
            BSE_BULK_DEALS_CSV_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200 and "text" in response.headers.get("content-type", ""):
            return response.text
    except httpx.HTTPError as e:
        logger.warning("BSE CSV endpoint failed: %s", e)
    return None


async def fetch_bse_bulk_deals_html(client: httpx.AsyncClient) -> str | None:
    """Fallback: fetch bulk deals from BSE HTML page."""
    try:
        response = await client.get(
            BSE_BULK_DEALS_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            return response.text
    except httpx.HTTPError as e:
        logger.warning("BSE HTML endpoint failed: %s", e)
    return None


def parse_csv_deals(csv_text: str) -> list[dict]:
    """Parse BSE bulk deals CSV format.

    Expected columns: Deal Date, Security Code, Security Name, Client Name,
    Deal Type (B/S), Quantity, Price, Remarks
    """
    deals: list[dict] = []
    lines = csv_text.strip().split("\n")

    if len(lines) < 2:
        return deals

    # Skip header
    for line in lines[1:]:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 7:
            continue

        try:
            deal_date_str = parts[0]
            security_code = parts[1]
            security_name = parts[2]
            client_name = parts[3]
            deal_type = parts[4].upper()
            quantity = int(float(parts[5]))
            price = float(parts[6])

            # Parse deal date
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    deal_date = datetime.strptime(deal_date_str, fmt).replace(tzinfo=UTC)
                    break
                except ValueError:
                    continue
            else:
                deal_date = datetime.now(UTC)

            deals.append({
                "symbol": security_code,
                "name": security_name,
                "party_name": client_name,
                "side": DealSide.BUY if deal_type in ("B", "BUY") else DealSide.SELL,
                "qty": quantity,
                "avg_price": price,
                "ts": deal_date,
            })
        except (ValueError, IndexError) as e:
            logger.debug("Skipping CSV row: %s — %s", line[:80], e)
            continue

    return deals


def parse_html_deals(html_text: str) -> list[dict]:
    """Parse bulk deals from BSE HTML table (fallback)."""
    deals: list[dict] = []
    soup = BeautifulSoup(html_text, "lxml")

    table = soup.find("table", {"id": "ContentPlaceHolder1_gvbulk"})
    if table is None:
        # Try any table with deal-like headers
        tables = soup.find_all("table")
        for t in tables:
            headers = [th.get_text(strip=True).lower() for th in t.find_all("th")]
            if "client name" in headers or "party name" in headers:
                table = t
                break

    if table is None:
        logger.warning("Could not find bulk deals table in BSE HTML response")
        return deals

    rows = table.find_all("tr")[1:]  # Skip header
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) < 7:
            continue

        try:
            deal_date_str = cells[0]
            security_code = cells[1]
            security_name = cells[2]
            client_name = cells[3]
            deal_type = cells[4].upper()
            quantity = int(cells[5].replace(",", ""))
            price = float(cells[6].replace(",", ""))

            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    deal_date = datetime.strptime(deal_date_str, fmt).replace(tzinfo=UTC)
                    break
                except ValueError:
                    continue
            else:
                deal_date = datetime.now(UTC)

            deals.append({
                "symbol": security_code,
                "name": security_name,
                "party_name": client_name,
                "side": DealSide.BUY if deal_type in ("B", "BUY") else DealSide.SELL,
                "qty": quantity,
                "avg_price": price,
                "ts": deal_date,
            })
        except (ValueError, IndexError) as e:
            logger.debug("Skipping HTML row: %s", e)
            continue

    return deals


async def get_or_create_instrument(
    db: AsyncSession, symbol: str, name: str
) -> Instrument:
    """Find or create an instrument for BSE."""
    result = await db.execute(
        select(Instrument).where(
            Instrument.symbol == symbol,
            Instrument.exchange == Exchange.BSE,
        )
    )
    instrument = result.scalar_one_or_none()
    if instrument is None:
        instrument = Instrument(
            symbol=symbol,
            exchange=Exchange.BSE,
            name=name,
        )
        db.add(instrument)
        await db.flush()
    return instrument


async def scrape_bse_bulk_deals(db: AsyncSession) -> int:
    """Main scraper entry point. Returns number of deals ingested."""
    async with httpx.AsyncClient() as client:
        # Try CSV first (preferred)
        raw_data = await fetch_bse_bulk_deals_csv(client)
        source_url = BSE_BULK_DEALS_CSV_URL
        parser = parse_csv_deals

        if raw_data is None:
            # Fallback to HTML
            logger.info("CSV unavailable, falling back to HTML scraping")
            raw_data = await fetch_bse_bulk_deals_html(client)
            source_url = BSE_BULK_DEALS_URL
            parser = parse_html_deals

        if raw_data is None:
            logger.error("Both BSE bulk deal endpoints failed")
            return 0

    # Persist raw payload for audit
    payload_hash = hashlib.sha256(raw_data.encode()).hexdigest()
    raw_payload = RawPayload(
        source="bse_bulk_deals",
        fetched_at=datetime.now(UTC),
        url=source_url,
        sha256=payload_hash,
        payload=raw_data,
    )
    db.add(raw_payload)
    await db.flush()

    # Parse
    deals = parser(raw_data)
    logger.info("Parsed %d bulk deals from BSE", len(deals))

    # Persist deals
    ingested = 0
    for deal_data in deals:
        instrument = await get_or_create_instrument(
            db, symbol=deal_data["symbol"], name=deal_data["name"]
        )
        deal = BulkDeal(
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
