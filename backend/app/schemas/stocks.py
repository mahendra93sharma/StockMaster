"""Pydantic schemas for stock/deal endpoints."""

from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    id: str
    instrument_name: str
    exchange: str
    action: str
    entry: float
    target: float
    stoploss: float
    confidence: float
    rationale: str
    risk_factors: list[str] = []
    horizon: str
    created_at: str


class PaginatedRecommendations(BaseModel):
    items: list[RecommendationResponse]
    cursor: str | None = None


class SharkDealResponse(BaseModel):
    id: str
    instrument_name: str
    symbol: str
    exchange: str
    party_name: str
    side: str
    qty: int
    avg_price: float
    pct_equity: float | None = None
    ts: str
    deal_type: str
    is_notable: bool = False
    notable_tags: list[str] | None = None


class PaginatedDeals(BaseModel):
    items: list[SharkDealResponse]
    cursor: str | None = None


class ClosedTradeResponse(BaseModel):
    id: str
    instrument_name: str
    exchange: str
    action: str
    entry: float
    exit_price: float
    pnl_pct: float
    close_reason: str
    horizon: str
    closed_at: str


class PaginatedClosedTrades(BaseModel):
    items: list[ClosedTradeResponse]
    cursor: str | None = None
