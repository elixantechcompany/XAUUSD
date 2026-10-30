"""
Unit tests for FVGDetector in src/strategy/strategy_core.py

Covers R5, R6, R7, R8, R9, R10, R11.
All tests use synthetic data. No MT5 connection required.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.strategy.strategy_core import FVGDetector, FVG


BASE_TIME = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(hours: int) -> datetime:
    return BASE_TIME + timedelta(hours=hours)


def _c(h: int, o: float, hi: float, lo: float, c: float) -> Candle:
    return Candle(
        time=_t(h), open=o, high=hi, low=lo, close=c,
        volume=100.0, symbol="XAUUSD", timeframe="H1",
    )


def _make_detector(
    min_fvg_atr_factor: float = 0.0,  # 0 = disable ATR filter for most tests
    min_fvg_ticks: int = 0,           # 0 = disable tick filter for most tests
    tick_size: float = 0.01,
) -> FVGDetector:
    return FVGDetector(
        symbol="XAUUSD",
        timeframe="H1",
        atr_period=14,
        min_fvg_atr_factor=min_fvg_atr_factor,
        min_fvg_ticks=min_fvg_ticks,
        tick_size=tick_size,
    )


# ── R2: timeframe enforcement ─────────────────────────────────────────────────

class TestTimeframeEnforcement:
    def test_raises_on_wrong_timeframe(self) -> None:
        with pytest.raises(ValueError, match="H1"):
            FVGDetector(symbol="XAUUSD", timeframe="M15")


# ── R5: bullish FVG ───────────────────────────────────────────────────────────

class TestBullishFVG:
    def _bullish_candles(self) -> list[Candle]:
        """
        Classic bullish FVG:
          C1: high=2010.0
          C2: big up candle
          C3: low=2015.0  → gap = [2010, 2015]
        Plus 14 prior candles so ATR can be computed.
        """
        prior = [_c(i, 2000, 2002, 1998, 2001) for i in range(14)]
        c1 = _c(14, 2008, 2010, 2005, 2009)
        c2 = _c(15, 2011, 2020, 2010, 2018)
        c3 = _c(16, 2016, 2022, 2015, 2021)
        return prior + [c1, c2, c3]

    def test_bullish_fvg_detected(self) -> None:
        candles = self._bullish_candles()
        det = _make_detector()
        fvgs = det.find_all_fvgs(candles)
        bullish = [f for f in fvgs if f.direction == "BULLISH"]
        assert len(bullish) >= 1

    def test_bullish_fvg_boundaries(self) -> None:
        candles = self._bullish_candles()
        det = _make_detector()
        fvgs = det.find_all_fvgs(candles)
        bullish = [f for f in fvgs if f.direction == "BULLISH"][-1]
        # R5: fvg_low = C1.high, fvg_high = C3.low
        assert bullish.fvg_low == pytest.approx(2010.0)
        assert bullish.fvg_high == pytest.approx(2015.0)
        assert bullish.direction == "BULLISH"

    def test_no_fvg_when_c1_high_equals_c3_low(self) -> None:
        """R5: strict < required. Equal values → no FVG."""
        prior = [_c(i, 2000, 2002, 1998, 2001) for i in range(14)]
        c1 = _c(14, 2008, 2010, 2005, 2009)
        c2 = _c(15, 2011, 2020, 2010, 2018)
        c3 = _c(16, 2010, 2022, 2010, 2021)   # C3.low == C1.high
        det = _make_detector()
        fvgs = det.find_all_fvgs(prior + [c1, c2, c3])
        target_fvg = [f for f in fvgs if f.c1_time == c1.time]
        assert len(target_fvg) == 0


# ── R6: bearish FVG ───────────────────────────────────────────────────────────

class TestBearishFVG:
    def _bearish_candles(self) -> list[Candle]:
        """
        Bearish FVG:
          C1: low=2050.0
          C2: big down candle
          C3: high=2045.0  → gap = [2045, 2050]
        """
        prior = [_c(i, 2060, 2062, 2058, 2061) for i in range(14)]
        c1 = _c(14, 2055, 2060, 2050, 2051)
        c2 = _c(15, 2048, 2050, 2040, 2041)
        c3 = _c(16, 2043, 2045, 2040, 2041)
        return prior + [c1, c2, c3]

    def test_bearish_fvg_detected(self) -> None:
        candles = self._bearish_candles()
        det = _make_detector()
        fvgs = det.find_all_fvgs(candles)
        bearish = [f for f in fvgs if f.direction == "BEARISH"]
        assert len(bearish) >= 1

    def test_bearish_fvg_boundaries(self) -> None:
        candles = self._bearish_candles()
        det = _make_detector()
        fvgs = det.find_all_fvgs(candles)
        bearish = [f for f in fvgs if f.direction == "BEARISH"][-1]
        # R6: fvg_high = C1.low, fvg_low = C3.high
        assert bearish.fvg_high == pytest.approx(2050.0)
        assert bearish.fvg_low == pytest.approx(2045.0)
        assert bearish.direction == "BEARISH"

    def test_no_fvg_when_c1_low_equals_c3_high(self) -> None:
        prior = [_c(i, 2060, 2062, 2058, 2061) for i in range(14)]
        c1 = _c(14, 2055, 2060, 2050, 2051)
        c2 = _c(15, 2048, 2050, 2040, 2041)
        c3 = _c(16, 2043, 2050, 2040, 2041)   # C3.high == C1.low
        det = _make_detector()
        fvgs = det.find_all_fvgs(prior + [c1, c2, c3])
        target_fvg = [f for f in fvgs if f.c1_time == c1.time]
        assert len(target_fvg) == 0


# ── R7: confirmation timing ───────────────────────────────────────────────────

class TestConfirmationTiming:
    def test_fewer_than_3_candles_returns_empty(self) -> None:
        det = _make_detector()
        c1 = _c(0, 2008, 2010, 2005, 2009)
        c2 = _c(1, 2011, 2020, 2010, 2018)
        assert det.find_all_fvgs([c1, c2]) == []
        assert det.find_all_fvgs([c1]) == []
        assert det.find_all_fvgs([]) == []


# ── R8: minimum size filter ───────────────────────────────────────────────────

class TestMinimumSizeFilter:
    def _candles_with_tiny_fvg(self) -> list[Candle]:
        """FVG gap = 0.01 (1 tick) — extremely small."""
        prior = [_c(i, 2000, 2002, 1998, 2001) for i in range(14)]
        c1 = _c(14, 2010, 2010.00, 2008, 2009)
        c2 = _c(15, 2010.01, 2012, 2010, 2011)
        c3 = _c(16, 2010.02, 2012, 2010.01, 2011)  # C3.low = 2010.01, gap = 0.01
        return prior + [c1, c2, c3]

    def test_fvg_rejected_when_below_threshold(self) -> None:
        candles = self._candles_with_tiny_fvg()
        # With ATR factor of 0.1 and ATR ~4.0, min_size ≈ 0.4 — gap 0.01 is rejected
        det = FVGDetector(
            symbol="XAUUSD", timeframe="H1",
            atr_period=14, min_fvg_atr_factor=0.1, min_fvg_ticks=2,
            tick_size=0.01,
        )
        fvgs = det.find_all_fvgs(candles)
        c1 = candles[14]
        target_fvg = [f for f in fvgs if f.c1_time == c1.time]
        assert len(target_fvg) == 0

    def test_fvg_rejected_when_atr_unavailable(self) -> None:
        """R8: reject when fewer than atr_period+1 candles available."""
        c1 = _c(0, 2008, 2010, 2005, 2009)
        c2 = _c(1, 2011, 2020, 2010, 2018)
        c3 = _c(2, 2016, 2022, 2015, 2021)
        det = FVGDetector(
            symbol="XAUUSD", timeframe="H1",
            atr_period=14, min_fvg_atr_factor=0.1, min_fvg_ticks=0,
            tick_size=0.01,
        )
        # Only 3 candles — ATR(14) needs 15. FVG rejected.
        fvgs = det.find_all_fvgs([c1, c2, c3])
        assert len(fvgs) == 0

    def test_min_size_uses_greater_of_atr_and_ticks(self) -> None:
        """R8: result = max(atr_factor × ATR, min_ticks × tick_size)."""
        prior = [_c(i, 2000, 2002, 1998, 2001) for i in range(14)]
        # Gap size = 5.0; ATR ≈ 4.0; atr_factor=0.1 → ATR min = 0.4
        # tick min = 2 × 0.01 = 0.02. Gap 5.0 > both → accepted
        c1 = _c(14, 2010, 2010.0, 2008, 2009)
        c2 = _c(15, 2012, 2020, 2011, 2018)
        c3 = _c(16, 2016, 2022, 2015.0, 2021)
        det = FVGDetector(
            symbol="XAUUSD", timeframe="H1",
            atr_period=14, min_fvg_atr_factor=0.1, min_fvg_ticks=2,
            tick_size=0.01,
        )
        fvgs = det.find_all_fvgs(prior + [c1, c2, c3])
        assert len(fvgs) >= 1


# ── R9: age expiry ────────────────────────────────────────────────────────────

class TestFVGAgeExpiry:
    def _make_fvg(self) -> FVG:
        from src.strategy.strategy_core import _fvg_id
        return FVG(
            id=_fvg_id("XAUUSD", "BULLISH", _t(14)),
            symbol="XAUUSD",
            timeframe="H1",
            direction="BULLISH",
            fvg_low=2010.0,
            fvg_high=2015.0,
            c1_time=_t(14),
            c3_time=_t(16),
            c1_high=2010.0, c1_low=2005.0,
            c3_high=2022.0, c3_low=2015.0,
            atr_at_detection=4.0,
            created_at=_t(16),
        )

    def _candles_after_c3(self, n: int) -> list[Candle]:
        """n completed candles with open time AFTER C3 (_t(16))."""
        return [_c(17 + i, 2020, 2022, 2018, 2021) for i in range(n)]

    def test_fvg_valid_at_23_bars(self) -> None:
        det = _make_detector()
        fvg = self._make_fvg()
        candles = self._candles_after_c3(23)
        assert not det.is_age_expired(fvg, candles, max_age_bars=24)

    def test_fvg_expired_at_24_bars(self) -> None:
        det = _make_detector()
        fvg = self._make_fvg()
        candles = self._candles_after_c3(24)
        assert det.is_age_expired(fvg, candles, max_age_bars=24)


# ── R10: stored fields ────────────────────────────────────────────────────────

class TestStoredFields:
    def test_all_required_fields_present(self) -> None:
        prior = [_c(i, 2000, 2002, 1998, 2001) for i in range(14)]
        c1 = _c(14, 2008, 2010, 2005, 2009)
        c2 = _c(15, 2011, 2020, 2010, 2018)
        c3 = _c(16, 2016, 2022, 2015, 2021)
        det = _make_detector()
        fvgs = det.find_all_fvgs(prior + [c1, c2, c3])
        bullish = [f for f in fvgs if f.direction == "BULLISH"]
        assert bullish, "Expected at least one bullish FVG"
        f = bullish[-1]
        assert f.id
        assert f.symbol == "XAUUSD"
        assert f.timeframe == "H1"
        assert f.direction == "BULLISH"
        assert f.fvg_low > 0
        assert f.fvg_high > f.fvg_low
        assert f.c1_time is not None
        assert f.c3_time is not None
        assert f.atr_at_detection > 0
        assert f.created_at is not None

    def test_id_is_stable(self) -> None:
        """R10: same inputs → same ID across calls."""
        prior = [_c(i, 2000, 2002, 1998, 2001) for i in range(14)]
        c1 = _c(14, 2008, 2010, 2005, 2009)
        c2 = _c(15, 2011, 2020, 2010, 2018)
        c3 = _c(16, 2016, 2022, 2015, 2021)
        det = _make_detector()
        fvgs1 = det.find_all_fvgs(prior + [c1, c2, c3])
        fvgs2 = det.find_all_fvgs(prior + [c1, c2, c3])
        ids1 = {f.id for f in fvgs1}
        ids2 = {f.id for f in fvgs2}
        assert ids1 == ids2


# ── R11: full traversal invalidation ──────────────────────────────────────────

class TestFullTraversalInvalidation:
    def _bullish_fvg(self) -> FVG:
        from src.strategy.strategy_core import _fvg_id
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

    def _bearish_fvg(self) -> FVG:
        from src.strategy.strategy_core import _fvg_id
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

    def test_bullish_fvg_invalidated_when_close_below_fvg_low(self) -> None:
        fvg = self._bullish_fvg()
        candle = _c(3, 2008, 2012, 2005, 2009)  # close=2009 < fvg_low=2010
        assert fvg.is_fully_traversed_by(candle) is True

    def test_bullish_fvg_not_invalidated_on_wick_only(self) -> None:
        fvg = self._bullish_fvg()
        candle = _c(3, 2012, 2014, 2008, 2011)  # wick below fvg_low but close=2011 > 2010
        assert fvg.is_fully_traversed_by(candle) is False

    def test_bearish_fvg_invalidated_when_close_above_fvg_high(self) -> None:
        fvg = self._bearish_fvg()
        candle = _c(3, 2048, 2052, 2046, 2051)  # close=2051 > fvg_high=2050
        assert fvg.is_fully_traversed_by(candle) is True

    def test_bearish_fvg_not_invalidated_on_wick_only(self) -> None:
        fvg = self._bearish_fvg()
        candle = _c(3, 2047, 2052, 2044, 2049)  # wick above fvg_high but close=2049 < 2050
        assert fvg.is_fully_traversed_by(candle) is False
