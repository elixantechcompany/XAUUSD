"""
Unit tests for BreakEvenTrailingManager.

Covers R89–R96 (spec v1.1): break-even trigger, stop placement,
ATR trailing stop, direction correctness, and prohibited behaviours.

All tests use synthetic candles. No MT5 connection required.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.strategy.strategy_core import BreakEvenTrailingManager, StopUpdateResult

BASE = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(h: int, lo: float, hi: float, c: float | None = None) -> Candle:
    if c is None:
        c = (lo + hi) / 2
    o = (lo + hi) / 2
    return Candle(
        time=_t(h), open=o, high=hi, low=lo, close=c,
        volume=100.0, symbol="XAUUSD", timeframe="H1",
    )


def _candles(n: int = 20, lo: float = 2000.0, hi: float = 2004.0) -> list[Candle]:
    """n flat candles — ATR ≈ hi - lo = 4.0."""
    return [_c(i, lo=lo, hi=hi) for i in range(n)]


def _manager(
    be_pct: float = 0.50,
    atr_factor: float = 1.0,
    tick_size: float = 0.01,
    trade_stops_level: int = 0,
    point: float = 0.01,
) -> BreakEvenTrailingManager:
    return BreakEvenTrailingManager(
        breakeven_trigger_pct=be_pct,
        trailing_atr_factor=atr_factor,
        atr_period=14,
        tick_size=tick_size,
        trade_stops_level=trade_stops_level,
        point=point,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Initialisation
# ─────────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_raises_on_invalid_pct(self) -> None:
        with pytest.raises(ValueError):
            BreakEvenTrailingManager(breakeven_trigger_pct=0.0)

    def test_raises_on_negative_atr_factor(self) -> None:
        with pytest.raises(ValueError):
            BreakEvenTrailingManager(trailing_atr_factor=-1.0)


# ─────────────────────────────────────────────────────────────────────────────
# R89: break-even trigger — bullish
# ─────────────────────────────────────────────────────────────────────────────

class TestBullishBreakEvenTrigger:
    """R89: fires when price reaches 50% of the way to TP."""

    def _setup(self, entry=2020.0, sl=2010.0, tp=2040.0):
        # At 50% progress: price = entry + 0.5*(tp-entry) = 2020 + 0.5*20 = 2030
        return entry, sl, tp

    def test_triggers_at_exact_50pct(self) -> None:
        entry, sl, tp = self._setup()
        mgr = _manager()
        candles = _candles(20)
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=sl, breakeven_fired=False,
            best_close_since_entry=2030.0,   # exactly 50%
            candles=candles, close_price=2030.0,
        )
        assert result.should_update is True
        assert result.is_breakeven is True
        assert result.new_sl == pytest.approx(entry, abs=0.01)

    def test_does_not_trigger_below_50pct(self) -> None:
        entry, sl, tp = self._setup()
        mgr = _manager()
        candles = _candles(20)
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=sl, breakeven_fired=False,
            best_close_since_entry=2029.0,   # 45% progress
            candles=candles, close_price=2029.0,
        )
        assert result.should_update is False

    def test_sl_set_to_exact_entry(self) -> None:
        """R90: new SL = exact entry price."""
        entry, sl, tp = self._setup()
        mgr = _manager()
        candles = _candles(20)
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=sl, breakeven_fired=False,
            best_close_since_entry=2035.0,
            candles=candles, close_price=2035.0,
        )
        assert result.should_update is True
        assert result.new_sl == pytest.approx(entry, abs=0.01)

    def test_skipped_when_sl_already_at_entry(self) -> None:
        """R89: skip if SL already at or above entry."""
        entry, sl, tp = self._setup()
        mgr = _manager()
        candles = _candles(20)
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=entry,   # already at break-even
            breakeven_fired=False,
            best_close_since_entry=2035.0,
            candles=candles, close_price=2035.0,
        )
        assert result.should_update is False

    def test_deferred_when_broker_min_stop_not_met(self) -> None:
        """R90: deferred when min stop distance not satisfied."""
        entry = 2020.0
        sl    = 2010.0
        tp    = 2040.0
        # trade_stops_level=100 points = 100*0.01 = 1.0 price units
        # At close_price=2020.5, distance from entry to close = 0.5 < 1.0
        mgr = _manager(trade_stops_level=100, point=0.01)
        candles = _candles(20)
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=sl, breakeven_fired=False,
            best_close_since_entry=2030.0,
            candles=candles, close_price=2030.0,
        )
        # The broker min is 1.0; close is 2030 and entry is 2020 → dist=10 > 1.0
        # so it should NOT defer here. Let's make close very close to entry:
        result2 = mgr.evaluate(
            direction="BULLISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=sl, breakeven_fired=False,
            best_close_since_entry=2030.0,
            candles=candles, close_price=2020.05,   # < 1.0 from entry
        )
        # best_close_since_entry is still 2030 so trigger should fire
        # but the min stop check uses current price (close_price)
        # Deferred because |2020.05 - 2020.0| = 0.05 < 1.0
        assert result2.should_update is False
        assert "deferring" in result2.reason.lower()


# ─────────────────────────────────────────────────────────────────────────────
# R89: break-even trigger — bearish
# ─────────────────────────────────────────────────────────────────────────────

class TestBearishBreakEvenTrigger:
    def test_triggers_at_50pct_bearish(self) -> None:
        # entry=2050, sl=2060, tp=2030 → 50% = 2050 - 0.5*(2050-2030) = 2040
        entry, sl, tp = 2050.0, 2060.0, 2030.0
        mgr = _manager()
        candles = _candles(20, lo=2040.0, hi=2044.0)
        result = mgr.evaluate(
            direction="BEARISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=sl, breakeven_fired=False,
            best_close_since_entry=2040.0,   # exactly 50% = (2050-2040)/(2050-2030) = 0.5
            candles=candles, close_price=2040.0,
        )
        assert result.should_update is True
        assert result.is_breakeven is True
        assert result.new_sl == pytest.approx(entry, abs=0.01)

    def test_does_not_trigger_below_50pct_bearish(self) -> None:
        entry, sl, tp = 2050.0, 2060.0, 2030.0
        mgr = _manager()
        candles = _candles(20, lo=2040.0, hi=2044.0)
        result = mgr.evaluate(
            direction="BEARISH",
            entry_price=entry, original_sl=sl, tp_price=tp,
            current_sl=sl, breakeven_fired=False,
            best_close_since_entry=2041.0,   # 45% progress (2050-2041)/(2050-2030)=0.45
            candles=candles, close_price=2041.0,
        )
        assert result.should_update is False


# ─────────────────────────────────────────────────────────────────────────────
# R92–R93: ATR trailing stop — bullish
# ─────────────────────────────────────────────────────────────────────────────

class TestBullishTrailing:
    """R92: trailing only active after BE. R93: trail = best_close - 1*ATR."""

    def test_no_trailing_before_breakeven(self) -> None:
        mgr = _manager()
        candles = _candles(20)
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=2020.0, original_sl=2010.0, tp_price=2040.0,
            current_sl=2020.0,  # SL at entry (as if BE just fired)
            breakeven_fired=False,  # BE not marked fired yet
            best_close_since_entry=2035.0,
            candles=candles, close_price=2035.0,
        )
        # breakeven_fired=False means we check BE trigger first, not trailing
        # Since current_sl=entry already, BE is skipped, and trailing not yet active
        assert result.should_update is False

    def test_trailing_activates_after_breakeven(self) -> None:
        """R92: trailing fires when breakeven_fired=True."""
        mgr = _manager(atr_factor=1.0)
        # ATR ≈ 4.0 with these candles
        candles = _candles(20, lo=2000.0, hi=2004.0)
        # best_close = 2035, trail = 2035 - 1.0*4.0 = 2031
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=2020.0, original_sl=2010.0, tp_price=2040.0,
            current_sl=2020.0,   # at break-even
            breakeven_fired=True,
            best_close_since_entry=2035.0,
            candles=candles, close_price=2035.0,
        )
        assert result.should_update is True
        assert result.is_trailing is True
        assert result.new_sl == pytest.approx(2031.0, abs=0.05)

    def test_trailing_never_moves_backward(self) -> None:
        """R96: SL only moves in favourable direction."""
        mgr = _manager(atr_factor=1.0)
        candles = _candles(20, lo=2000.0, hi=2004.0)
        # best_close = 2025 (price pulled back), trail = 2025 - 4 = 2021
        # current_sl = 2031 (already higher) — should NOT move down to 2021
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=2020.0, original_sl=2010.0, tp_price=2040.0,
            current_sl=2031.0,
            breakeven_fired=True,
            best_close_since_entry=2025.0,   # price pulled back
            candles=candles, close_price=2025.0,
        )
        assert result.should_update is False

    def test_trailing_sl_never_below_entry_after_breakeven(self) -> None:
        """R96: SL must not go below entry once BE is set."""
        mgr = _manager(atr_factor=10.0)  # huge factor to push SL below entry
        candles = _candles(20, lo=2000.0, hi=2004.0)
        # best_close = 2022, ATR=4, trail = 2022 - 40 = 1982 (below entry=2020)
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=2020.0, original_sl=2010.0, tp_price=2040.0,
            current_sl=2020.0,
            breakeven_fired=True,
            best_close_since_entry=2022.0,
            candles=candles, close_price=2022.0,
        )
        assert result.should_update is False


# ─────────────────────────────────────────────────────────────────────────────
# R93–R94: ATR trailing stop — bearish
# ─────────────────────────────────────────────────────────────────────────────

class TestBearishTrailing:
    def test_trailing_bearish(self) -> None:
        """R93: bear trail = lowest_close + 1*ATR."""
        mgr = _manager(atr_factor=1.0)
        candles = _candles(20, lo=2000.0, hi=2004.0)
        # best_close(bear)=2035, trail = 2035 + 4.0 = 2039
        # current_sl = 2050 (original) — 2039 < 2050 so this improves
        result = mgr.evaluate(
            direction="BEARISH",
            entry_price=2050.0, original_sl=2060.0, tp_price=2030.0,
            current_sl=2050.0,   # at break-even
            breakeven_fired=True,
            best_close_since_entry=2035.0,
            candles=candles, close_price=2035.0,
        )
        assert result.should_update is True
        assert result.is_trailing is True
        assert result.new_sl == pytest.approx(2039.0, abs=0.05)

    def test_trailing_never_moves_backward_bearish(self) -> None:
        """R96: bear SL only moves down (toward lower prices)."""
        mgr = _manager(atr_factor=1.0)
        candles = _candles(20, lo=2000.0, hi=2004.0)
        # best_close = 2045 (price bounced up), trail = 2045 + 4 = 2049
        # current_sl = 2039 (already tighter) — should NOT move up to 2049
        result = mgr.evaluate(
            direction="BEARISH",
            entry_price=2050.0, original_sl=2060.0, tp_price=2030.0,
            current_sl=2039.0,
            breakeven_fired=True,
            best_close_since_entry=2045.0,
            candles=candles, close_price=2045.0,
        )
        assert result.should_update is False


# ─────────────────────────────────────────────────────────────────────────────
# R93: ATR unavailable — graceful skip
# ─────────────────────────────────────────────────────────────────────────────

class TestATRUnavailable:
    def test_trailing_skipped_when_atr_unavailable(self) -> None:
        """R93: skip trailing if ATR cannot be computed (< 15 candles)."""
        mgr = _manager()
        candles = _candles(5)  # only 5 candles — ATR(14) needs 15
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=2020.0, original_sl=2010.0, tp_price=2040.0,
            current_sl=2020.0,
            breakeven_fired=True,
            best_close_since_entry=2035.0,
            candles=candles, close_price=2035.0,
        )
        assert result.should_update is False
        assert "atr" in result.reason.lower()


# ─────────────────────────────────────────────────────────────────────────────
# R96: TP unchanged
# ─────────────────────────────────────────────────────────────────────────────

class TestTPUnchanged:
    def test_breakeven_does_not_change_tp(self) -> None:
        """R96: manager never modifies TP — only returns new_sl."""
        mgr = _manager()
        candles = _candles(20)
        original_tp = 2040.0
        result = mgr.evaluate(
            direction="BULLISH",
            entry_price=2020.0, original_sl=2010.0, tp_price=original_tp,
            current_sl=2010.0, breakeven_fired=False,
            best_close_since_entry=2030.0,
            candles=candles, close_price=2030.0,
        )
        # The result only contains new_sl — no TP field
        assert not hasattr(result, "new_tp") or getattr(result, "new_tp", None) is None


# ─────────────────────────────────────────────────────────────────────────────
# update_best_close utility
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateBestClose:
    def test_bullish_tracks_highest(self) -> None:
        assert BreakEvenTrailingManager.update_best_close("BULLISH", 2030.0, 2035.0) == 2035.0
        assert BreakEvenTrailingManager.update_best_close("BULLISH", 2030.0, 2025.0) == 2030.0

    def test_bearish_tracks_lowest(self) -> None:
        assert BreakEvenTrailingManager.update_best_close("BEARISH", 2030.0, 2025.0) == 2025.0
        assert BreakEvenTrailingManager.update_best_close("BEARISH", 2030.0, 2035.0) == 2030.0

    def test_none_initialises_to_current(self) -> None:
        assert BreakEvenTrailingManager.update_best_close("BULLISH", None, 2030.0) == 2030.0
        assert BreakEvenTrailingManager.update_best_close("BEARISH", None, 2030.0) == 2030.0
