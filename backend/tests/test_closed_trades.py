"""Tests for closed trades service logic."""

from app.db.models import RecommendationAction
from app.services.closed_trades import _calculate_pnl


def test_calculate_pnl_buy_profit():
    pnl = _calculate_pnl(RecommendationAction.BUY, entry=100.0, exit_price=112.0)
    assert pnl == 12.0


def test_calculate_pnl_buy_loss():
    pnl = _calculate_pnl(RecommendationAction.BUY, entry=100.0, exit_price=95.0)
    assert pnl == -5.0


def test_calculate_pnl_sell_profit():
    # Short: entry high, exit low = profit
    pnl = _calculate_pnl(RecommendationAction.SELL, entry=100.0, exit_price=88.0)
    assert pnl == 12.0


def test_calculate_pnl_sell_loss():
    # Short: entry low, exit high = loss
    pnl = _calculate_pnl(RecommendationAction.SELL, entry=100.0, exit_price=105.0)
    assert pnl == -5.0


def test_calculate_pnl_hold():
    pnl = _calculate_pnl(RecommendationAction.HOLD, entry=100.0, exit_price=110.0)
    assert pnl == 0.0


def test_calculate_pnl_precision():
    pnl = _calculate_pnl(RecommendationAction.BUY, entry=2450.0, exit_price=2744.0)
    assert pnl == 12.0  # (2744 - 2450) / 2450 * 100 = 12.0
