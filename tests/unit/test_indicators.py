"""
Unit tests for src/data/indicators.py

Tests cover ATR calculation correctness and edge cases.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from src.data.candle import Candle
from src.data.indicators import atr, true_range


def _candle(time_offset_hours: int, o: float, h: float, l: float, c: float) -> Candle:
    t = datetime(2024, 1, 1, time_offset_hours % 24, 0, 0, tzinfo=timezone.utc)
    return Candle(
        time=t, open=o, high=h, low=l, close=c,
        volume=100.0, symbol="XAUUSD", timeframe="H1",
    )


class TestTrueRange:
    def test_simple_range_dominates(self) -> None:
        tr = true_range(prev_close=100.0, high=105.0, low=98.0)
        assert tr == pytest.approx(7.0)

    def test_gap_up_dominates(self) -> None:
        # prev_close=100, high=110, low=108 → TR = max(2, 10, 8) = 10
        tr = true_range(prev_close=100.0, high=110.0, low=108.0)
        assert tr == pytest.approx(10.0)

    def test_gap_down_dominates(self) -> None:
        # prev_close=110, high=102, low=99 → TR = max(3, 8, 11) = 11
        tr = true_range(prev_close=110.0, high=102.0, low=99.0)
        assert tr == pytest.approx(11.0)


class TestATR:
    def _make_candles(self, n: int) -> list[Candle]:
        """Make n candles with range exactly 2.0 each (TR = 2.0 always)."""
        candles = []
        for i in range(n):
            candles.append(_candle(i, o=100.0, h=101.0, l=99.0, c=100.0))
        return candles

    def test_returns_none_when_insufficient_data(self) -> None:
        candles = self._make_candles(14)  # need 15 for period=14
        assert atr(candles, period=14) is None

    def test_returns_value_with_sufficient_data(self) -> None:
        candles = self._make_candles(15)
        result = atr(candles, period=14)
        assert result is not None
        assert result == pytest.approx(2.0)

    def test_exact_period_boundary(self) -> None:
        # Exactly period+1 candles → should compute
        candles = self._make_candles(15)
        assert atr(candles, period=14) is not None

    def test_one_fewer_than_needed(self) -> None:
        candles = self._make_candles(14)
        assert atr(candles, period=14) is None

    def test_raises_on_invalid_period(self) -> None:
        candles = self._make_candles(15)
        with pytest.raises(ValueError):
            atr(candles, period=0)
