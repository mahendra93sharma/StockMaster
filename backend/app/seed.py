"""Seed script — populates the database with demo data for development.

Run: python -m app.seed
Requires: DATABASE_URL env var or .env file pointing to a running Postgres.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.models import (
    BulkDeal,
    DealSide,
    Exchange,
    Horizon,
    Instrument,
    NotableInvestor,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    User,
    UserRole,
)
from app.db.session import async_session_factory

SEED_INSTRUMENTS = [
    {"symbol": "500325", "name": "Reliance Industries Ltd", "exchange": Exchange.BSE, "sector": "Energy", "isin": "INE002A01018"},
    {"symbol": "532540", "name": "Tata Consultancy Services Ltd", "exchange": Exchange.BSE, "sector": "IT", "isin": "INE467B01029"},
    {"symbol": "500180", "name": "HDFC Bank Ltd", "exchange": Exchange.BSE, "sector": "Banking", "isin": "INE040A01034"},
    {"symbol": "532174", "name": "ICICI Bank Ltd", "exchange": Exchange.BSE, "sector": "Banking", "isin": "INE090A01021"},
    {"symbol": "500209", "name": "Infosys Ltd", "exchange": Exchange.BSE, "sector": "IT", "isin": "INE009A01021"},
    {"symbol": "532454", "name": "Bharti Airtel Ltd", "exchange": Exchange.BSE, "sector": "Telecom", "isin": "INE397D01024"},
    {"symbol": "500112", "name": "State Bank of India", "exchange": Exchange.BSE, "sector": "Banking", "isin": "INE062A01020"},
    {"symbol": "500696", "name": "Hindustan Unilever Ltd", "exchange": Exchange.BSE, "sector": "FMCG", "isin": "INE030A01027"},
    {"symbol": "532555", "name": "NTPC Ltd", "exchange": Exchange.BSE, "sector": "Power", "isin": "INE733E01010"},
    {"symbol": "500010", "name": "HDFC Life Insurance", "exchange": Exchange.BSE, "sector": "Insurance", "isin": "INE795G01014"},
]

SEED_NOTABLE_INVESTORS = [
    {"normalized_name": "RAKESH JHUNJHUNWALA", "aliases": ["RARE ENTERPRISES", "RARE ENTERPRISES LTD"], "tags": ["HNI"]},
    {"normalized_name": "DOLLY KHANNA", "aliases": ["DOLLY KHANNA"], "tags": ["HNI"]},
    {"normalized_name": "MUTUAL FUND-SBI", "aliases": ["SBI MUTUAL FUND", "SBI MF"], "tags": ["FII"]},
    {"normalized_name": "LIC OF INDIA", "aliases": ["LIFE INSURANCE CORPORATION", "LIC"], "tags": ["FII"]},
]


async def seed_data() -> None:
    async with async_session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(Instrument).limit(1))
        if result.scalar_one_or_none():
            print("Database already has data. Skipping seed.")
            return

        # Admin user
        admin = User(
            email="admin@stockmaster.app",
            display_name="StockMaster Admin",
            role=UserRole.admin,
        )
        db.add(admin)

        # Test users
        test_user_1 = User(
            email="testuser1@stockmaster.app",
            display_name="Test User One",
            role=UserRole.user,
        )
        db.add(test_user_1)

        test_user_2 = User(
            email="testuser2@stockmaster.app",
            display_name="Test User Two",
            role=UserRole.user,
        )
        db.add(test_user_2)

        # Instruments
        instruments: list[Instrument] = []
        for data in SEED_INSTRUMENTS:
            inst = Instrument(**data)
            db.add(inst)
            instruments.append(inst)
        await db.flush()

        # Notable investors
        for inv_data in SEED_NOTABLE_INVESTORS:
            inv = NotableInvestor(**inv_data)
            db.add(inv)
        await db.flush()

        # Bulk deals (synthetic)
        now = datetime.now(UTC)
        deal_parties = ["RARE ENTERPRISES", "DOLLY KHANNA", "MORGAN STANLEY", "GOLDMAN SACHS INDIA", "CITADEL ADVISORS"]
        for i, inst in enumerate(instruments[:5]):
            for j in range(3):
                deal = BulkDeal(
                    instrument_id=inst.id,
                    party_name=deal_parties[(i + j) % len(deal_parties)],
                    side=DealSide.BUY if (i + j) % 2 == 0 else DealSide.SELL,
                    qty=10000 * (j + 1),
                    avg_price=100.0 + i * 50 + j * 10,
                    pct_equity=0.1 * (j + 1),
                    ts=now - timedelta(days=j),
                )
                db.add(deal)

        # Recommendations (one per instrument per horizon)
        horizons = [Horizon.short, Horizon.mid, Horizon.long]
        actions = [RecommendationAction.BUY, RecommendationAction.SELL, RecommendationAction.HOLD]
        base_prices = [2450, 3800, 1650, 1100, 1500, 1350, 780, 2500, 350, 650]

        for i, inst in enumerate(instruments):
            for h_idx, horizon in enumerate(horizons):
                base = base_prices[i]
                action = actions[(i + h_idx) % 3]
                entry = base * 1.0
                target = base * 1.12 if action == RecommendationAction.BUY else base * 0.88
                stoploss = base * 0.95 if action == RecommendationAction.BUY else base * 1.05

                rec = Recommendation(
                    instrument_id=inst.id,
                    horizon=horizon,
                    action=action,
                    entry=round(entry, 2),
                    target=round(target, 2),
                    stoploss=round(stoploss, 2),
                    confidence=0.65 + (i % 4) * 0.08,
                    rationale=f"Based on technical analysis and recent {horizon.value}-term momentum indicators for {inst.name}. Volume patterns suggest institutional accumulation.",
                    risk_factors=["Market volatility", "Sector rotation risk", "Global macro uncertainty"],
                    llm_meta={"model": "claude-sonnet-4-20250514", "tokens_used": 1500, "cost_usd": 0.02},
                    status=RecommendationStatus.active,
                )
                db.add(rec)

        await db.commit()
        print(f"Seeded: 1 admin + 2 test users, {len(instruments)} instruments, {len(instruments) * 3} recommendations, 15 bulk deals")


if __name__ == "__main__":
    asyncio.run(seed_data())
