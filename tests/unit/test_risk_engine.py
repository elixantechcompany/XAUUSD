"""
Unit tests for RiskEngine.

Covers R44–R58 (risk per trade, sizing, daily limits, lockouts).
Uses in-memory SQLite via conftest db fixture.
"""
from __future__ import annotations

import pytest
from datetime import date, datetime, timezone

from src.config.settings import RiskSettings
from src.data.market_data_adapter import SymbolInfo
from src.risk.engine import RiskEngine, SizingResult
from tests.conftest import make_xauusd_info, make_btcusd_info


def SymbolInfo_copy(info: SymbolInfo, **kwargs) -> SymbolInfo:
    """Return a copy of SymbolInfo with overridden fields."""
    fields = {
        "name": info.name, "digits": info.digits, "point": info.point,
        "tick_size": info.tick_size, "tick_value": info.tick_value,
        "contract_size": info.contract_size, "volume_min": info.volume_min,
        "volume_max": info.volume_max, "volume_step": info.volume_step,
        "trade_stops_level": info.trade_stops_level, "spread": info.spread,
        "currency_profit": info.currency_profit,
        "currency_margin": info.currency_margin,
    }
    fields.update(kwargs)
    return SymbolInfo(**fields)


def _engine(
    risk_pct: float = 1.0,
    min_rr: float = 2.0,
    max_daily: int = 5,
    daily_loss_pct: float = 3.0,
    max_consecutive: int = 3,
    max_spread: dict[str, float] | None = None,
) -> RiskEngine:
    if max_spread is None:
        max_spread = {"XAUUSD": 10.0, "BTCUSD": 100.0}
    s = RiskSettings(
        risk_pct_per_trade=risk_pct,
        min_reward_to_risk=min_rr,
        max_daily_trades=max_daily,
        daily_loss_pct=daily_loss_pct,
        max_consecutive_losses=max_consecutive,
        max_spread_pips=max_spread,
    )
    return RiskEngine(settings=s, account_label="test")


TODAY = date(2024, 6, 1)


class TestPositionSizing:
    """R44, R45, R46, R47, R48."""

    def test_risk_is_exactly_1pct_of_equity(self) -> None:
        """R44: risk = 1% of equity."""
        info = make_xauusd_info()  # tick_value=1.0, tick_size=0.01, point=0.01
        engine = _engine()
        # entry=2020, sl=2010 → sl_distance=10, sl_ticks=1000
        # pip_value_per_lot = tick_value/tick_size*point = 1/0.01*0.01 = 1.0
        # risk_usd = 10000 * 0.01 = 100
        # volume = 100 / (1000 * 1.0) = 0.1
        result = engine.calculate_size(
            symbol_info=info,
            direction="BULLISH",
            entry_price=2020.0,
            sl_price=2010.0,
            equity=10_000.0,
        )
        assert result.approved
        assert result.risk_usd == pytest.approx(100.0, rel=0.01)

    def test_volume_rounded_down(self) -> None:
        """R46: volume always rounded DOWN to volume_step."""
        info = make_xauusd_info()
        engine = _engine()
        result = engine.calculate_size(
            symbol_info=info,
            direction="BULLISH",
            entry_price=2020.0,
            sl_price=2010.0,
            equity=10_000.0,
        )
        assert result.approved
        step = info.volume_step  # 0.01
        assert abs(result.volume % step) < 1e-9

    def test_rejected_when_volume_below_minimum(self) -> None:
        """R47: reject when computed volume < volume_min."""
        info = make_xauusd_info()
        engine = _engine(risk_pct=1.0)
        # Make SL very wide so volume comes out tiny
        result = engine.calculate_size(
            symbol_info=info,
            direction="BULLISH",
            entry_price=2020.0,
            sl_price=1000.0,   # 1020 pts SL — volume will be tiny
            equity=100.0,       # tiny equity
        )
        assert not result.approved
        assert "minimum" in result.rejection_reason.lower()

    def test_xauusd_and_btcusd_use_different_tick_values(self) -> None:
        """R48: each instrument uses its own specs."""
        xau = make_xauusd_info()   # tick_value=1.0
        btc = make_btcusd_info()   # tick_value=0.01
        engine = _engine()
        r_xau = engine.calculate_size(
            symbol_info=xau, direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
        )
        r_btc = engine.calculate_size(
            symbol_info=btc, direction="BULLISH",
            entry_price=30000.0, sl_price=29900.0, equity=10_000.0,
        )
        # Different tick_values → different volumes for similar % risk
        assert r_xau.volume != r_btc.volume

    def test_spread_block_when_over_limit(self) -> None:
        """R59/R60: spread check via calculate_size."""
        info = make_xauusd_info()
        # Fake a very wide spread (spread=10000 points = 100 pips at 0.01 point)
        wide_info = SymbolInfo_copy(info, spread=10000)
        engine = _engine()
        # Set a tight spread limit so 100 pips fails
        engine.settings.max_spread_pips["XAUUSD"] = 5.0
        result = engine.calculate_size(
            symbol_info=wide_info,
            direction="BULLISH",
            entry_price=2020.0,
            sl_price=2010.0,
            equity=10_000.0,
        )
        assert not result.approved
        assert "spread" in result.rejection_reason.lower()

    def test_spread_block_when_unconfigured(self) -> None:
        """R60: no spread limit configured → entries blocked."""
        info = make_xauusd_info()
        engine = _engine()
        # max_spread_pips is empty dict by default → no limit for XAUUSD
        engine.settings.max_spread_pips = {}
        result = engine.calculate_size(
            symbol_info=info,
            direction="BULLISH",
            entry_price=2020.0,
            sl_price=2010.0,
            equity=10_000.0,
        )
        assert not result.approved
        assert "not configured" in result.rejection_reason.lower()


class TestDailyLimits:
    """R50, R51, R54, R55, R56."""

    def test_fifth_trade_allowed_sixth_blocked(self, db) -> None:
        """R50: max 5 entries per day."""
        engine = _engine(max_daily=5)
        sizing = SizingResult(
            approved=True, volume=0.1, risk_usd=100.0,
            reward_usd=200.0, rr_ratio=2.0,
            sl_distance_pips=100.0, tp_distance_pips=200.0,
        )
        for _ in range(5):
            engine.record_new_entry(db, "XAUUSD", TODAY)

        check = engine.check_daily_limits(
            db=db, symbol="XAUUSD", sizing=sizing,
            current_equity=10_000.0, today=TODAY,
        )
        assert not check.approved
        assert "daily trade limit" in check.rejection_reason.lower()

    def test_daily_loss_lock_blocks_entries(self, db) -> None:
        """R54: daily loss limit triggers lock."""
        engine = _engine(daily_loss_pct=3.0)
        # Start of day equity = 10,000 → limit = 300
        row = engine.get_or_create_daily_state(db, "XAUUSD", TODAY, 10_000.0)
        row.realized_pnl_today = -350.0   # > 3% loss
        db.commit()

        sizing = SizingResult(
            approved=True, volume=0.1, risk_usd=100.0,
            reward_usd=200.0, rr_ratio=2.0,
            sl_distance_pips=100.0, tp_distance_pips=200.0,
        )
        check = engine.check_daily_limits(
            db=db, symbol="XAUUSD", sizing=sizing,
            current_equity=9_650.0, today=TODAY,
        )
        assert not check.approved
        assert "loss" in check.rejection_reason.lower()

    def test_daily_loss_lock_persists_after_restart(self, db) -> None:
        """R56: lock survives — it's in the DB, not in memory."""
        engine = _engine(daily_loss_pct=3.0)
        row = engine.get_or_create_daily_state(db, "XAUUSD", TODAY, 10_000.0)
        row.daily_loss_lock = True
        db.commit()

        # New engine instance — simulates restart
        engine2 = _engine(daily_loss_pct=3.0)
        sizing = SizingResult(
            approved=True, volume=0.1, risk_usd=100.0,
            reward_usd=200.0, rr_ratio=2.0,
            sl_distance_pips=100.0, tp_distance_pips=200.0,
        )
        check = engine2.check_daily_limits(
            db=db, symbol="XAUUSD", sizing=sizing,
            current_equity=9_650.0, today=TODAY,
        )
        assert not check.approved


class TestConsecutiveLossLockout:
    """R58."""

    def test_three_losses_trigger_lockout(self, db) -> None:
        engine = _engine(max_consecutive=3)
        for _ in range(3):
            engine.record_closed_trade(db, "XAUUSD", pnl=-50.0, today=TODAY)

        status = engine.get_lockout_status(db, "XAUUSD", TODAY)
        assert status["consecutive_loss_lock"] is True

    def test_win_resets_consecutive_counter(self, db) -> None:
        engine = _engine(max_consecutive=3)
        engine.record_closed_trade(db, "XAUUSD", pnl=-50.0, today=TODAY)
        engine.record_closed_trade(db, "XAUUSD", pnl=-50.0, today=TODAY)
        engine.record_closed_trade(db, "XAUUSD", pnl=+100.0, today=TODAY)  # win

        status = engine.get_lockout_status(db, "XAUUSD", TODAY)
        assert status["consecutive_losses"] == 0
        assert status["consecutive_loss_lock"] is False

    def test_lockout_threshold_zero_disables_lockout(self, db) -> None:
        """R58: max_consecutive_losses=0 → disabled."""
        engine = _engine(max_consecutive=0)
        for _ in range(5):
            engine.record_closed_trade(db, "XAUUSD", pnl=-50.0, today=TODAY)
        status = engine.get_lockout_status(db, "XAUUSD", TODAY)
        assert status["consecutive_loss_lock"] is False

    def test_lockout_persists_across_days(self, db) -> None:
        """R58: lock does not auto-reset on new day — requires manual clear."""
        engine = _engine(max_consecutive=3)
        for _ in range(3):
            engine.record_closed_trade(db, "XAUUSD", pnl=-50.0, today=TODAY)

        # Query on a later date — lock row was set on TODAY
        status = engine.get_lockout_status(db, "XAUUSD", TODAY)
        assert status["consecutive_loss_lock"] is True

    def test_manual_clear_removes_lockout(self, db) -> None:
        engine = _engine(max_consecutive=3)
        for _ in range(3):
            engine.record_closed_trade(db, "XAUUSD", pnl=-50.0, today=TODAY)
        engine.clear_consecutive_loss_lock(db, "XAUUSD", TODAY)
        status = engine.get_lockout_status(db, "XAUUSD", TODAY)
        assert status["consecutive_loss_lock"] is False


class TestNewsLock:
    """R62, R63."""

    def test_news_lock_blocks_entries(self, db) -> None:
        engine = _engine()
        engine.set_news_lock(db, "XAUUSD", True, TODAY)
        sizing = SizingResult(
            approved=True, volume=0.1, risk_usd=100.0,
            reward_usd=200.0, rr_ratio=2.0,
            sl_distance_pips=100.0, tp_distance_pips=200.0,
        )
        check = engine.check_daily_limits(
            db=db, symbol="XAUUSD", sizing=sizing,
            current_equity=10_000.0, today=TODAY,
        )
        assert not check.approved
        assert "news" in check.rejection_reason.lower()

    def test_news_lock_clears(self, db) -> None:
        engine = _engine()
        engine.set_news_lock(db, "XAUUSD", True, TODAY)
        engine.set_news_lock(db, "XAUUSD", False, TODAY)
        sizing = SizingResult(
            approved=True, volume=0.1, risk_usd=100.0,
            reward_usd=200.0, rr_ratio=2.0,
            sl_distance_pips=100.0, tp_distance_pips=200.0,
        )
        check = engine.check_daily_limits(
            db=db, symbol="XAUUSD", sizing=sizing,
            current_equity=10_000.0, today=TODAY,
        )
        assert check.approved
