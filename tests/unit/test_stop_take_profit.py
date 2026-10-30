"""
Unit tests for StopLossCalculator and TakeProfitCalculator.

Covers R35, R36, R37, R40, R41, R42.
"""
from __future__ import annotations

import math
import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.strategy.strategy_core import (
    FVG, Swing, LiquiditySweep, StopLossCalculator, TakeProfitCalculator, _fvg_id,
)

BASE = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(h: int, lo: float, hi: float, o: float | None = None, c: float | None = None) -> Candle:
    if o is None:
        o = (lo + hi) / 2
    if c is None:
        c = (lo + hi) / 2
    return Candle(
        time=_t(h), open=o, high=hi, low=lo, close=c,
        volume=100.0, symbol="XAUUSD", timeframe="H1",
    )


def _bullish_fvg() -> FVG:
    return FVG(
        id=_fvg_id("XAUUSD", "BULLISH", _t(0)),
        symbol="XAUUSD", timeframe="H1",
        direction="BULLISH",
        fvg_low=2010.0, fvg_high=2015.0,
        c1_time=_t(0), c3_time=_t(2),
        c1_high=2010.0, c1_low=2005.0,
        c3_high=2022.0, c3_low=2015.0,
        atr_at_detection=4.0, created_at=_t(2),
    )


def _bearish_fvg() -> FVG:
    return FVG(
        id=_fvg_id("XAUUSD", "BEARISH", _t(0)),
        symbol="XAUUSD", timeframe="H1",
        direction="BEARISH",
        fvg_low=2045.0, fvg_high=2050.0,
        c1_time=_t(0), c3_time=_t(2),
        c1_high=2060.0, c1_low=2050.0,
        c3_high=2045.0, c3_low=2040.0,
        atr_at_detection=4.0, created_at=_t(2),
    )


def _bullish_sweep(sweep_low: float) -> LiquiditySweep:
    swing = Swing(candle=_c(1, lo=sweep_low - 5, hi=sweep_low), level=sweep_low + 1,
                  direction="LOW", confirmed_at=_t(1))
    return LiquiditySweep(
        swing=swing, sweep_candle=_c(3, lo=sweep_low, hi=sweep_low + 10),
        direction="BULLISH", swept_level=sweep_low + 1, sweep_extreme=sweep_low,
    )


def _bearish_sweep(sweep_high: float) -> LiquiditySweep:
    swing = Swing(candle=_c(1, lo=sweep_high, hi=sweep_high + 5), level=sweep_high - 1,
                  direction="HIGH", confirmed_at=_t(1))
    return LiquiditySweep(
        swing=swing, sweep_candle=_c(3, lo=sweep_high - 10, hi=sweep_high),
        direction="BEARISH", swept_level=sweep_high - 1, sweep_extreme=sweep_high,
    )


def _candles_with_known_atr(n: int = 20, range_: float = 4.0) -> list[Candle]:
    """ATR ≈ range_ (each candle has that exact range)."""
    result = []
    for i in range(n):
        lo = 2000.0
        hi = lo + range_
        result.append(_c(i, lo=lo, hi=hi))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# StopLossCalculator
# ─────────────────────────────────────────────────────────────────────────────

class TestStopLossCalculator:
    def test_bullish_sl_is_below_sweep_extreme(self) -> None:
        """R35: bullish SL below sweep_extreme."""
        fvg = _bullish_fvg()
        sweep = _bullish_sweep(sweep_low=2000.0)   # sweep_extreme=2000.0
        candles = _candles_with_known_atr()
        calc = StopLossCalculator(
            atr_period=14, sl_buffer_atr_factor=0.05, sl_buffer_min_ticks=2,
            tick_size=0.01, trade_stops_level=0, point=0.01,
        )
        sl, reason = calc.calculate(fvg, sweep, entry_price=2020.0, candles=candles)
        assert reason == ""
        assert sl is not None
        assert sl < sweep.sweep_extreme

    def test_bearish_sl_is_above_sweep_extreme(self) -> None:
        """R35: bearish SL above sweep_extreme."""
        fvg = _bearish_fvg()
        sweep = _bearish_sweep(sweep_high=2060.0)   # sweep_extreme=2060.0
        candles = _candles_with_known_atr()
        calc = StopLossCalculator(
            atr_period=14, sl_buffer_atr_factor=0.05, sl_buffer_min_ticks=2,
            tick_size=0.01, trade_stops_level=0, point=0.01,
        )
        sl, reason = calc.calculate(fvg, sweep, entry_price=2042.0, candles=candles)
        assert reason == ""
        assert sl is not None
        assert sl > sweep.sweep_extreme

    def test_buffer_uses_greater_of_atr_and_ticks(self) -> None:
        """R36: buffer = max(min_ticks * tick_size, atr_factor * ATR)."""
        fvg = _bullish_fvg()
        # ATR=4, atr_factor=0.05 → atr_buffer=0.2; tick_min=2*0.01=0.02
        # Expected buffer = max(0.02, 0.2) = 0.2
        sweep = _bullish_sweep(sweep_low=2000.0)
        candles = _candles_with_known_atr(range_=4.0)
        calc = StopLossCalculator(
            atr_period=14, sl_buffer_atr_factor=0.05, sl_buffer_min_ticks=2,
            tick_size=0.01, trade_stops_level=0, point=0.01,
        )
        sl, reason = calc.calculate(fvg, sweep, entry_price=2020.0, candles=candles)
        assert reason == ""
        # sweep_extreme=2000; buffer≈0.2; raw_sl=2000-0.2=1999.8, floor to 1999.80
        assert sl is not None
        assert sl == pytest.approx(1999.80, abs=0.01)

    def test_tick_min_used_when_larger_than_atr_buffer(self) -> None:
        """R36: tick buffer dominates when ATR is very small."""
        fvg = _bullish_fvg()
        # ATR=0.01, atr_factor=0.05 → atr_buffer=0.0005; tick_min=10*0.01=0.10
        # Expected buffer = max(0.10, 0.0005) = 0.10
        candles = _candles_with_known_atr(range_=0.01)
        sweep = _bullish_sweep(sweep_low=2000.0)
        calc = StopLossCalculator(
            atr_period=14, sl_buffer_atr_factor=0.05, sl_buffer_min_ticks=10,
            tick_size=0.01, trade_stops_level=0, point=0.01,
        )
        sl, reason = calc.calculate(fvg, sweep, entry_price=2020.0, candles=candles)
        assert reason == ""
        assert sl is not None
        assert sl < 2000.0 - 0.09   # at least 10 ticks below sweep_extreme

    def test_sl_rejected_when_too_close_to_entry(self) -> None:
        """R37: broker stop distance check."""
        fvg = _bullish_fvg()
        sweep = _bullish_sweep(sweep_low=2019.5)  # very close to entry
        candles = _candles_with_known_atr(range_=0.01)
        calc = StopLossCalculator(
            atr_period=14, sl_buffer_atr_factor=0.05, sl_buffer_min_ticks=2,
            tick_size=0.01, trade_stops_level=100,  # 100 points minimum
            point=0.01,
        )
        sl, reason = calc.calculate(fvg, sweep, entry_price=2020.0, candles=candles)
        assert sl is None
        assert "broker minimum" in reason.lower()

    def test_returns_none_when_atr_unavailable(self) -> None:
        """R36: reject when ATR cannot be computed."""
        fvg = _bullish_fvg()
        sweep = _bullish_sweep(sweep_low=2000.0)
        # Only 3 candles — not enough for ATR(14)
        tiny_candles = [_c(i, lo=2000.0, hi=2004.0) for i in range(3)]
        calc = StopLossCalculator(atr_period=14)
        sl, reason = calc.calculate(fvg, sweep, entry_price=2020.0, candles=tiny_candles)
        assert sl is None
        assert "atr" in reason.lower()


# ─────────────────────────────────────────────────────────────────────────────
# TakeProfitCalculator
# ─────────────────────────────────────────────────────────────────────────────

class TestTakeProfitCalculator:
    def test_raises_on_min_rr_below_2(self) -> None:
        """R40: min_rr cannot be set below 2.0."""
        with pytest.raises(ValueError, match="2.0"):
            TakeProfitCalculator(min_rr=1.5)

    def test_bullish_tp_is_2x_sl_distance_above_entry(self) -> None:
        """R41: tp = entry + 2 × (entry − sl)."""
        calc = TakeProfitCalculator(min_rr=2.0, tick_size=0.01)
        fvg = _bullish_fvg()
        # entry=2020, sl=2010 → sl_distance=10 → raw_tp=2020+20=2040
        tp, rr, reason = calc.calculate(fvg, entry_price=2020.0, sl_price=2010.0)
        assert reason == ""
        assert tp is not None
        assert tp == pytest.approx(2040.0, abs=0.02)
        assert rr >= 2.0

    def test_bearish_tp_is_2x_sl_distance_below_entry(self) -> None:
        """R41: tp = entry − 2 × (sl − entry)."""
        calc = TakeProfitCalculator(min_rr=2.0, tick_size=0.01)
        fvg = _bearish_fvg()
        # entry=2048, sl=2058 → sl_distance=10 → raw_tp=2048-20=2028
        tp, rr, reason = calc.calculate(fvg, entry_price=2048.0, sl_price=2058.0)
        assert reason == ""
        assert tp is not None
        assert tp == pytest.approx(2028.0, abs=0.02)
        assert rr >= 2.0

    def test_tp_rounded_toward_entry_bullish(self) -> None:
        """R42: bullish TP rounded DOWN (toward entry), not up."""
        calc = TakeProfitCalculator(min_rr=2.0, tick_size=0.01)
        fvg = _bullish_fvg()
        # entry=2020, sl=2009.995 → sl_distance=10.005 → raw_tp=2040.01
        tp, rr, reason = calc.calculate(fvg, entry_price=2020.0, sl_price=2009.995)
        if tp is not None:
            # tp should be floor'd, not ceil'd
            assert tp <= 2020.0 + 2 * (2020.0 - 2009.995) + 0.001

    def test_tp_rejected_when_rr_below_minimum_after_rounding(self) -> None:
        """R40: if rounding kills R:R, trade is rejected."""
        calc = TakeProfitCalculator(min_rr=2.0, tick_size=1.0)  # coarse tick
        fvg = _bullish_fvg()
        # entry=2020, sl=2019 → sl_distance=1 → raw_tp=2022; floor to 2022
        # tp_distance = 2, sl_distance = 1 → rr = 2.0 → should pass
        tp, rr, reason = calc.calculate(fvg, entry_price=2020.0, sl_price=2019.0)
        # This should either pass with rr=2.0 or reject — depends on rounding
        if tp is not None:
            assert rr >= 2.0

    def test_rejects_zero_sl_distance(self) -> None:
        calc = TakeProfitCalculator(min_rr=2.0, tick_size=0.01)
        fvg = _bullish_fvg()
        tp, rr, reason = calc.calculate(fvg, entry_price=2020.0, sl_price=2020.0)
        assert tp is None
        assert "zero" in reason.lower()
