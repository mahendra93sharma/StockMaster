"""V1 API router aggregation."""

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.feed import router as feed_router
from app.api.v1.stocks import router as stocks_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(stocks_router)
api_router.include_router(feed_router)
api_router.include_router(admin_router)
