"""LLM service — Claude-powered stock recommendation generation.

Uses Anthropic tool_use to get structured JSON output for each horizon.
"""

import hashlib
import logging
from typing import Any

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

# The tool schema Claude will be forced to use
RECOMMENDATION_TOOL = {
    "name": "submit_recommendations",
    "description": "Submit stock recommendations for all three investment horizons.",
    "input_schema": {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "horizon": {
                            "type": "string",
                            "enum": ["short", "mid", "long"],
                            "description": "Investment horizon: short (1-2 weeks), mid (1-3 months), long (6-12 months)",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["BUY", "SELL", "HOLD"],
                            "description": "Recommended trading action",
                        },
                        "entry": {
                            "type": "number",
                            "description": "Recommended entry price in INR",
                        },
                        "target": {
                            "type": "number",
                            "description": "Target price in INR for this horizon",
                        },
                        "stoploss": {
                            "type": "number",
                            "description": "Stop-loss price in INR",
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence score 0.0 to 1.0",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "2-4 sentence explanation of the recommendation",
                        },
                        "risk_factors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Top 2-4 risk factors for this recommendation",
                        },
                    },
                    "required": [
                        "horizon",
                        "action",
                        "entry",
                        "target",
                        "stoploss",
                        "confidence",
                        "rationale",
                        "risk_factors",
                    ],
                },
                "minItems": 3,
                "maxItems": 3,
            }
        },
        "required": ["recommendations"],
    },
}


def _build_system_prompt() -> str:
    return """You are StockMaster AI, an expert Indian stock market analyst.
You analyze stocks listed on BSE/NSE and provide actionable recommendations.

Guidelines:
- Entry price should be close to the current market price (within 2% for short-term).
- Target: short-term +5-12%, mid-term +10-25%, long-term +20-50%.
- Stoploss: short-term -3-5%, mid-term -7-12%, long-term -10-15%.
- Confidence reflects the strength of supporting signals (0.5 = neutral, 0.8+ = strong conviction).
- Be conservative. If uncertain, recommend HOLD with moderate confidence.
- Always consider sector trends, recent deal activity, and market conditions.
- Risk factors must be specific to this stock, not generic market risks.
- Rationale must reference specific data points from the context provided.

IMPORTANT: You MUST call the submit_recommendations tool with exactly 3 recommendations (one per horizon: short, mid, long). Do not output any other text."""


def _build_user_prompt(
    instrument_name: str,
    symbol: str,
    sector: str | None,
    recent_price: float | None,
    deals_context: str,
    news_context: str,
) -> str:
    parts = [
        f"## Analyze: {instrument_name} ({symbol})",
        f"Sector: {sector or 'Unknown'}",
    ]
    if recent_price:
        parts.append(f"Current/Recent Price: ₹{recent_price:.2f}")
    if deals_context:
        parts.append(f"\n### Recent Bulk/Block Deals:\n{deals_context}")
    if news_context:
        parts.append(f"\n### Recent News:\n{news_context}")

    parts.append(
        "\nProvide recommendations for all three horizons (short, mid, long) "
        "by calling the submit_recommendations tool."
    )
    return "\n".join(parts)


async def generate_recommendations(
    instrument_name: str,
    symbol: str,
    sector: str | None = None,
    recent_price: float | None = None,
    deals_context: str = "",
    news_context: str = "",
) -> dict[str, Any]:
    """Call Claude to generate recommendations for one instrument.

    Returns:
        {
            "recommendations": [...],  # list of 3 recommendation dicts
            "meta": {"model": ..., "input_tokens": ..., "output_tokens": ..., "cost_usd": ..., "prompt_hash": ...}
        }
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    user_prompt = _build_user_prompt(
        instrument_name=instrument_name,
        symbol=symbol,
        sector=sector,
        recent_price=recent_price,
        deals_context=deals_context,
        news_context=news_context,
    )

    prompt_hash = hashlib.sha256(user_prompt.encode()).hexdigest()[:16]

    try:
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            system=_build_system_prompt(),
            messages=[{"role": "user", "content": user_prompt}],
            tools=[RECOMMENDATION_TOOL],
            tool_choice={"type": "tool", "name": "submit_recommendations"},
        )
    except anthropic.APIError as e:
        logger.error("Anthropic API error for %s: %s", symbol, e)
        raise

    # Extract tool use block
    tool_block = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_recommendations":
            tool_block = block
            break

    if not tool_block:
        raise ValueError(f"Claude did not call submit_recommendations for {symbol}")

    recommendations = tool_block.input.get("recommendations", [])
    if len(recommendations) != 3:
        raise ValueError(
            f"Expected 3 recommendations for {symbol}, got {len(recommendations)}"
        )

    # Validate horizons
    horizons_seen = {r["horizon"] for r in recommendations}
    if horizons_seen != {"short", "mid", "long"}:
        raise ValueError(f"Missing horizons for {symbol}: got {horizons_seen}")

    # Cost estimation (Claude Sonnet pricing: ~$3/1M input, $15/1M output)
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)

    meta = {
        "model": settings.anthropic_model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 6),
        "prompt_hash": prompt_hash,
    }

    return {"recommendations": recommendations, "meta": meta}
