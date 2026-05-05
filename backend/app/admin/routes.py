"""HTMX-powered admin dashboard routes.

Serves server-rendered HTML pages with HTMX for interactivity.
Authentication is via a simple admin token cookie (for now).
"""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import (
    ClosedTrade,
    Instrument,
    Recommendation,
    RecommendationStatus,
    SchedulerRun,
)
from app.db.session import get_db
from app.services.closed_trades import close_recommendation, get_closed_trades
from app.services.scheduler import (
    job_bse_bulk_deals,
    job_bse_news,
    job_corporate_actions,
    job_nse_block_deals,
    job_position_monitor,
    job_recommendations,
    scheduler,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/admin")

# Simple admin password check (cookie-based for dashboard)
ADMIN_COOKIE_NAME = "sm_admin_token"


def _check_admin(request: Request) -> bool:
    """Verify admin cookie. Simple token-based auth for the web dashboard."""
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    # In production, use a proper session. For now, accept JWT secret as admin token.
    return token == settings.jwt_secret_key


# ─── Dashboard ───────────────────────────────────────────────────────────────


@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_root(request: Request):
    if _check_admin(request):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if password == settings.jwt_secret_key:
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie(ADMIN_COOKIE_NAME, password, httponly=True, samesite="strict")
        return response
    return templates.TemplateResponse(request, "login.html", {"error": "Invalid password"})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    if not _check_admin(request):
        return RedirectResponse(url="/admin/login")

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0)

    # Stats
    active_recs = await db.execute(
        select(func.count()).where(Recommendation.status == RecommendationStatus.active)
    )
    closed_count = await db.execute(select(func.count()).select_from(ClosedTrade))
    avg_pnl_result = await db.execute(select(func.avg(ClosedTrade.pnl_pct)))
    instrument_count = await db.execute(select(func.count()).select_from(Instrument))
    runs_today = await db.execute(
        select(func.count()).where(SchedulerRun.started_at >= today_start)
    )
    wins = await db.execute(
        select(func.count()).where(ClosedTrade.pnl_pct > 0)
    )
    total_closed = closed_count.scalar() or 0
    total_wins = wins.scalar() or 0

    stats = {
        "active_recommendations": active_recs.scalar() or 0,
        "closed_trades": total_closed,
        "avg_pnl": avg_pnl_result.scalar() or 0.0,
        "instruments": instrument_count.scalar() or 0,
        "scheduler_runs_today": runs_today.scalar() or 0,
        "win_rate": (total_wins / total_closed * 100) if total_closed > 0 else 0,
    }

    # Recent runs
    recent = await db.execute(
        select(SchedulerRun).order_by(SchedulerRun.started_at.desc()).limit(10)
    )
    recent_runs = []
    for run in recent.scalars().all():
        duration = ""
        if run.finished_at and run.started_at:
            delta = run.finished_at - run.started_at
            duration = f"{delta.total_seconds():.1f}s"
        recent_runs.append({
            "job_name": run.job_name,
            "started_at": run.started_at.strftime("%Y-%m-%d %H:%M") if run.started_at else "",
            "status": run.status.value,
            "items_ingested": run.items_ingested,
            "duration": duration,
        })

    jobs = ["bse_bulk_deals", "nse_block_deals", "bse_news", "corporate_actions", "recommendations", "position_monitor"]

    return templates.TemplateResponse(request, "dashboard.html", {
        "active_page": "dashboard",
        "stats": stats,
        "recent_runs": recent_runs,
        "jobs": jobs,
    })


@router.post("/dashboard/trigger/{job_name}")
async def trigger_job_dashboard(job_name: str, request: Request):
    if not _check_admin(request):
        return Response(status_code=401)

    job_map = {
        "bse_bulk_deals": job_bse_bulk_deals,
        "nse_block_deals": job_nse_block_deals,
        "bse_news": job_bse_news,
        "corporate_actions": job_corporate_actions,
        "recommendations": job_recommendations,
        "position_monitor": job_position_monitor,
    }

    if job_name in job_map:
        asyncio.create_task(job_map[job_name]())
        return Response(status_code=204, headers={"HX-Trigger": "job-triggered"})
    return Response(status_code=404)


# ─── Recommendations ─────────────────────────────────────────────────────────


@router.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(request: Request, db: AsyncSession = Depends(get_db)):
    if not _check_admin(request):
        return RedirectResponse(url="/admin/login")

    result = await db.execute(
        select(Recommendation, Instrument.name, Instrument.exchange)
        .join(Instrument, Recommendation.instrument_id == Instrument.id)
        .where(Recommendation.status == RecommendationStatus.active)
        .order_by(Recommendation.created_at.desc())
        .limit(100)
    )

    recommendations = []
    for row in result.all():
        rec = row[0]
        recommendations.append({
            "id": str(rec.id),
            "instrument_name": row[1],
            "exchange": row[2].value,
            "horizon": rec.horizon.value,
            "action": rec.action.value,
            "entry": rec.entry,
            "target": rec.target,
            "stoploss": rec.stoploss,
            "confidence": rec.confidence,
            "created_at": rec.created_at.strftime("%Y-%m-%d %H:%M") if rec.created_at else "",
        })

    return templates.TemplateResponse(request, "recommendations.html", {
        "active_page": "recommendations",
        "recommendations": recommendations,
    })


@router.post("/recommendations/{rec_id}/close", response_class=HTMLResponse)
async def close_recommendation_admin(rec_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    if not _check_admin(request):
        return Response(status_code=401)

    from uuid import UUID
    result = await db.execute(
        select(Recommendation).where(Recommendation.id == UUID(rec_id))
    )
    rec = result.scalar_one_or_none()
    if not rec:
        return Response(status_code=404)

    await close_recommendation(db, rec, rec.entry, "Manually closed by admin")
    await db.commit()

    # Return empty row (HTMX will replace the row)
    return HTMLResponse(
        f'<tr id="rec-{rec_id}" style="opacity:0.5;"><td colspan="9">Closed manually</td></tr>'
    )


# ─── Closed Trades ───────────────────────────────────────────────────────────


@router.get("/closed-trades", response_class=HTMLResponse)
async def closed_trades_page(request: Request, db: AsyncSession = Depends(get_db)):
    if not _check_admin(request):
        return RedirectResponse(url="/admin/login")

    trades_data = await get_closed_trades(db, limit=100)

    # Summary
    total = len(trades_data)
    wins = sum(1 for t in trades_data if t["pnl_pct"] > 0)
    losses = total - wins
    avg_pnl = sum(t["pnl_pct"] for t in trades_data) / total if total > 0 else 0

    # Format dates
    for t in trades_data:
        if t["closed_at"] and "T" in t["closed_at"]:
            t["closed_at"] = t["closed_at"][:16].replace("T", " ")

    return templates.TemplateResponse(request, "closed_trades.html", {
        "active_page": "closed_trades",
        "trades": trades_data,
        "summary": {"total": total, "wins": wins, "losses": losses, "avg_pnl": avg_pnl},
    })


# ─── Scheduler ───────────────────────────────────────────────────────────────


@router.get("/scheduler", response_class=HTMLResponse)
async def scheduler_page(request: Request):
    if not _check_admin(request):
        return RedirectResponse(url="/admin/login")

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "trigger": str(job.trigger),
            "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M %Z") if job.next_run_time else "—",
        })

    return templates.TemplateResponse(request, "scheduler.html", {
        "active_page": "scheduler",
        "jobs": jobs,
    })


@router.get("/scheduler/history", response_class=HTMLResponse)
async def scheduler_history_partial(request: Request, db: AsyncSession = Depends(get_db)):
    if not _check_admin(request):
        return Response(status_code=401)

    result = await db.execute(
        select(SchedulerRun).order_by(SchedulerRun.started_at.desc()).limit(50)
    )
    runs = []
    for run in result.scalars().all():
        runs.append({
            "job_name": run.job_name,
            "started_at": run.started_at.strftime("%Y-%m-%d %H:%M") if run.started_at else "",
            "finished_at": run.finished_at.strftime("%H:%M:%S") if run.finished_at else None,
            "status": run.status.value,
            "items_ingested": run.items_ingested,
            "error": run.error[:100] if run.error else None,
        })

    return templates.TemplateResponse(request, "partials/scheduler_history.html", {
        "runs": runs,
    })


# ─── LLM Logs & Costs ────────────────────────────────────────────────────────


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, db: AsyncSession = Depends(get_db)):
    if not _check_admin(request):
        return RedirectResponse(url="/admin/login")

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0)

    # Scheduler stats
    runs_today = await db.execute(
        select(func.count()).where(SchedulerRun.started_at >= today_start)
    )

    # Recent runs for log console
    recent = await db.execute(
        select(SchedulerRun).order_by(SchedulerRun.started_at.desc()).limit(50)
    )
    recent_runs = []
    for run in recent.scalars().all():
        duration = ""
        if run.finished_at and run.started_at:
            delta = run.finished_at - run.started_at
            duration = f"{delta.total_seconds():.1f}s"
        recent_runs.append({
            "job_name": run.job_name,
            "started_at": run.started_at.strftime("%H:%M:%S") if run.started_at else "",
            "status": run.status.value,
            "items_ingested": run.items_ingested,
            "duration": duration,
        })

    # Scheduler jobs
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "trigger": str(job.trigger),
            "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M %Z") if job.next_run_time else "—",
        })

    return templates.TemplateResponse(request, "logs.html", {
        "active_page": "logs",
        "llm_cap": settings.llm_daily_budget if hasattr(settings, "llm_daily_budget") else 1.00,
        "model_name": settings.llm_model if hasattr(settings, "llm_model") else "claude-sonnet-4-20250514",
        "scheduler_running": scheduler.running,
        "active_jobs": len(scheduler.get_jobs()),
        "runs_today": runs_today.scalar() or 0,
        "recent_runs": recent_runs,
        "jobs": jobs,
    })
