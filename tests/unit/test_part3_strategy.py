"""
Unit tests for Part 3 Strategy Alignment:
- MarketConfirmationChecker (Part 3.D)
- FVGEntryCandleManager (Part 3.E)
- BreakoutTriggerChecker (Part 3.E)
- SetupStateMachine Part 3 lifecycle (Part 3.F)
- Part3StrategyEngine end-to-end evaluation (Part 3 sequence)
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.state.models import SetupState, SetupDirection
from src.state.state_machine import SetupStateMachine, SetupRepository
from src.strategy.strategy_core import (
    FVG, LiquiditySweep, Swing, ReferenceCandle, _fvg_id,
    MarketConfirmationChecker, FVGEntryCandleManager, BreakoutTriggerChecker,
)
from src.strategy.part3_strategy import Part3StrategyEngine, Part3TradeSignal

BASE = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(h: int, o: float, h_: float, l: float, c: float) -> Candle:
    return Candle(
        time=_t(h), open=o, high=h_, low=l, close=c,
        volume=100.0, symbol="XAUUSD", timeframe="H1",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Market Confirmation Checker (Part 3.D)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMarketConfirmationChecker:
    def test_bullish_confirmation_valid(self):
        prev = _c(1, 2000.0, 2010.0, 1995.0, 2005.0)
        curr = _c(2, 2005.0, 2015.0, 2002.0, 2012.0)  # close 2012 > prev.high 2010
        assert MarketConfirmationChecker.check_market_confirmation("BULLISH", curr, prev) is True

    def test_bullish_confirmation_rejected_when_close_equal(self):
        prev = _c(1, 2000.0, 2010.0, 1995.0, 2005.0)
        curr = _c(2, 2005.0, 2015.0, 2002.0, 2010.0)  # close 2010 == prev.high 2010 (strict inequality)
        assert MarketConfirmationChecker.check_market_confirmation("BULLISH", curr, prev) is False

    def test_bullish_confirmation_rejected_when_wick_above_but_close_below(self):
        prev = _c(1, 2000.0, 2010.0, 1995.0, 2005.0)
        curr = _c(2, 2005.0, 2015.0, 2002.0, 2008.0)  # high 2015 > 2010, but close 2008 < 2010
        assert MarketConfirmationChecker.check_market_confirmation("BULLISH", curr, prev) is False

    def test_bearish_confirmation_valid(self):
        prev = _c(1, 2020.0, 2025.0, 2015.0, 2018.0)
        curr = _c(2, 2018.0, 2020.0, 2008.0, 2012.0)  # close 2012 < prev.low 2015
        assert MarketConfirmationChecker.check_market_confirmation("BEARISH", curr, prev) is True

    def test_bearish_confirmation_rejected_when_close_equal(self):
        prev = _c(1, 2020.0, 2025.0, 2015.0, 2018.0)
        curr = _c(2, 2018.0, 2020.0, 2010.0, 2015.0)  # close 2015 == prev.low 2015
        assert MarketConfirmationChecker.check_market_confirmation("BEARISH", curr, prev) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FVG Entry Candle Manager (Part 3.E)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFVGEntryCandleManager:
    @pytest.fixture
    def bullish_fvg(self) -> FVG:
        return FVG(
            id=_fvg_id("XAUUSD", "BULLISH", _t(0)),
            symbol="XAUUSD", timeframe="H1",
            direction="BULLISH",
            fvg_low=2010.0, fvg_high=2020.0,
            c1_time=_t(0), c3_time=_t(2),
            c1_high=2010.0, c1_low=2005.0,
            c3_high=2030.0, c3_low=2020.0,
            atr_at_detection=5.0, created_at=_t(2),
        )

    def test_captures_first_entering_candle_and_freezes(self, bullish_fvg):
        # Candle 3 stays outside (low 2025 > 2020)
        c3 = _c(3, 2025.0, 2030.0, 2025.0, 2028.0)
        # Candle 4 penetrates FVG (low 2015 <= 2020)
        c4 = _c(4, 2028.0, 2029.0, 2015.0, 2016.0)
        # Candle 5 also inside FVG
        c5 = _c(5, 2016.0, 2018.0, 2012.0, 2014.0)

        entry_ref = FVGEntryCandleManager.find_first_entering_candle(bullish_fvg, [c3, c4, c5])
        assert entry_ref is not None
        assert entry_ref.candle.time == c4.time
        assert entry_ref.frozen is True
        assert entry_ref.trigger_high == c4.high

    def test_returns_none_when_no_candle_enters(self, bullish_fvg):
        c3 = _c(3, 2025.0, 2030.0, 2022.0, 2028.0)
        c4 = _c(4, 2028.0, 2032.0, 2024.0, 2030.0)
        entry_ref = FVGEntryCandleManager.find_first_entering_candle(bullish_fvg, [c3, c4])
        assert entry_ref is None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Breakout Trigger Checker (Part 3.E)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBreakoutTriggerChecker:
    def test_bullish_candle_breakout(self):
        entry_candle = _c(4, 2020.0, 2025.0, 2015.0, 2018.0)
        ref = ReferenceCandle(candle=entry_candle, frozen=True)

        breakout_c = _c(5, 2018.0, 2030.0, 2017.0, 2027.0)  # close 2027 > high 2025
        non_breakout = _c(5, 2018.0, 2025.0, 2017.0, 2023.0)  # close 2023 <= high 2025

        assert BreakoutTriggerChecker.check_candle_breakout("BULLISH", ref, breakout_c) is True
        assert BreakoutTriggerChecker.check_candle_breakout("BULLISH", ref, non_breakout) is False

    def test_bearish_candle_breakout(self):
        entry_candle = _c(4, 2020.0, 2025.0, 2015.0, 2018.0)
        ref = ReferenceCandle(candle=entry_candle, frozen=True)

        breakout_c = _c(5, 2018.0, 2019.0, 2010.0, 2012.0)  # close 2012 < low 2015
        non_breakout = _c(5, 2018.0, 2019.0, 2014.0, 2016.0)  # close 2016 >= low 2015

        assert BreakoutTriggerChecker.check_candle_breakout("BEARISH", ref, breakout_c) is True
        assert BreakoutTriggerChecker.check_candle_breakout("BEARISH", ref, non_breakout) is False

    def test_unfrozen_candle_raises_error(self):
        entry_candle = _c(4, 2020.0, 2025.0, 2015.0, 2018.0)
        ref = ReferenceCandle(candle=entry_candle, frozen=False)
        breakout_c = _c(5, 2018.0, 2030.0, 2017.0, 2027.0)

        with pytest.raises(ValueError, match="Entry candle must be frozen"):
            BreakoutTriggerChecker.check_candle_breakout("BULLISH", ref, breakout_c)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. State Machine Part 3 Sequence (Part 3.F)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPart3StateMachineSequence:
    def test_part3_lifecycle_flow(self, db):
        pivot = _c(1, 2005.0, 2010.0, 2000.0, 2005.0)
        swing = Swing(candle=pivot, level=2000.0, direction="LOW", confirmed_at=_t(2))
        sweep_c = _c(3, 2002.0, 2008.0, 1995.0, 2004.0)  # wick 1995 < 2000, close 2004 > 2000
        sweep = LiquiditySweep(swing=swing, sweep_candle=sweep_c, direction="BULLISH", swept_level=2000.0, sweep_extreme=1995.0)

        repo = SetupRepository(db)
        setup = repo.create_part3_setup("setup_p3_1", "XAUUSD", "H1", "BULLISH", sweep, _t(3))
        m = SetupStateMachine(setup, db)

        assert m.state == SetupState.SWEEP_CONFIRMED

        # Market Confirmation
        prev_c = sweep_c
        confirm_c = _c(4, 2004.0, 2015.0, 2003.0, 2012.0)  # close 2012 > prev high 2008
        assert m.confirm_market_confirmation(confirm_c, prev_c, _t(4)) is True
        assert m.state == SetupState.MARKET_CONFIRMATION

        # FVG Identified
        fvg = FVG(
            id=_fvg_id("XAUUSD", "BULLISH", _t(2)),
            symbol="XAUUSD", timeframe="H1",
            direction="BULLISH",
            fvg_low=2008.0, fvg_high=2015.0,
            c1_time=_t(2), c3_time=_t(4),
            c1_high=2008.0, c1_low=2000.0,
            c3_high=2022.0, c3_low=2015.0,
            atr_at_detection=5.0, created_at=_t(4),
        )
        assert m.identify_fvg(fvg, _t(4)) is True
        assert m.state == SetupState.FVG_IDENTIFIED

        # Retracement Watch
        assert m.begin_fvg_retracement(_t(4)) is True
        assert m.state == SetupState.WAITING_FOR_RETRACEMENT

        # Record First Entering Candle
        entry_c = _c(5, 2020.0, 2021.0, 2012.0, 2014.0)  # enters FVG (low 2012 <= high 2015)
        entry_ref = ReferenceCandle(candle=entry_c, frozen=True)
        assert m.record_fvg_entry(entry_ref, _t(5)) is True
        assert m.state == SetupState.FVG_ENTERED
        assert m.setup.ref_candle_frozen is True

        # Await Breakout
        assert m.await_breakout(_t(5)) is True
        assert m.state == SetupState.WAITING_FOR_BREAKOUT

        # Confirm Breakout
        assert m.confirm_breakout(
            proposed_entry=2022.0, proposed_sl=1994.0, proposed_tp=2078.0,
            proposed_volume=0.01, estimated_risk_usd=100.0, estimated_rr=2.0,
            timestamp=_t(6),
        ) is True
        assert m.state == SetupState.ENTRY_CONFIRMED

        # Risk check & order
        assert m.begin_risk_check(_t(6)) is True
        assert m.state == SetupState.RISK_CHECK
        assert m.risk_approved(_t(6)) is True
        assert m.state == SetupState.ORDER_PENDING
        assert m.position_opened(_t(6)) is True
        assert m.state == SetupState.POSITION_OPEN


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Part3StrategyEngine End-to-End Evaluation
# ═══════════════════════════════════════════════════════════════════════════════

class TestPart3StrategyEngine:
    def test_full_bullish_sequence_produces_signal(self):
        engine = Part3StrategyEngine(symbol="XAUUSD", timeframe="H1")

        # Build realistic H1 candles:
        # C0..C3: establish swing low at C1 (low = 2000.0)
        # Left bars = 2, right bars = 2
        c0 = _c(0, 2010.0, 2015.0, 2005.0, 2008.0)
        c1 = _c(1, 2008.0, 2012.0, 2000.0, 2004.0)  # Pivot Low = 2000.0
        c2 = _c(2, 2004.0, 2010.0, 2003.0, 2008.0)
        c3 = _c(3, 2008.0, 2014.0, 2005.0, 2012.0)  # Swing Low confirmed at C3 open (2000.0)
        
        # C4: Liquidity sweep (low 1996 < 2000, close 2002 > 2000)
        c4 = _c(4, 2010.0, 2010.0, 1996.0, 2002.0)

        # C5: Market confirmation & FVG C1 (close 2012 > C4 high 2010)
        c5 = _c(5, 2002.0, 2014.0, 2001.0, 2012.0)  # FVG C1 high = 2014.0

        # C6: Big expansion candle (FVG C2)
        c6 = _c(6, 2012.0, 2028.0, 2012.0, 2026.0)

        # C7: FVG C3 (low 2022 > C5 high 2014 -> gap between 2014 and 2022)
        c7 = _c(7, 2026.0, 2035.0, 2022.0, 2032.0)

        # C8: Retracement enters FVG (low 2018 <= 2022). High is 2025.0
        c8 = _c(8, 2024.0, 2025.0, 2018.0, 2020.0)

        # C9: Breakout candle (close 2028 > C8 high 2025)
        c9 = _c(9, 2020.0, 2030.0, 2019.0, 2028.0)

        # Provide enough baseline candles before C0 for ATR(14)
        prefix = [
            _c(-15 + i, 2010.0 + i, 2015.0 + i, 2005.0 + i, 2010.0 + i)
            for i in range(15)
        ]
        candles = prefix + [c0, c1, c2, c3, c4, c5, c6, c7, c8, c9]

        signals = engine.evaluate(candles)
        assert len(signals) >= 1
        sig = signals[0]
        assert sig.direction == "BULLISH"
        assert sig.entry_price == c9.close
        assert sig.sl_price < sig.sweep_extreme  # SL below sweep extreme 1996.0
        assert sig.tp_price > sig.entry_price
        assert sig.rr >= 2.0

    def test_full_bearish_sequence_produces_signal(self):
        engine = Part3StrategyEngine(symbol="XAUUSD", timeframe="H1")

        # C0..C3: establish swing high at C1 (high = 2050.0)
        c0 = _c(0, 2040.0, 2042.0, 2035.0, 2038.0)
        c1 = _c(1, 2038.0, 2050.0, 2037.0, 2045.0)  # Pivot High = 2050.0
        c2 = _c(2, 2045.0, 2046.0, 2040.0, 2042.0)
        c3 = _c(3, 2042.0, 2044.0, 2038.0, 2040.0)  # Confirmed at C3

        # C4: Liquidity sweep of swing high (high 2053 > 2050, close 2047 < 2050)
        c4 = _c(4, 2040.0, 2053.0, 2039.0, 2047.0)

        # C5: Market confirmation & FVG C1 (close 2036 < C4 low 2039)
        c5 = _c(5, 2047.0, 2048.0, 2035.0, 2036.0)  # C1 low = 2035.0

        # C6: Big expansion candle down (FVG C2)
        c6 = _c(6, 2036.0, 2037.0, 2018.0, 2020.0)

        # C7: FVG C3 (high 2026 < C5 low 2035 -> gap between 2026 and 2035)
        c7 = _c(7, 2020.0, 2026.0, 2015.0, 2018.0)

        # C8: Retracement enters FVG from below (high 2030 >= 2026). Low is 2022.0
        c8 = _c(8, 2023.0, 2030.0, 2022.0, 2025.0)

        # C9: Breakout candle down (close 2019 < C8 low 2022)
        c9 = _c(9, 2025.0, 2026.0, 2016.0, 2019.0)

        prefix = [
            _c(-15 + i, 2040.0 - i, 2045.0 - i, 2035.0 - i, 2040.0 - i)
            for i in range(15)
        ]
        candles = prefix + [c0, c1, c2, c3, c4, c5, c6, c7, c8, c9]

        signals = engine.evaluate(candles)
        assert len(signals) >= 1
        sig = signals[0]
        assert sig.direction == "BEARISH"
        assert sig.entry_price == c9.close
        assert sig.sl_price > sig.sweep_extreme  # SL above sweep extreme 2053.0
        assert sig.tp_price < sig.entry_price
        assert sig.rr >= 2.0
