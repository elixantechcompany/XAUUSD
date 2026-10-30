"""
Unit tests for ReferenceCandleSelector, GapExitChecker, and EntryTriggerChecker.

Covers R21–R31.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.strategy.strategy_core import (
    FVG, ReferenceCandle, ReferenceCandleSelector,
    GapExitChecker, EntryTriggerChecker, _fvg_id,
)

BASE = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(
    h: int, lo: float, hi: float,
    o: float | None = None, c: float | None = None,
) -> Candle:
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


# ─────────────────────────────────────────────────────────────────────────────
# ReferenceCandleSelector (R21, R22, R25)
# ─────────────────────────────────────────────────────────────────────────────

class TestBullishReferenceCandle:
    """R21: bullish — most recent candle intersecting FVG with low <= fvg_high."""

    def test_selects_most_recent_qualifying_candle(self) -> None:
        fvg = _bullish_fvg()  # fvg_low=2010, fvg_high=2015
        # Three candles that all qualify; most recent should be selected
        c1 = _c(3, lo=2012.0, hi=2018.0)   # intersects; low=2012 < fvg_high=2015
        c2 = _c(4, lo=2011.0, hi=2016.0)   # intersects; low=2011 < fvg_high=2015
        c3 = _c(5, lo=2013.0, hi=2017.0)   # intersects; low=2013 < fvg_high=2015
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [c1, c2, c3])
        assert ref is not None
        assert ref.candle.time == _t(5)   # most recent

    def test_candle_fully_above_fvg_not_selected(self) -> None:
        """R21: candle that doesn't intersect FVG is excluded."""
        fvg = _bullish_fvg()
        # Candle range entirely above fvg_high=2015
        c = _c(3, lo=2016.0, hi=2020.0)
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [c])
        assert ref is None

    def test_candle_fully_below_fvg_not_selected(self) -> None:
        """R21: candle below fvg_low doesn't intersect."""
        fvg = _bullish_fvg()
        c = _c(3, lo=2005.0, hi=2009.0)   # high=2009 < fvg_low=2010
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [c])
        assert ref is None

    def test_returns_none_when_no_qualifying_candle(self) -> None:
        """R25: setup rejected when no qualifying candle."""
        fvg = _bullish_fvg()
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [])
        assert ref is None


class TestBearishReferenceCandle:
    """R22: bearish — most recent candle with high >= fvg_low."""

    def test_selects_most_recent_qualifying_candle(self) -> None:
        fvg = _bearish_fvg()  # fvg_low=2045, fvg_high=2050
        c1 = _c(3, lo=2043.0, hi=2047.0)  # intersects; high=2047 >= fvg_low=2045
        c2 = _c(4, lo=2044.0, hi=2048.0)  # intersects; high=2048 >= fvg_low=2045
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [c1, c2])
        assert ref is not None
        assert ref.candle.time == _t(4)

    def test_candle_fully_below_fvg_not_selected(self) -> None:
        fvg = _bearish_fvg()
        c = _c(3, lo=2040.0, hi=2044.0)  # high=2044 < fvg_low=2045
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [c])
        assert ref is None


# ─────────────────────────────────────────────────────────────────────────────
# Freeze (R23, R24)
# ─────────────────────────────────────────────────────────────────────────────

class TestFreeze:
    def test_freeze_produces_frozen_copy(self) -> None:
        """R24: frozen() returns a frozen ReferenceCandle."""
        fvg = _bullish_fvg()
        candle = _c(3, lo=2012.0, hi=2018.0)
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [candle])
        assert ref is not None
        assert ref.frozen is False
        frozen = ref.freeze()
        assert frozen.frozen is True
        assert frozen.candle == ref.candle

    def test_trigger_high_correct(self) -> None:
        fvg = _bullish_fvg()
        candle = _c(3, lo=2012.0, hi=2018.0)
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [candle])
        assert ref.trigger_high == pytest.approx(2018.0)

    def test_trigger_low_correct(self) -> None:
        fvg = _bearish_fvg()
        candle = _c(3, lo=2043.0, hi=2047.0)
        ref = ReferenceCandleSelector.find_reference_candle(fvg, [candle])
        assert ref.trigger_low == pytest.approx(2043.0)


# ─────────────────────────────────────────────────────────────────────────────
# GapExitChecker (R26)
# ─────────────────────────────────────────────────────────────────────────────

class TestGapExitChecker:
    def test_bullish_gap_exit_on_close_above_fvg_high(self) -> None:
        """R26: bullish exit when candle.close > fvg_high."""
        fvg = _bullish_fvg()  # fvg_high=2015
        checker = GapExitChecker(mode="candle_close")
        candle = _c(5, lo=2012.0, hi=2020.0, c=2016.0)  # close=2016 > 2015
        assert checker.is_gap_exited(fvg, candle) is True

    def test_bullish_no_exit_when_close_at_fvg_high(self) -> None:
        """R26: strict inequality — close at boundary is not an exit."""
        fvg = _bullish_fvg()
        checker = GapExitChecker(mode="candle_close")
        candle = _c(5, lo=2012.0, hi=2020.0, c=2015.0)  # close == fvg_high
        assert checker.is_gap_exited(fvg, candle) is False

    def test_bullish_no_exit_when_close_below_fvg_high(self) -> None:
        fvg = _bullish_fvg()
        checker = GapExitChecker(mode="candle_close")
        candle = _c(5, lo=2012.0, hi=2020.0, c=2014.0)
        assert checker.is_gap_exited(fvg, candle) is False

    def test_bearish_gap_exit_on_close_below_fvg_low(self) -> None:
        """R26: bearish exit when candle.close < fvg_low."""
        fvg = _bearish_fvg()  # fvg_low=2045
        checker = GapExitChecker(mode="candle_close")
        candle = _c(5, lo=2042.0, hi=2048.0, c=2044.0)  # close=2044 < 2045
        assert checker.is_gap_exited(fvg, candle) is True

    def test_bearish_no_exit_at_boundary(self) -> None:
        fvg = _bearish_fvg()
        checker = GapExitChecker(mode="candle_close")
        candle = _c(5, lo=2042.0, hi=2048.0, c=2045.0)  # close == fvg_low
        assert checker.is_gap_exited(fvg, candle) is False

    def test_raises_on_unsupported_mode(self) -> None:
        with pytest.raises(NotImplementedError):
            GapExitChecker(mode="tick_break")


# ─────────────────────────────────────────────────────────────────────────────
# EntryTriggerChecker — CANDLE_CLOSE mode (R29)
# ─────────────────────────────────────────────────────────────────────────────

class TestCandleCloseTrigger:
    def _frozen_ref(self, hi: float, lo: float) -> ReferenceCandle:
        c = _c(3, lo=lo, hi=hi)
        return ReferenceCandle(candle=c, frozen=True)

    def test_bullish_trigger_on_close_above_trigger(self) -> None:
        """R29: bullish close > ref.trigger_high."""
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        candle = _c(6, lo=2017.0, hi=2022.0, c=2021.0)  # close=2021 > trigger=2018
        assert EntryTriggerChecker.check_candle_close(fvg, ref, candle) is True

    def test_bullish_no_trigger_at_trigger_level(self) -> None:
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        candle = _c(6, lo=2017.0, hi=2022.0, c=2018.0)  # close == trigger
        assert EntryTriggerChecker.check_candle_close(fvg, ref, candle) is False

    def test_bullish_no_trigger_below_trigger_level(self) -> None:
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        candle = _c(6, lo=2014.0, hi=2017.0, c=2017.0)  # close < trigger
        assert EntryTriggerChecker.check_candle_close(fvg, ref, candle) is False

    def test_bearish_trigger_on_close_below_trigger(self) -> None:
        fvg = _bearish_fvg()
        ref = self._frozen_ref(hi=2048.0, lo=2043.0)
        candle = _c(6, lo=2040.0, hi=2045.0, c=2041.0)  # close=2041 < trigger=2043
        assert EntryTriggerChecker.check_candle_close(fvg, ref, candle) is True

    def test_bearish_no_trigger_at_trigger_level(self) -> None:
        fvg = _bearish_fvg()
        ref = self._frozen_ref(hi=2048.0, lo=2043.0)
        candle = _c(6, lo=2040.0, hi=2045.0, c=2043.0)
        assert EntryTriggerChecker.check_candle_close(fvg, ref, candle) is False

    def test_raises_when_reference_not_frozen(self) -> None:
        """R24: must raise if ref not frozen."""
        fvg = _bullish_fvg()
        ref = ReferenceCandle(candle=_c(3, lo=2012.0, hi=2018.0), frozen=False)
        candle = _c(6, lo=2017.0, hi=2022.0, c=2021.0)
        with pytest.raises(ValueError, match="frozen"):
            EntryTriggerChecker.check_candle_close(fvg, ref, candle)


# ─────────────────────────────────────────────────────────────────────────────
# EntryTriggerChecker — TICK_BREAK mode (R30, R31)
# ─────────────────────────────────────────────────────────────────────────────

class TestTickBreakTrigger:
    def _frozen_ref(self, hi: float, lo: float) -> ReferenceCandle:
        c = _c(3, lo=lo, hi=hi)
        return ReferenceCandle(candle=c, frozen=True)

    def _now(self) -> datetime:
        return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def _tick_time(self, seconds_ago: float = 1.0) -> datetime:
        return self._now() - timedelta(seconds=seconds_ago)

    def test_bullish_tick_trigger_fires_on_ask_above_trigger(self) -> None:
        """R30: ask > trigger_high triggers bullish entry."""
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        fired, reason = EntryTriggerChecker.check_tick_break(
            fvg, ref, bid=2018.5, ask=2019.0,
            tick_time=self._tick_time(1), now=self._now(),
        )
        assert fired is True
        assert reason == ""

    def test_bullish_no_trigger_when_ask_at_trigger(self) -> None:
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        fired, _ = EntryTriggerChecker.check_tick_break(
            fvg, ref, bid=2017.5, ask=2018.0,
            tick_time=self._tick_time(1), now=self._now(),
        )
        assert fired is False

    def test_bearish_tick_trigger_fires_on_bid_below_trigger(self) -> None:
        """R30: bid < trigger_low triggers bearish entry."""
        fvg = _bearish_fvg()
        ref = self._frozen_ref(hi=2048.0, lo=2043.0)
        fired, reason = EntryTriggerChecker.check_tick_break(
            fvg, ref, bid=2042.0, ask=2042.5,
            tick_time=self._tick_time(1), now=self._now(),
        )
        assert fired is True

    def test_stale_tick_rejected(self) -> None:
        """R31: tick older than max_tick_age_seconds is rejected."""
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        fired, reason = EntryTriggerChecker.check_tick_break(
            fvg, ref, bid=2018.5, ask=2019.0,
            tick_time=self._tick_time(10),  # 10 seconds old > default 5
            now=self._now(),
            max_tick_age_seconds=5,
        )
        assert fired is False
        assert "stale" in reason.lower()

    def test_zero_bid_rejected(self) -> None:
        """R31: zero bid is invalid."""
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        fired, reason = EntryTriggerChecker.check_tick_break(
            fvg, ref, bid=0.0, ask=2019.0,
            tick_time=self._tick_time(1), now=self._now(),
        )
        assert fired is False

    def test_inverted_spread_rejected(self) -> None:
        """R31: ask <= bid is invalid."""
        fvg = _bullish_fvg()
        ref = self._frozen_ref(hi=2018.0, lo=2012.0)
        fired, reason = EntryTriggerChecker.check_tick_break(
            fvg, ref, bid=2019.0, ask=2018.0,  # inverted
            tick_time=self._tick_time(1), now=self._now(),
        )
        assert fired is False
        assert "inverted" in reason.lower()

    def test_raises_when_reference_not_frozen(self) -> None:
        fvg = _bullish_fvg()
        ref = ReferenceCandle(candle=_c(3, lo=2012.0, hi=2018.0), frozen=False)
        with pytest.raises(ValueError, match="frozen"):
            EntryTriggerChecker.check_tick_break(
                fvg, ref, bid=2018.5, ask=2019.0,
                tick_time=self._tick_time(1), now=self._now(),
            )
