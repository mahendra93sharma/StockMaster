"""Admin router — scheduler status, manual triggers, recommendations management."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.db.models import SchedulerRun, User
from app.db.session import get_db
from app.services.scheduler import (
    job_bse_bulk_deals,
    job_bse_news,
    job_corporate_actions,
    job_nse_block_deals,
    job_position_monitor,
    job_recommendations,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/scheduler/runs")
async def list_scheduler_runs(
    job: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List scheduler run history."""
    query = select(SchedulerRun).order_by(SchedulerRun.started_at.desc())

    if job:
        query = query.where(SchedulerRun.job_name == job)
    if cursor:
        query = query.where(SchedulerRun.started_at < cursor)

    query = query.limit(limit)
    result = await db.execute(query)
    runs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(r.id),
                "job_name": r.job_name,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "status": r.status.value,
                "error": r.error,
                "items_ingested": r.items_ingested,
            }
            for r in runs
        ],
        "cursor": runs[-1].started_at.isoformat() if runs else None,
    }


@router.post("/scheduler/{job_name}/trigger", status_code=202)
async def trigger_job(
    job_name: str,
    user: User = Depends(require_admin),
) -> dict:
    """Manually trigger a scheduler job."""
    job_map = {
        "bse_bulk_deals": job_bse_bulk_deals,
        "nse_block_deals": job_nse_block_deals,
        "bse_news": job_bse_news,
        "corporate_actions": job_corporate_actions,
        "recommendations": job_recommendations,
        "position_monitor": job_position_monitor,
    }

    if job_name not in job_map:
        from app.core.exceptions import NotFoundError
        raise NotFoundError(f"Job '{job_name}'")

    # Run async in background (fire and forget for the response)
    import asyncio
    asyncio.create_task(job_map[job_name]())

    logger.info("Admin %s triggered job: %s", user.email, job_name)
    return {"status": "triggered", "job": job_name}
