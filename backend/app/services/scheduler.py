"""Scheduler service — APScheduler integration."""

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.models import SchedulerRun, SchedulerRunStatus
from app.db.session import async_session_factory
from app.services.closed_trades import check_and_close_positions
from app.services.recommendation_engine import run_recommendation_pipeline
from app.services.scrapers import scrape_bse_bulk_deals
from app.services.scrapers.corporate_actions import scrape_corporate_actions
from app.services.scrapers.news import scrape_bse_news
from app.services.scrapers.nse_block_deals import scrape_nse_block_deals

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_job(job_name: str, job_func, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """Wrapper that records scheduler runs."""
    started_at = datetime.now(UTC)
    async with async_session_factory() as db:
        run = SchedulerRun(
            job_name=job_name,
            started_at=started_at,
            status=SchedulerRunStatus.running,
        )
        db.add(run)
        await db.commit()

        try:
            items = await job_func(db)
            run.status = SchedulerRunStatus.success
            run.items_ingested = items
            await db.commit()
            logger.info("Job %s succeeded: %d items", job_name, items)
        except Exception as exc:
            run.status = SchedulerRunStatus.failed
            run.error = str(exc)[:2000]
            await db.commit()
            logger.exception("Job %s failed", job_name)
        finally:
            run.finished_at = datetime.now(UTC)
            await db.commit()


async def job_bse_bulk_deals() -> None:
    """Scheduled job: BSE bulk deals scraper."""
    await run_job("bse_bulk_deals", scrape_bse_bulk_deals)


async def job_nse_block_deals() -> None:
    """Scheduled job: NSE block deals scraper."""
    await run_job("nse_block_deals", scrape_nse_block_deals)


async def job_bse_news() -> None:
    """Scheduled job: BSE news/announcements scraper."""
    await run_job("bse_news", scrape_bse_news)


async def job_corporate_actions() -> None:
    """Scheduled job: Corporate actions scraper."""
    await run_job("corporate_actions", scrape_corporate_actions)


async def job_recommendations() -> None:
    """Scheduled job: LLM recommendation pipeline."""
    await run_job("recommendations", run_recommendation_pipeline)


async def job_position_monitor() -> None:
    """Scheduled job: Check positions against target/stoploss."""
    await run_job("position_monitor", check_and_close_positions)


def start_scheduler() -> None:
    """Configure and start the APScheduler instance."""
    # Market hours (Mon-Fri, 09:00-15:30 IST): every 30 minutes
    scheduler.add_job(
        job_bse_bulk_deals,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="0,30",
        timezone="Asia/Kolkata",
        id="bse_bulk_deals",
        replace_existing=True,
    )

    # End of day snapshot (16:00 IST)
    scheduler.add_job(
        job_bse_bulk_deals,
        "cron",
        day_of_week="mon-fri",
        hour=16,
        minute=0,
        timezone="Asia/Kolkata",
        id="bse_bulk_deals_eod",
        replace_existing=True,
    )

    # NSE block deals: every 30 min during market hours
    scheduler.add_job(
        job_nse_block_deals,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="15,45",
        timezone="Asia/Kolkata",
        id="nse_block_deals",
        replace_existing=True,
    )

    # BSE news: every 15 minutes during market + 1 hour after
    scheduler.add_job(
        job_bse_news,
        "cron",
        day_of_week="mon-fri",
        hour="9-16",
        minute="0,15,30,45",
        timezone="Asia/Kolkata",
        id="bse_news",
        replace_existing=True,
    )

    # Corporate actions: once daily at 08:00 IST
    scheduler.add_job(
        job_corporate_actions,
        "cron",
        day_of_week="mon-fri",
        hour=8,
        minute=0,
        timezone="Asia/Kolkata",
        id="corporate_actions",
        replace_existing=True,
    )

    # Recommendation pipeline: twice daily (09:30 and 16:30 IST)
    scheduler.add_job(
        job_recommendations,
        "cron",
        day_of_week="mon-fri",
        hour="9,16",
        minute=30,
        timezone="Asia/Kolkata",
        id="recommendations",
        replace_existing=True,
    )

    # Position monitor: every 15 min during market hours
    scheduler.add_job(
        job_position_monitor,
        "cron",
        day_of_week="mon-fri",
        hour="9-15",
        minute="5,20,35,50",
        timezone="Asia/Kolkata",
        id="position_monitor",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
