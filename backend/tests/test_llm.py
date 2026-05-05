"""Tests for LLM recommendation service — mocked Anthropic calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm import _build_user_prompt, generate_recommendations


def test_build_user_prompt_basic():
    prompt = _build_user_prompt(
        instrument_name="Reliance Industries Ltd",
        symbol="500325",
        sector="Energy",
        recent_price=2450.50,
        deals_context="- 2026-05-01 | RARE ENTERPRISES | BUY | Qty: 50,000 | ₹2450.50",
        news_context="",
    )
    assert "Reliance Industries Ltd" in prompt
    assert "500325" in prompt
    assert "Energy" in prompt
    assert "2450.50" in prompt
    assert "RARE ENTERPRISES" in prompt


def test_build_user_prompt_no_data():
    prompt = _build_user_prompt(
        instrument_name="TCS",
        symbol="532540",
        sector=None,
        recent_price=None,
        deals_context="",
        news_context="",
    )
    assert "TCS" in prompt
    assert "Unknown" in prompt
    assert "Recent Price" not in prompt


@pytest.mark.asyncio
async def test_generate_recommendations_success():
    """Test that generate_recommendations correctly parses Claude's tool_use response."""
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "submit_recommendations"
    mock_tool_block.input = {
        "recommendations": [
            {
                "horizon": "short",
                "action": "BUY",
                "entry": 2450.0,
                "target": 2700.0,
                "stoploss": 2350.0,
                "confidence": 0.75,
                "rationale": "Strong momentum and institutional buying.",
                "risk_factors": ["Market volatility", "Oil price sensitivity"],
            },
            {
                "horizon": "mid",
                "action": "BUY",
                "entry": 2450.0,
                "target": 3000.0,
                "stoploss": 2200.0,
                "confidence": 0.70,
                "rationale": "Sector rotation favoring energy.",
                "risk_factors": ["Policy changes", "Crude oil fluctuations"],
            },
            {
                "horizon": "long",
                "action": "HOLD",
                "entry": 2450.0,
                "target": 3500.0,
                "stoploss": 2100.0,
                "confidence": 0.65,
                "rationale": "Diversified business provides stability.",
                "risk_factors": ["Regulatory risk", "Capex execution"],
            },
        ]
    }

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]
    mock_response.usage = MagicMock(input_tokens=1000, output_tokens=500)

    with patch("app.services.llm.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        result = await generate_recommendations(
            instrument_name="Reliance Industries",
            symbol="500325",
            sector="Energy",
            recent_price=2450.0,
            deals_context="Some deals",
            news_context="Some news",
        )

    assert len(result["recommendations"]) == 3
    assert result["recommendations"][0]["horizon"] == "short"
    assert result["recommendations"][0]["action"] == "BUY"
    assert result["recommendations"][0]["entry"] == 2450.0
    assert result["meta"]["model"] == "claude-sonnet-4-20250514"
    assert result["meta"]["input_tokens"] == 1000
    assert result["meta"]["output_tokens"] == 500
    assert result["meta"]["cost_usd"] > 0


@pytest.mark.asyncio
async def test_generate_recommendations_no_tool_call():
    """Test that we raise ValueError if Claude doesn't call the tool."""
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Here are my recommendations..."

    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_response.usage = MagicMock(input_tokens=500, output_tokens=200)

    with patch("app.services.llm.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        with pytest.raises(ValueError, match="did not call submit_recommendations"):
            await generate_recommendations(
                instrument_name="TCS",
                symbol="532540",
            )


@pytest.mark.asyncio
async def test_generate_recommendations_wrong_horizon_count():
    """Test validation fails when not all 3 horizons are present."""
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "submit_recommendations"
    mock_tool_block.input = {
        "recommendations": [
            {
                "horizon": "short",
                "action": "BUY",
                "entry": 100.0,
                "target": 110.0,
                "stoploss": 95.0,
                "confidence": 0.7,
                "rationale": "Test",
                "risk_factors": [],
            },
            {
                "horizon": "short",  # duplicate!
                "action": "SELL",
                "entry": 100.0,
                "target": 90.0,
                "stoploss": 105.0,
                "confidence": 0.6,
                "rationale": "Test",
                "risk_factors": [],
            },
            {
                "horizon": "mid",
                "action": "HOLD",
                "entry": 100.0,
                "target": 120.0,
                "stoploss": 90.0,
                "confidence": 0.5,
                "rationale": "Test",
                "risk_factors": [],
            },
        ]
    }

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]
    mock_response.usage = MagicMock(input_tokens=500, output_tokens=300)

    with patch("app.services.llm.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        with pytest.raises(ValueError, match="Missing horizons"):
            await generate_recommendations(
                instrument_name="Test",
                symbol="000001",
            )
