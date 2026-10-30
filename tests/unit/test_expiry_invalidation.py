"""
Unit tests for SetupExpiryChecker.

Covers R64, R65, R66, R67, R68, R69.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.strategy.strategy_core import (
    FVG, Swing, LiquiditySweep, SetupExpiryChecker, _fvg_id,
)

BASE = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(h: int, lo: float, hi: float, c: float | None = None) -> Candle:
    if c is None:
        c = (lo + hi) / 2
    return Candle(
        time=_t(h), open=(lo + hi) / 2, high=hi, low=lo, close=c,
        volume=100.0, symbol="XAUUSD", timeframe="H1",
    )


def _bullish_fvg(c3_hour: int = 2) -> FVG:
    return FVG(
        id=_fvg_id("XAUUSD", "BULLISH", _t(0)),
        symbol="XAUUSD", timeframe="H1",
        direction="BULLISH",
        fvg_low=2010.0, fvg_high=2015.0,
        c1_time=_t(0), c3_time=_t(c3_hour),
        c1_high=2010.0, c1_low=2005.0,
        c3_high=2022.0, c3_low=2015.0,
        atr_at_detection=4.0, created_at=_t(c3_hour),
    )


def _bearish_fvg(c3_hour: int = 2) -> FVG:
    return FVG(
        id=_fvg_id("XAUUSD", "BEARISH", _t(0)),
        symbol="XAUUSD", timeframe="H1",
        direction="BEARISH",
        fvg_low=2045.0, fvg_high=2050.0,
        c1_time=_t(0), c3_time=_t(c3_hour),
        c1_high=2060.0, c1_low=2050.0,
        c3_high=2045.0, c3_low=2040.0,
        atr_at_detection=4.0, created_at=_t(c3_hour),
    )


def _sweep(direction: str = "BULLISH", sweep_hour: int = 5,
           extreme: float = 2000.0) -> LiquiditySweep:
    pivot = _c(sweep_hour - 1, extreme, extreme + 5)
    swing = Swing(candle=pivot, level=extreme + 1, direction="LOW",
                  confirmed_at=_t(sweep_hour - 1))
    sc = _c(sweep_hour, lo=extreme, hi=extreme + 10)
    return LiquiditySweep(
        swing=swing, sweep_candle=sc,
        direction=direction, swept_level=extreme + 1,
        sweep_extreme=extreme,
    )


class TestFVGAgeExpiry:
    """R65: FVG expires after max_fvg_age_bars completed bars since C3."""

    def _candles_after_c3(self, n: int) -> list[Candle]:
        return [_c(3 + i, lo=2020.0, hi=2024.0) for i in range(n)]

    def test_fvg_not_expired_at_23_bars(self) -> None:
        checker = SetupExpiryChecker(max_fvg_age_bars=24, max_setup_age_bars_after_sweep=12)
        fvg = _bullish_fvg(c3_hour=2)
        candles = self._candles_after_c3(23)
        expired, _ = checker.check_expiry(fvg, None, candles)
        assert not expired

    def test_fvg_expired_at_24_bars(self) -> None:
        checker = SetupExpiryChecker(max_fvg_age_bars=24, max_setup_age_bars_after_sweep=12)
        fvg = _bullish_fvg(c3_hour=2)
        candles = self._candles_after_c3(24)
        expired, reason = checker.check_expiry(fvg, None, candles)
        assert expired
        assert "age" in reason.lower()


class TestPostSweepExpiry:
    """R64: setup expires if not triggered within max bars after sweep."""

    def test_expires_at_12_bars_after_sweep(self) -> None:
        checker = SetupExpiryChecker(max_fvg_age_bars=24, max_setup_age_bars_after_sweep=12)
        fvg = _bullish_fvg(c3_hour=2)
        sweep = _sweep(sweep_hour=5)
        # 12 candles after sweep (hours 6–17)
        candles = [_c(6 + i, lo=2020.0, hi=2024.0) for i in range(12)]
        expired, reason = checker.check_expiry(fvg, sweep, candles)
        assert expired
        assert "sweep" in reason.lower()

    def test_valid_at_11_bars_after_sweep(self) -> None:
        checker = SetupExpiryChecker(max_fvg_age_bars=24, max_setup_age_bars_after_sweep=12)
        fvg = _bullish_fvg(c3_hour=2)
        sweep = _sweep(sweep_hour=5)
        candles = [_c(6 + i, lo=2020.0, hi=2024.0) for i in range(11)]
        expired, _ = checker.check_expiry(fvg, sweep, candles)
        assert not expired


class TestBullishInvalidation:
    """R66, R67: bullish setup invalidated on close below sweep extreme."""

    def test_close_below_sweep_low_invalidates(self) -> None:
        checker = SetupExpiryChecker()
        fvg = _bullish_fvg()
        sweep = _sweep("BULLISH", sweep_hour=5, extreme=2000.0)
        # Candle closes below sweep_extreme=2000
        candle = _c(10, lo=1995.0, hi=2005.0, c=1998.0)
        invalid, reason = checker.check_invalidation(fvg, sweep, candle)
        assert invalid
        assert "invalidated" in reason.lower()

    def test_wick_below_sweep_low_does_not_invalidate(self) -> None:
        """R67: only close triggers — wick alone does not."""
        checker = SetupExpiryChecker()
        fvg = _bullish_fvg()
        sweep = _sweep("BULLISH", sweep_hour=5, extreme=2000.0)
        # Wick below 2000 but close above (inside FVG [2010, 2015])
        candle = _c(10, lo=1995.0, hi=2014.0, c=2012.0)
        invalid, _ = checker.check_invalidation(fvg, sweep, candle)
        assert not invalid

    def test_fvg_fully_traversed_invalidates(self) -> None:
        """R11: close below fvg_low also invalidates."""
        checker = SetupExpiryChecker()
        fvg = _bullish_fvg()   # fvg_low=2010
        candle = _c(10, lo=2005.0, hi=2012.0, c=2009.0)  # close < fvg_low
        invalid, reason = checker.check_invalidation(fvg, None, candle)
        assert invalid


class TestBearishInvalidation:
    """R66, R68: bearish setup invalidated on close above sweep extreme."""

    def test_close_above_sweep_high_invalidates(self) -> None:
        checker = SetupExpiryChecker()
        fvg = _bearish_fvg()
        sweep = _sweep("BEARISH", sweep_hour=5, extreme=2060.0)
        candle = _c(10, lo=2055.0, hi=2065.0, c=2062.0)  # close > 2060
        invalid, reason = checker.check_invalidation(fvg, sweep, candle)
        assert invalid

    def test_wick_above_sweep_high_does_not_invalidate(self) -> None:
        checker = SetupExpiryChecker()
        fvg = _bearish_fvg()
        sweep = _sweep("BEARISH", sweep_hour=5, extreme=2060.0)
        # wick above 2060 but close below (inside FVG [2045, 2050])
        candle = _c(10, lo=2046.0, hi=2063.0, c=2048.0)  # wick above but close below
        invalid, _ = checker.check_invalidation(fvg, sweep, candle)
        assert not invalid
