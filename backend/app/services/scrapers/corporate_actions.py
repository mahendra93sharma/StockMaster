"""Corporate actions scraper — fetches upcoming corporate events from BSE.

Covers: dividends, splits, bonuses, mergers/demergers, rights issues.
"""

import hashlib
import logging
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CorporateAction, CorporateActionType, Exchange, Instrument, RawPayload

logger = logging.getLogger(__name__)

BSE_CORPORATE_ACTIONS_URL = "https://api.bseindia.com/BseIndiaAPI/api/DefaultData/w"
BSE_CA_PARAMS = {
    "Atea": "C",  # Corporate actions
    "Atea1": "",
    "Atea2": "",
}

USER_AGENT = "StockMaster/1.0 (+https://stockmaster.app; contact@stockmaster.app)"
REQUEST_TIMEOUT = 30.0


def _map_action_type(purpose: str) -> CorporateActionType | None:
    """Map BSE purpose text to our CorporateActionType enum."""
    p = purpose.lower()
    if "dividend" in p:
        return CorporateActionType.dividend
    elif "split" in p or "sub-division" in p:
        return CorporateActionType.split
    elif "bonus" in p:
        return CorporateActionType.bonus
    elif "demerger" in p:
        return CorporateActionType.demerger
    elif "merger" in p or "amalgamation" in p:
        return CorporateActionType.merger
    return None


def parse_corporate_actions(data: list[dict]) -> list[dict]:
    """Parse BSE corporate actions response.

    Expected fields:
    - scrip_code: "500325"
    - long_name: "Reliance Industries"
    - purpose: "Dividend - Rs 8 Per Share"
    - ex_dt: "15/05/2026"
    - bcrd_from: "10/05/2026"
    """
    actions: list[dict] = []

    for record in data:
        try:
            scrip_code = str(record.get("scrip_code", "")).strip()
            company = record.get("long_name", "").strip()
            purpose = record.get("purpose", "").strip()
            ex_date_str = record.get("ex_dt", "").strip()

            if not scrip_code or not purpose:
                continue

            action_type = _map_action_type(purpose)
            if action_type is None:
                continue  # Skip unknown types

            # Parse ex-date
            effective_date = None
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    effective_date = datetime.strptime(ex_date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if effective_date is None:
                effective_date = date.today()

            actions.append({
                "symbol": scrip_code,
                "company": company,
                "type": action_type,
                "details": {"purpose": purpose, "ex_date": ex_date_str},
                "effective_date": effective_date,
            })
        except (ValueError, KeyError) as e:
            logger.debug("Skipping corporate action record: %s", e)
            continue

    return actions


async def scrape_corporate_actions(db: AsyncSession) -> int:
    """Fetch BSE corporate actions. Returns count of items ingested."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                BSE_CORPORATE_ACTIONS_URL,
                params=BSE_CA_PARAMS,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("BSE corporate actions API failed: %s", e)
            return 0

    raw_text = response.text

    # Persist raw payload
    payload_hash = hashlib.sha256(raw_text.encode()).hexdigest()
    raw_payload = RawPayload(
        source="bse_corporate_actions",
        fetched_at=datetime.now(UTC),
        url=BSE_CORPORATE_ACTIONS_URL,
        sha256=payload_hash,
        payload=raw_text[:50000],
    )
    db.add(raw_payload)
    await db.flush()

    # Parse
    try:
        data = response.json()
        if isinstance(data, dict):
            data = data.get("Table", data.get("data", []))
    except Exception as e:
        logger.error("Failed to parse BSE corporate actions JSON: %s", e)
        return 0

    actions = parse_corporate_actions(data)
    logger.info("Parsed %d corporate actions from BSE", len(actions))

    # Persist (skip duplicates by instrument + type + effective_date)
    ingested = 0
    for item in actions:
        # Look up instrument
        inst_result = await db.execute(
            select(Instrument).where(
                Instrument.symbol == item["symbol"],
                Instrument.exchange == Exchange.BSE,
            )
        )
        instrument = inst_result.scalar_one_or_none()
        if instrument is None:
            continue  # Only track actions for known instruments

        # Check for duplicate
        existing = await db.execute(
            select(CorporateAction.id).where(
                CorporateAction.instrument_id == instrument.id,
                CorporateAction.type == item["type"],
                CorporateAction.effective_date == item["effective_date"],
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            continue

        ca = CorporateAction(
            instrument_id=instrument.id,
            type=item["type"],
            details=item["details"],
            effective_date=item["effective_date"],
        )
        db.add(ca)
        ingested += 1

    await db.flush()
    return ingested
