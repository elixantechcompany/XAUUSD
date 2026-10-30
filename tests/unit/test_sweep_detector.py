"""
Unit tests for LiquiditySweepDetector in src/strategy/strategy_core.py

Covers R15, R16, R17, R18.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.strategy.strategy_core import (
    FVG, Swing, LiquiditySweepDetector, _fvg_id,
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


def _bullish_fvg(c3_hour: int = 3) -> FVG:
    return FVG(
        id=_fvg_id("XAUUSD", "BULLISH", _t(1)),
        symbol="XAUUSD", timeframe="H1",
        direction="BULLISH",
        fvg_low=2010.0, fvg_high=2015.0,
        c1_time=_t(1), c3_time=_t(c3_hour),
        c1_high=2010.0, c1_low=2005.0,
        c3_high=2022.0, c3_low=2015.0,
        atr_at_detection=4.0,
        created_at=_t(c3_hour),
    )


def _bearish_fvg(c3_hour: int = 3) -> FVG:
    return FVG(
        id=_fvg_id("XAUUSD", "BEARISH", _t(1)),
        symbol="XAUUSD", timeframe="H1",
        direction="BEARISH",
        fvg_low=2045.0, fvg_high=2050.0,
        c1_time=_t(1), c3_time=_t(c3_hour),
        c1_high=2060.0, c1_low=2050.0,
        c3_high=2045.0, c3_low=2040.0,
        atr_at_detection=4.0,
        created_at=_t(c3_hour),
    )


def _swing_low(level: float, confirmed_hour: int) -> Swing:
    pivot = _c(confirmed_hour - 2, level, level + 5)
    return Swing(
        candle=pivot,
        level=level,
        direction="LOW",
        confirmed_at=_t(confirmed_hour),
    )


def _swing_high(level: float, confirmed_hour: int) -> Swing:
    pivot = _c(confirmed_hour - 2, level - 5, level)
    return Swing(
        candle=pivot,
        level=level,
        direction="HIGH",
        confirmed_at=_t(confirmed_hour),
    )


class TestBullishSweep:
    """R15: bullish sweep — wick below swing low + close back above."""

    def test_valid_bullish_sweep_detected(self) -> None:
        fvg = _bullish_fvg(c3_hour=3)
        swing = _swing_low(level=2005.0, confirmed_hour=2)
        # Sweep candle: hour 4 (after FVG c3_time=3), wick below 2005, close above 2005
        sweep_candle = _c(4, lo=2003.0, hi=2010.0, c=2007.0)
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [sweep_candle], [swing])
        assert len(sweeps) == 1
        assert sweeps[0].direction == "BULLISH"
        assert sweeps[0].swept_level == pytest.approx(2005.0)
        assert sweeps[0].sweep_extreme == pytest.approx(2003.0)

    def test_no_sweep_when_close_stays_below_swing_level(self) -> None:
        """R15: close-back required. Wick below but close below → not a sweep."""
        fvg = _bullish_fvg(c3_hour=3)
        swing = _swing_low(level=2005.0, confirmed_hour=2)
        candle = _c(4, lo=2003.0, hi=2010.0, c=2004.0)  # close=2004 < 2005
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0

    def test_no_sweep_when_close_exactly_at_swing_level(self) -> None:
        """R15: strict inequality — close must be strictly above."""
        fvg = _bullish_fvg(c3_hour=3)
        swing = _swing_low(level=2005.0, confirmed_hour=2)
        candle = _c(4, lo=2003.0, hi=2010.0, c=2005.0)  # close == level
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0

    def test_no_sweep_when_no_wick_below(self) -> None:
        """R15: candle must wick below the swing level."""
        fvg = _bullish_fvg(c3_hour=3)
        swing = _swing_low(level=2005.0, confirmed_hour=2)
        candle = _c(4, lo=2006.0, hi=2010.0, c=2008.0)  # low > swing level
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0


class TestBearishSweep:
    """R16: bearish sweep — wick above swing high + close back below."""

    def test_valid_bearish_sweep_detected(self) -> None:
        fvg = _bearish_fvg(c3_hour=3)
        swing = _swing_high(level=2055.0, confirmed_hour=2)
        sweep_candle = _c(4, lo=2048.0, hi=2058.0, c=2052.0)  # wick above 2055, close below
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [sweep_candle], [swing])
        assert len(sweeps) == 1
        assert sweeps[0].direction == "BEARISH"
        assert sweeps[0].sweep_extreme == pytest.approx(2058.0)

    def test_no_sweep_when_close_stays_above_swing_level(self) -> None:
        fvg = _bearish_fvg(c3_hour=3)
        swing = _swing_high(level=2055.0, confirmed_hour=2)
        candle = _c(4, lo=2048.0, hi=2058.0, c=2056.0)  # close above swing level
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0

    def test_no_sweep_when_close_exactly_at_swing_level(self) -> None:
        fvg = _bearish_fvg(c3_hour=3)
        swing = _swing_high(level=2055.0, confirmed_hour=2)
        candle = _c(4, lo=2048.0, hi=2058.0, c=2055.0)  # close == level
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0


class TestSweepOrdering:
    """R17: sweep candle must open AFTER FVG c3_time."""

    def test_sweep_before_fvg_not_associated(self) -> None:
        fvg = _bullish_fvg(c3_hour=5)   # FVG confirmed at hour 5
        swing = _swing_low(level=2005.0, confirmed_hour=2)
        # Sweep candle at hour 4 — before FVG c3_time
        candle = _c(4, lo=2003.0, hi=2010.0, c=2007.0)
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0

    def test_sweep_at_same_time_as_fvg_not_associated(self) -> None:
        fvg = _bullish_fvg(c3_hour=4)
        swing = _swing_low(level=2005.0, confirmed_hour=2)
        candle = _c(4, lo=2003.0, hi=2010.0, c=2007.0)  # time == c3_time
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0

    def test_sweep_after_fvg_is_associated(self) -> None:
        fvg = _bullish_fvg(c3_hour=3)
        swing = _swing_low(level=2005.0, confirmed_hour=2)
        candle = _c(4, lo=2003.0, hi=2010.0, c=2007.0)  # time > c3_time
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 1

    def test_swing_confirmed_after_candle_not_eligible(self) -> None:
        """R14: swing confirmed_at must be before sweep candle time."""
        fvg = _bullish_fvg(c3_hour=3)
        # swing confirmed at hour 5, but sweep candle is at hour 4
        swing = _swing_low(level=2005.0, confirmed_hour=5)
        candle = _c(4, lo=2003.0, hi=2010.0, c=2007.0)
        det = LiquiditySweepDetector()
        sweeps = det.find_sweeps_for_fvg(fvg, [candle], [swing])
        assert len(sweeps) == 0
