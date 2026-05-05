"""News scraper — fetches latest market news from BSE announcements.

Sources:
- BSE corporate filings API (primary)
- Can be extended to include other sources
"""

import hashlib
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Exchange, Instrument, News, RawPayload

logger = logging.getLogger(__name__)

BSE_ANNOUNCEMENTS_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
BSE_ANNOUNCEMENTS_PARAMS = {
    "strCat": "-1",
    "strPrevDate": "",
    "strScrip": "",
    "strSearch": "P",
    "strToDate": "",
    "strType": "C",
}

USER_AGENT = "StockMaster/1.0 (+https://stockmaster.app; contact@stockmaster.app)"
REQUEST_TIMEOUT = 30.0


def parse_bse_announcements(data: list[dict]) -> list[dict]:
    """Parse BSE announcement records.

    Expected fields:
    - DT_TM: "2026-05-05T14:30:00"
    - SCRIP_CD: "500325"
    - SLONGNAME: "Reliance Industries Ltd"
    - NEWSSUB: "Quarterly results..."
    - ATTACHMENTNAME: "file.pdf"
    - NEWS_DT: "05 May 2026"
    - CATEGORYNAME: "Result"
    """
    news_items: list[dict] = []

    for record in data:
        try:
            scrip_code = str(record.get("SCRIP_CD", "")).strip()
            title = record.get("NEWSSUB", "").strip()
            company_name = record.get("SLONGNAME", "").strip()
            dt_str = record.get("DT_TM", "")
            attachment = record.get("ATTACHMENTNAME", "")
            category = record.get("CATEGORYNAME", "")

            if not title or not scrip_code:
                continue

            # Parse timestamp
            ts = None
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%d %b %Y", "%d-%m-%Y"):
                try:
                    ts = datetime.strptime(dt_str, fmt).replace(tzinfo=UTC)
                    break
                except ValueError:
                    continue
            if ts is None:
                ts = datetime.now(UTC)

            url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}" if attachment else f"https://www.bseindia.com/stock-share-price/{scrip_code}"

            news_items.append({
                "symbol": scrip_code,
                "company_name": company_name,
                "title": title,
                "source": f"BSE/{category}" if category else "BSE",
                "url": url,
                "summary": f"[{category}] {title}" if category else title,
                "ts": ts,
            })
        except (ValueError, KeyError) as e:
            logger.debug("Skipping BSE announcement: %s", e)
            continue

    return news_items


async def scrape_bse_news(db: AsyncSession) -> int:
    """Fetch BSE corporate announcements. Returns count of items ingested."""
    today = datetime.now(UTC).strftime("%Y%m%d")
    params = {**BSE_ANNOUNCEMENTS_PARAMS, "strPrevDate": today, "strToDate": today}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                BSE_ANNOUNCEMENTS_URL,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("BSE announcements API failed: %s", e)
            return 0

    raw_text = response.text

    # Persist raw payload
    payload_hash = hashlib.sha256(raw_text.encode()).hexdigest()
    raw_payload = RawPayload(
        source="bse_news",
        fetched_at=datetime.now(UTC),
        url=BSE_ANNOUNCEMENTS_URL,
        sha256=payload_hash,
        payload=raw_text[:50000],  # Cap storage for large responses
    )
    db.add(raw_payload)
    await db.flush()

    # Parse
    try:
        data = response.json()
        if isinstance(data, dict):
            data = data.get("Table", [])
    except Exception as e:
        logger.error("Failed to parse BSE announcements JSON: %s", e)
        return 0

    news_items = parse_bse_announcements(data)
    logger.info("Parsed %d news items from BSE", len(news_items))

    # Persist (skip duplicates by URL)
    ingested = 0
    for item in news_items:
        # Check for existing
        existing = await db.execute(
            select(News.id).where(News.url == item["url"]).limit(1)
        )
        if existing.scalar_one_or_none():
            continue

        # Look up instrument
        inst_result = await db.execute(
            select(Instrument).where(
                Instrument.symbol == item["symbol"],
                Instrument.exchange == Exchange.BSE,
            )
        )
        instrument = inst_result.scalar_one_or_none()

        news = News(
            instrument_id=instrument.id if instrument else None,
            title=item["title"][:1000],
            source=item["source"][:200],
            url=item["url"][:2048],
            summary=item["summary"][:5000] if item["summary"] else None,
            ts=item["ts"],
        )
        db.add(news)
        ingested += 1

    await db.flush()
    return ingested
