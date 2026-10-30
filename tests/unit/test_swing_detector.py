"""
Unit tests for SwingDetector in src/strategy/strategy_core.py

Covers R12, R13, R14.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.strategy.strategy_core import SwingDetector

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


class TestSwingDetectorInitialization:
    def test_raises_on_zero_left_bars(self) -> None:
        with pytest.raises(ValueError):
            SwingDetector(left_bars=0, right_bars=2)

    def test_raises_on_zero_right_bars(self) -> None:
        with pytest.raises(ValueError):
            SwingDetector(left_bars=2, right_bars=0)


class TestSwingHighDetection:
    """R12: swing high = strictly higher than 2 candles each side."""

    def _standard_high_candles(self) -> list[Candle]:
        """
        Positions: 0,1 | PIVOT(2) | 3,4
        Pivot high = 105, surroundings = 100.
        left_bars=2, right_bars=2 → confirmed_at = candle[4].time
        """
        return [
            _c(0, 98, 100),
            _c(1, 98, 100),
            _c(2, 100, 105),   # pivot high
            _c(3, 98, 100),
            _c(4, 98, 100),
        ]

    def test_swing_high_detected(self) -> None:
        det = SwingDetector(left_bars=2, right_bars=2)
        swings = det.find_swings(self._standard_high_candles())
        highs = [s for s in swings if s.direction == "HIGH"]
        assert len(highs) == 1
        assert highs[0].level == pytest.approx(105.0)

    def test_confirmed_at_correct_candle(self) -> None:
        """R14: confirmed_at = open time of pivot_index + right_bars."""
        det = SwingDetector(left_bars=2, right_bars=2)
        candles = self._standard_high_candles()
        swings = det.find_swings(candles)
        highs = [s for s in swings if s.direction == "HIGH"]
        assert highs[0].confirmed_at == _t(4)

    def test_no_swing_high_with_insufficient_candles(self) -> None:
        """R14: need at least left+1+right candles."""
        det = SwingDetector(left_bars=2, right_bars=2)
        candles = self._standard_high_candles()[:4]  # missing right bar
        highs = [s for s in det.find_swings(candles) if s.direction == "HIGH"]
        assert len(highs) == 0


class TestSwingLowDetection:
    """R12: swing low = strictly lower than 2 candles each side."""

    def _standard_low_candles(self) -> list[Candle]:
        return [
            _c(0, 100, 102),
            _c(1, 100, 102),
            _c(2, 95, 102),    # pivot low
            _c(3, 100, 102),
            _c(4, 100, 102),
        ]

    def test_swing_low_detected(self) -> None:
        det = SwingDetector(left_bars=2, right_bars=2)
        swings = det.find_swings(self._standard_low_candles())
        lows = [s for s in swings if s.direction == "LOW"]
        assert len(lows) == 1
        assert lows[0].level == pytest.approx(95.0)

    def test_confirmed_at_correct_candle(self) -> None:
        det = SwingDetector(left_bars=2, right_bars=2)
        candles = self._standard_low_candles()
        lows = [s for s in det.find_swings(candles) if s.direction == "LOW"]
        assert lows[0].confirmed_at == _t(4)


class TestTieHandling:
    """R13: ties (equal values) do NOT produce a pivot."""

    def test_equal_high_on_left_no_swing_high(self) -> None:
        candles = [
            _c(0, 98, 105),    # same high as pivot
            _c(1, 98, 100),
            _c(2, 100, 105),   # "pivot" — but candle[0] ties it
            _c(3, 98, 100),
            _c(4, 98, 100),
        ]
        det = SwingDetector(left_bars=2, right_bars=2)
        highs = [s for s in det.find_swings(candles) if s.direction == "HIGH"]
        assert len(highs) == 0

    def test_equal_high_on_right_no_swing_high(self) -> None:
        candles = [
            _c(0, 98, 100),
            _c(1, 98, 100),
            _c(2, 100, 105),   # "pivot"
            _c(3, 98, 100),
            _c(4, 98, 105),    # same high as pivot
        ]
        det = SwingDetector(left_bars=2, right_bars=2)
        highs = [s for s in det.find_swings(candles) if s.direction == "HIGH"]
        assert len(highs) == 0

    def test_equal_low_no_swing_low(self) -> None:
        candles = [
            _c(0, 95, 102),    # same low as "pivot"
            _c(1, 100, 102),
            _c(2, 95, 102),    # "pivot"
            _c(3, 100, 102),
            _c(4, 100, 102),
        ]
        det = SwingDetector(left_bars=2, right_bars=2)
        lows = [s for s in det.find_swings(candles) if s.direction == "LOW"]
        assert len(lows) == 0


class TestLookAheadBias:
    """R14: pivot at index i requires candles[i+right_bars] to exist."""

    def test_pivot_absent_when_right_bars_not_yet_closed(self) -> None:
        """
        5 candles, pivot at index 2.
        With right_bars=2, index 4 is the last right candle.
        Remove it → pivot should not appear.
        """
        full = [
            _c(0, 98, 100),
            _c(1, 98, 100),
            _c(2, 100, 105),
            _c(3, 98, 100),
            _c(4, 98, 100),
        ]
        det = SwingDetector(left_bars=2, right_bars=2)
        # Full list → pivot detected
        assert len([s for s in det.find_swings(full) if s.direction == "HIGH"]) == 1
        # Without last right bar → no pivot
        partial = full[:4]
        assert len([s for s in det.find_swings(partial) if s.direction == "HIGH"]) == 0
