"""
Unit tests for settings.py

Verifies that approved constraints are enforced at the settings level.
"""
from __future__ import annotations

import pytest
from src.config.settings import RiskSettings, StrategySettings, AppSettings


class TestRiskSettings:
    def test_min_rr_cannot_be_set_below_2(self) -> None:
        """R40: min_reward_to_risk enforced at settings level."""
        with pytest.raises(Exception, match="2.0"):
            RiskSettings(min_reward_to_risk=1.5)

    def test_risk_pct_below_minimum_rejected(self) -> None:
        with pytest.raises(Exception):
            RiskSettings(risk_pct_per_trade=0.001)

    def test_risk_pct_above_maximum_rejected(self) -> None:
        with pytest.raises(Exception):
            RiskSettings(risk_pct_per_trade=6.0)

    def test_approved_defaults(self) -> None:
        s = RiskSettings()
        assert s.risk_pct_per_trade == 1.0
        assert s.min_reward_to_risk == 2.0
        assert s.max_daily_trades == 5
        assert s.daily_loss_pct == 3.0
        assert s.max_consecutive_losses == 3


class TestStrategySettings:
    def test_approved_defaults(self) -> None:
        s = StrategySettings()
        assert "XAUUSD" in s.symbols
        assert "BTCUSD" in s.symbols
        assert s.timeframe == "H1"
        assert s.entry_trigger_mode == "CANDLE_CLOSE"
        assert s.pivot_left_bars == 2
        assert s.pivot_right_bars == 2
        assert s.max_fvg_age_bars == 24
        assert s.max_setup_age_bars_after_sweep == 12
        assert s.min_fvg_atr_factor == 0.1
        assert s.min_fvg_ticks == 2


class TestAppSettings:
    def test_live_mode_blocked(self) -> None:
        """IMPL7: live trading permanently disabled."""
        with pytest.raises(Exception, match="[Ll]ive"):
            AppSettings(execution_mode="live")

    def test_paper_mode_allowed(self) -> None:
        s = AppSettings(execution_mode="paper")
        assert s.execution_mode == "paper"

    def test_demo_mode_allowed(self) -> None:
        s = AppSettings(execution_mode="demo")
        assert s.execution_mode == "demo"
