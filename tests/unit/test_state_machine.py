"""
Unit tests for SetupStateMachine and SetupRepository.

Covers R19, R20, R23, R24, R64–R69, R73.
Uses in-memory SQLite via the conftest db fixture.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.state.models import SetupState, SetupDirection
from src.state.state_machine import SetupStateMachine, SetupRepository
from src.strategy.strategy_core import (
    FVG, LiquiditySweep, Swing, ReferenceCandle, _fvg_id,
)

BASE = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(h: int, lo: float, hi: float) -> Candle:
    return Candle(
        time=_t(h), open=(lo + hi) / 2, high=hi, low=lo,
        close=(lo + hi) / 2, volume=100.0,
        symbol="XAUUSD", timeframe="H1",
    )


def _make_fvg(direction: str = "BULLISH") -> FVG:
    return FVG(
        id=_fvg_id("XAUUSD", direction, _t(0)),
        symbol="XAUUSD", timeframe="H1",
        direction=direction,
        fvg_low=2010.0, fvg_high=2015.0,
        c1_time=_t(0), c3_time=_t(2),
        c1_high=2010.0, c1_low=2005.0,
        c3_high=2022.0, c3_low=2015.0,
        atr_at_detection=4.0, created_at=_t(2),
    )


def _make_sweep(direction: str = "BULLISH", sweep_low: float = 2000.0) -> LiquiditySweep:
    pivot = _c(1, lo=sweep_low - 5, hi=sweep_low + 5)
    swing = Swing(candle=pivot, level=sweep_low, direction="LOW",
                  confirmed_at=_t(2))
    sweep_candle = _c(4, lo=sweep_low - 2, hi=sweep_low + 8)
    return LiquiditySweep(
        swing=swing, sweep_candle=sweep_candle,
        direction=direction, swept_level=sweep_low,
        sweep_extreme=sweep_low - 2,
    )


def _make_ref(hi: float = 2018.0, lo: float = 2012.0,
              frozen: bool = False) -> ReferenceCandle:
    c = _c(5, lo=lo, hi=hi)
    return ReferenceCandle(candle=c, frozen=frozen)


class TestHappyPathSequence:
    """R19: all transitions follow the required order."""

    def test_full_sequence_reaches_position_open(self, db) -> None:
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)

        assert m.state == SetupState.FVG_DETECTED

        m.confirm_sweep(_make_sweep(), _t(4))
        assert m.state == SetupState.SWEEP_CONFIRMED

        m.begin_retracement_watch(_t(4))
        assert m.state == SetupState.WAITING_FOR_RETRACEMENT

        m.save_reference_candle(_make_ref(), _t(5))
        assert m.state == SetupState.REFERENCE_CANDLE_SAVED

        m.confirm_gap_exit(_t(6))
        assert m.state == SetupState.WAITING_FOR_GAP_EXIT

        m.confirm_ready_to_trigger(_t(6))
        assert m.state == SetupState.WAITING_FOR_TRIGGER

        m.signal_ready(2020.0, 2005.0, 2050.0, 0.01, 100.0, 2.0, _t(7))
        assert m.state == SetupState.SIGNAL_READY

        m.begin_risk_check(_t(7))
        assert m.state == SetupState.RISK_CHECK

        m.risk_approved(_t(7))
        assert m.state == SetupState.ORDER_PENDING

        m.position_opened(_t(7))
        assert m.state == SetupState.POSITION_OPEN

        m.position_closed(_t(8))
        assert m.state == SetupState.CLOSED
        assert m.is_terminal

    def test_all_transitions_persisted(self, db) -> None:
        """R73: every transition written to audit log."""
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        m.confirm_sweep(_make_sweep(), _t(4))
        m.begin_retracement_watch(_t(4))

        transitions = setup.transitions
        events = [t.event for t in transitions]
        assert "FVG_DETECTED" in events
        assert "SWEEP_CONFIRMED" in events
        assert "RETRACEMENT_WATCH_STARTED" in events


class TestOutOfOrderRejection:
    """R20: transitions out of sequence are rejected."""

    def test_sweep_ignored_when_not_in_fvg_detected(self, db) -> None:
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        m.confirm_sweep(_make_sweep(), _t(4))
        m.begin_retracement_watch(_t(4))
        # Try confirming sweep again — wrong state
        result = m.confirm_sweep(_make_sweep(), _t(5))
        assert result is False
        assert m.state == SetupState.WAITING_FOR_RETRACEMENT

    def test_position_opened_from_wrong_state_rejected(self, db) -> None:
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        result = m.position_opened(_t(5))
        assert result is False
        assert m.state == SetupState.FVG_DETECTED


class TestReferenceCandle:
    """R23, R24: reference candle update and freeze."""

    def test_reference_candle_can_be_updated_before_freeze(self, db) -> None:
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        m.confirm_sweep(_make_sweep(), _t(4))
        m.begin_retracement_watch(_t(4))
        m.save_reference_candle(_make_ref(hi=2016.0), _t(5))

        assert setup.trigger_level == pytest.approx(2016.0)
        m.update_reference_candle(_make_ref(hi=2018.0), _t(6))
        assert setup.trigger_level == pytest.approx(2018.0)

    def test_reference_candle_frozen_after_gap_exit(self, db) -> None:
        """R24: after confirm_gap_exit, ref_candle_frozen=True."""
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        m.confirm_sweep(_make_sweep(), _t(4))
        m.begin_retracement_watch(_t(4))
        m.save_reference_candle(_make_ref(hi=2018.0), _t(5))
        m.confirm_gap_exit(_t(6))

        assert setup.ref_candle_frozen is True

    def test_cannot_update_ref_after_gap_exit(self, db) -> None:
        """R24: update_reference_candle rejected after freeze."""
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        m.confirm_sweep(_make_sweep(), _t(4))
        m.begin_retracement_watch(_t(4))
        m.save_reference_candle(_make_ref(hi=2018.0), _t(5))
        m.confirm_gap_exit(_t(6))
        m.confirm_ready_to_trigger(_t(6))

        old_trigger = setup.trigger_level
        result = m.update_reference_candle(_make_ref(hi=2020.0), _t(7))
        assert result is False
        assert setup.trigger_level == old_trigger  # unchanged


class TestTerminalStateProtection:
    """R69: no transitions from terminal states."""

    def test_expired_setup_cannot_transition(self, db) -> None:
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        m.expire("test expiry", _t(5))
        assert m.is_terminal
        # Any further transition should fail
        assert m.expire("again", _t(6)) is False
        assert m.invalidate("again", _t(6)) is False

    def test_invalidated_cannot_be_resurrected(self, db) -> None:
        """R69: no resurrection."""
        fvg = _make_fvg()
        repo = SetupRepository(db)
        setup = repo.create(fvg.id, fvg, _t(0))
        m = SetupStateMachine(setup, db)
        m.invalidate("test", _t(5))
        assert m.state == SetupState.INVALIDATED
        assert m.confirm_sweep(_make_sweep(), _t(6)) is False


class TestSetupRepository:
    def test_create_and_get(self, db) -> None:
        fvg = _make_fvg()
        repo = SetupRepository(db)
        created = repo.create(fvg.id, fvg, _t(0))
        fetched = repo.get(fvg.id)
        assert fetched is not None
        assert fetched.id == fvg.id
        assert fetched.state == SetupState.FVG_DETECTED

    def test_get_active_excludes_terminal(self, db) -> None:
        fvg = _make_fvg()
        fvg2_id = _fvg_id("XAUUSD", "BEARISH", _t(10))
        from src.strategy.strategy_core import FVG as FVGType
        fvg2 = FVGType(
            id=fvg2_id, symbol="XAUUSD", timeframe="H1",
            direction="BEARISH", fvg_low=2045.0, fvg_high=2050.0,
            c1_time=_t(10), c3_time=_t(12),
            c1_high=2050.0, c1_low=2045.0,
            c3_high=2048.0, c3_low=2044.0,
            atr_at_detection=4.0, created_at=_t(12),
        )
        repo = SetupRepository(db)
        s1 = repo.create(fvg.id, fvg, _t(0))
        s2 = repo.create(fvg2.id, fvg2, _t(10))

        m1 = SetupStateMachine(s1, db)
        m1.expire("expired for test", _t(5))

        active = repo.get_active(symbol="XAUUSD")
        ids = {s.id for s in active}
        assert fvg.id not in ids       # expired → not active
        assert fvg2.id in ids           # not expired → active
