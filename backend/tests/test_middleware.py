"""Tests for middleware and metrics."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_security_headers(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


async def test_request_id_injected(client: AsyncClient):
    resp = await client.get("/health")
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0


async def test_request_id_preserved(client: AsyncClient):
    resp = await client.get("/health", headers={"X-Request-ID": "my-trace-123"})
    assert resp.headers["X-Request-ID"] == "my-trace-123"


async def test_metrics_endpoint(client: AsyncClient):
    # Make a request first so metrics have data
    await client.get("/health")
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text
    assert "GET" in resp.text
