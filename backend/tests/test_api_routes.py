"""Tests for API routes and error handling."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "env" in data


async def test_recommendations_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/stocks/recommendations")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"]["code"] == "UNAUTHORIZED"


async def test_shark_deals_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/stocks/shark-deals")
    assert resp.status_code == 401


async def test_closed_trades_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/stocks/closed-trades")
    assert resp.status_code == 401


async def test_home_feed_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/feed/home")
    assert resp.status_code == 401


async def test_invalid_bearer_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/stocks/recommendations",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


async def test_admin_login_page_renders(client: AsyncClient):
    resp = await client.get("/admin/login")
    assert resp.status_code == 200
    assert "StockMaster" in resp.text
    assert "password" in resp.text.lower()


async def test_admin_dashboard_unauthenticated(client: AsyncClient):
    resp = await client.get("/admin/dashboard", follow_redirects=False)
    assert resp.status_code in (302, 303, 307)
    assert "/admin/login" in resp.headers.get("location", "")


async def test_admin_login_wrong_password(client: AsyncClient):
    resp = await client.post(
        "/admin/login",
        data={"password": "wrong-password"},
        follow_redirects=False,
    )
    assert resp.status_code == 200
    assert "invalid" in resp.text.lower() or "incorrect" in resp.text.lower()


async def test_404_returns_json(client: AsyncClient):
    resp = await client.get("/api/v1/nonexistent-route")
    assert resp.status_code == 404


async def test_openapi_available_in_qa(client: AsyncClient):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["info"]["title"] == "StockMaster API"
