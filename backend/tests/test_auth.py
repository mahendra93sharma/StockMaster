"""Tests for health and basic auth endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "env" in data


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_google_auth_invalid_token(client):
    response = await client.post("/api/v1/auth/google", json={"id_token": "invalid"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "bogus"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_unauthenticated(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401
