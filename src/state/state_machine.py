"""
Persistent Setup State Machine — STRATEGY_SPEC.md v1.0

State flow (R19 happy path):
  FVG_DETECTED
    → SWEEP_CONFIRMED
    → WAITING_FOR_RETRACEMENT
    → REFERENCE_CANDLE_SAVED      (first qualifying retracement candle)
    → WAITING_FOR_GAP_EXIT        (ref candle frozen; monitoring for gap exit)
    → GAP_EXITED                  (gap exit confirmed — NEW state, IMPL3)
    → WAITING_FOR_TRIGGER
    → SIGNAL_READY
    → RISK_CHECK
    → ORDER_PENDING
    → POSITION_OPEN
    → CLOSED

Terminal states (R69): CLOSED, EXPIRED, INVALIDATED, REJECTED
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.state.models import (
    Setup, SetupState, SetupTransition, SetupDirection,
    SPEC_VERSION,
)
from src.strategy.strategy_core import (
    FVG, LiquiditySweep, ReferenceCandle, SPEC_HASH_PLACEHOLDER,
)
from src.data.candle import Candle
from src.utils.logging_config import get_logger

log = get_logger(__name__)

_TERMINAL_STATES = {
    SetupState.CLOSED,
    SetupState.EXPIRED,
    SetupState.INVALIDATED,
    SetupState.REJECTED,
}


class SetupStateMachine:
    """
    Manages one trading setup through its lifecycle.

    Every transition is persisted immediately (R73).
    The caller must provide a valid SQLAlchemy session.
    No clock reads inside — timestamps are injected (IMPL1).
    """

    def __init__(
        self,
        setup: Setup,
        db: Session,
        spec_hash: str = SPEC_HASH_PLACEHOLDER,
    ) -> None:
        self._setup = setup
        self._db = db
        self._spec_hash = spec_hash

    @property
    def setup_id(self) -> str:
        return self._setup.id

    @property
    def state(self) -> SetupState:
        return self._setup.state

    @property
    def is_terminal(self) -> bool:
        return self._setup.state in _TERMINAL_STATES

    @property
    def setup(self) -> Setup:
        return self._setup

    # ── Transitions (R19 sequence) ────────────────────────────────────────────

    def confirm_sweep(self, sweep: LiquiditySweep, timestamp: datetime) -> bool:
        """FVG_DETECTED → SWEEP_CONFIRMED (stage 2)."""
        if self._setup.state != SetupState.FVG_DETECTED:
            log.warning("confirm_sweep_wrong_state",
                        id=self.setup_id, state=self._setup.state)
            return False
        self._setup.sweep_level = sweep.swept_level
        self._setup.sweep_candle_time = sweep.sweep_candle.time
        self._setup.sweep_extreme = sweep.sweep_extreme
        self._transition(
            SetupState.FVG_DETECTED, SetupState.SWEEP_CONFIRMED,
            "SWEEP_CONFIRMED",
            f"Sweep at {sweep.swept_level:.5f} "
            f"candle={sweep.sweep_candle.time.isoformat()} "
            f"extreme={sweep.sweep_extreme:.5f}",
            timestamp,
        )
        return True

    def begin_retracement_watch(self, timestamp: datetime) -> bool:
        """SWEEP_CONFIRMED → WAITING_FOR_RETRACEMENT (stage 3)."""
        if self._setup.state != SetupState.SWEEP_CONFIRMED:
            return False
        self._transition(
            SetupState.SWEEP_CONFIRMED, SetupState.WAITING_FOR_RETRACEMENT,
            "RETRACEMENT_WATCH_STARTED",
            "Monitoring for price retracement into FVG",
            timestamp,
        )
        return True

    def save_reference_candle(self, ref: ReferenceCandle, timestamp: datetime) -> bool:
        """WAITING_FOR_RETRACEMENT → REFERENCE_CANDLE_SAVED (stage 4)."""
        if self._setup.state != SetupState.WAITING_FOR_RETRACEMENT:
            return False
        self._store_reference(ref)
        self._transition(
            SetupState.WAITING_FOR_RETRACEMENT, SetupState.REFERENCE_CANDLE_SAVED,
            "REFERENCE_CANDLE_SAVED",
            f"Ref candle {ref.candle.time.isoformat()} "
            f"H={ref.candle.high:.5f} L={ref.candle.low:.5f} "
            f"trigger={self._setup.trigger_level:.5f}",
            timestamp,
        )
        return True

    def update_reference_candle(self, ref: ReferenceCandle, timestamp: datetime) -> bool:
        """
        Update reference candle while in REFERENCE_CANDLE_SAVED (R23).
        Only allowed before gap exit (ref not yet frozen).
        """
        if self._setup.state != SetupState.REFERENCE_CANDLE_SAVED:
            return False
        old_trigger = self._setup.trigger_level
        self._store_reference(ref)
        self._transition(
            SetupState.REFERENCE_CANDLE_SAVED, SetupState.REFERENCE_CANDLE_SAVED,
            "REFERENCE_CANDLE_UPDATED",
            f"Ref updated {ref.candle.time.isoformat()} "
            f"trigger {old_trigger:.5f} → {self._setup.trigger_level:.5f}",
            timestamp,
        )
        return True

    def confirm_gap_exit(self, timestamp: datetime) -> bool:
        """
        REFERENCE_CANDLE_SAVED → WAITING_FOR_GAP_EXIT (stage 5).

        The reference candle is now frozen — no more updates (R24).
        """
        if self._setup.state != SetupState.REFERENCE_CANDLE_SAVED:
            return False
        self._setup.ref_candle_frozen = True
        self._transition(
            SetupState.REFERENCE_CANDLE_SAVED, SetupState.WAITING_FOR_GAP_EXIT,
            "GAP_EXIT_DETECTED",
            f"Price exited FVG. Ref candle FROZEN. "
            f"Trigger level={self._setup.trigger_level:.5f}",
            timestamp,
        )
        return True

    def confirm_ready_to_trigger(self, timestamp: datetime) -> bool:
        """
        WAITING_FOR_GAP_EXIT → GAP_EXITED → WAITING_FOR_TRIGGER (stages 6–7).

        This fires when the gap exit is fully confirmed and we start watching
        for the trigger level break.
        """
        if self._setup.state not in (
            SetupState.WAITING_FOR_GAP_EXIT, SetupState.GAP_EXITED
        ):
            return False
        # Pass through GAP_EXITED as a named intermediate state (IMPL3)
        if self._setup.state == SetupState.WAITING_FOR_GAP_EXIT:
            self._transition(
                SetupState.WAITING_FOR_GAP_EXIT, SetupState.GAP_EXITED,
                "GAP_EXITED",
                "Gap exit fully confirmed",
                timestamp,
            )
        self._transition(
            SetupState.GAP_EXITED, SetupState.WAITING_FOR_TRIGGER,
            "READY_FOR_TRIGGER",
            f"Monitoring trigger level {self._setup.trigger_level:.5f}",
            timestamp,
        )
        return True

    def signal_ready(
        self,
        proposed_entry: float,
        proposed_sl: float,
        proposed_tp: float,
        proposed_volume: float,
        estimated_risk_usd: float,
        estimated_rr: float,
        timestamp: datetime,
    ) -> bool:
        """WAITING_FOR_TRIGGER → SIGNAL_READY (stage 8)."""
        if self._setup.state != SetupState.WAITING_FOR_TRIGGER:
            return False
        self._setup.proposed_entry = proposed_entry
        self._setup.proposed_sl = proposed_sl
        self._setup.proposed_tp = proposed_tp
        self._setup.proposed_volume = proposed_volume
        self._setup.estimated_risk_usd = estimated_risk_usd
        self._setup.estimated_rr = estimated_rr
        self._setup.trigger_fired_at = timestamp
        self._transition(
            SetupState.WAITING_FOR_TRIGGER, SetupState.SIGNAL_READY,
            "TRIGGER_BROKEN",
            f"Entry={proposed_entry:.5f} SL={proposed_sl:.5f} "
            f"TP={proposed_tp:.5f} Vol={proposed_volume} "
            f"Risk=${estimated_risk_usd:.2f} R:R={estimated_rr:.2f}",
            timestamp,
        )
        return True

    def begin_risk_check(self, timestamp: datetime) -> bool:
        """SIGNAL_READY or ENTRY_CONFIRMED → RISK_CHECK (stage 9)."""
        if self._setup.state not in (SetupState.SIGNAL_READY, SetupState.ENTRY_CONFIRMED):
            return False
        old_state = self._setup.state
        self._transition(
            old_state, SetupState.RISK_CHECK,
            "RISK_CHECK_STARTED", None, timestamp,
        )
        return True

    def risk_approved(self, timestamp: datetime) -> bool:
        """RISK_CHECK → ORDER_PENDING (stage 10)."""
        if self._setup.state != SetupState.RISK_CHECK:
            return False
        self._transition(
            SetupState.RISK_CHECK, SetupState.ORDER_PENDING,
            "RISK_APPROVED", None, timestamp,
        )
        return True

    def risk_rejected(self, reason: str, timestamp: datetime) -> bool:
        """RISK_CHECK / SIGNAL_READY / ENTRY_CONFIRMED → REJECTED."""
        if self._setup.state not in (SetupState.RISK_CHECK, SetupState.SIGNAL_READY, SetupState.ENTRY_CONFIRMED):
            return False
        old = self._setup.state
        self._setup.rejection_reason = reason
        self._transition(old, SetupState.REJECTED, "RISK_REJECTED", reason, timestamp)
        return True

    # ── Part 3 Master Specification Explicit Sequence Transitions ───────────

    def confirm_sweep_detected(self, sweep: LiquiditySweep, timestamp: datetime) -> bool:
        """DETECTED → SWEEP_CONFIRMED (Part 3.C)."""
        if self._setup.state not in (SetupState.DETECTED, SetupState.FVG_DETECTED):
            return False
        old_state = self._setup.state
        self._setup.sweep_level = sweep.swept_level
        self._setup.sweep_candle_time = sweep.sweep_candle.time
        self._setup.sweep_extreme = sweep.sweep_extreme
        self._transition(
            old_state, SetupState.SWEEP_CONFIRMED,
            "SWEEP_CONFIRMED",
            f"Confirmed sweep of {sweep.direction} swing at {sweep.swept_level:.5f}. "
            f"Extreme: {sweep.sweep_extreme:.5f}",
            timestamp,
        )
        return True

    def confirm_market_confirmation(
        self,
        confirming_candle: Candle,
        preceding_candle: Candle,
        timestamp: datetime,
    ) -> bool:
        """SWEEP_CONFIRMED → MARKET_CONFIRMATION (Part 3.D)."""
        if self._setup.state != SetupState.SWEEP_CONFIRMED:
            return False
        self._setup.market_confirmation_time = confirming_candle.time
        self._setup.market_confirmation_candle_close = confirming_candle.close
        extreme = preceding_candle.high if self._setup.direction == SetupDirection.BULLISH else preceding_candle.low
        self._setup.market_confirmation_preceding_extreme = extreme
        self._transition(
            SetupState.SWEEP_CONFIRMED, SetupState.MARKET_CONFIRMATION,
            "MARKET_CONFIRMATION",
            f"Preceding candle {'high' if self._setup.direction == SetupDirection.BULLISH else 'low'} "
            f"broken at {confirming_candle.close:.5f} vs {extreme:.5f}",
            timestamp,
        )
        return True

    def identify_fvg(self, fvg: FVG, timestamp: datetime) -> bool:
        """MARKET_CONFIRMATION → FVG_IDENTIFIED (Part 3.B)."""
        if self._setup.state != SetupState.MARKET_CONFIRMATION:
            return False
        self._setup.fvg_high = fvg.fvg_high
        self._setup.fvg_low = fvg.fvg_low
        self._setup.fvg_open_time = fvg.c1_time
        self._setup.fvg_c1_time = fvg.c1_time
        self._setup.fvg_c3_time = fvg.c3_time
        self._setup.fvg_atr_at_detection = fvg.atr_at_detection
        self._setup.fvg_c1_high = fvg.c1_high
        self._setup.fvg_c1_low = fvg.c1_low
        self._setup.fvg_c3_high = fvg.c3_high
        self._setup.fvg_c3_low = fvg.c3_low
        self._transition(
            SetupState.MARKET_CONFIRMATION, SetupState.FVG_IDENTIFIED,
            "FVG_IDENTIFIED",
            f"FVG identified [{fvg.fvg_low:.5f} - {fvg.fvg_high:.5f}]",
            timestamp,
        )
        return True

    def begin_fvg_retracement(self, timestamp: datetime) -> bool:
        """FVG_IDENTIFIED → WAITING_FOR_RETRACEMENT (Part 3.E)."""
        if self._setup.state != SetupState.FVG_IDENTIFIED:
            return False
        self._transition(
            SetupState.FVG_IDENTIFIED, SetupState.WAITING_FOR_RETRACEMENT,
            "WAITING_FOR_RETRACEMENT",
            "Awaiting price retracement into FVG zone",
            timestamp,
        )
        return True

    def record_fvg_entry(self, entry_candle: ReferenceCandle, timestamp: datetime) -> bool:
        """WAITING_FOR_RETRACEMENT → FVG_ENTERED (Part 3.E - locks & freezes first entering candle)."""
        if self._setup.state != SetupState.WAITING_FOR_RETRACEMENT:
            return False
        self._store_reference(entry_candle)
        self._setup.ref_candle_frozen = True
        self._transition(
            SetupState.WAITING_FOR_RETRACEMENT, SetupState.FVG_ENTERED,
            "FVG_ENTERED",
            f"First candle entered FVG at {entry_candle.candle.time.isoformat()}. "
            f"FROZEN trigger level: {self._setup.trigger_level:.5f}",
            timestamp,
        )
        return True

    def await_breakout(self, timestamp: datetime) -> bool:
        """FVG_ENTERED → WAITING_FOR_BREAKOUT (Part 3.E)."""
        if self._setup.state != SetupState.FVG_ENTERED:
            return False
        self._transition(
            SetupState.FVG_ENTERED, SetupState.WAITING_FOR_BREAKOUT,
            "WAITING_FOR_BREAKOUT",
            f"Watching for breakout beyond {self._setup.trigger_level:.5f}",
            timestamp,
        )
        return True

    def confirm_breakout(
        self,
        proposed_entry: float,
        proposed_sl: float,
        proposed_tp: float,
        proposed_volume: float,
        estimated_risk_usd: float,
        estimated_rr: float,
        timestamp: datetime,
    ) -> bool:
        """WAITING_FOR_BREAKOUT → ENTRY_CONFIRMED (Part 3.E)."""
        if self._setup.state != SetupState.WAITING_FOR_BREAKOUT:
            return False
        self._setup.proposed_entry = proposed_entry
        self._setup.proposed_sl = proposed_sl
        self._setup.proposed_tp = proposed_tp
        self._setup.proposed_volume = proposed_volume
        self._setup.estimated_risk_usd = estimated_risk_usd
        self._setup.estimated_rr = estimated_rr
        self._setup.trigger_fired_at = timestamp
        self._transition(
            SetupState.WAITING_FOR_BREAKOUT, SetupState.ENTRY_CONFIRMED,
            "ENTRY_CONFIRMED",
            f"Breakout confirmed at {proposed_entry:.5f}. SL={proposed_sl:.5f}, TP={proposed_tp:.5f}, R:R={estimated_rr:.2f}",
            timestamp,
        )
        return True

    def position_opened(self, timestamp: datetime) -> bool:
        """ORDER_PENDING → POSITION_OPEN (stage 11)."""
        if self._setup.state != SetupState.ORDER_PENDING:
            return False
        self._transition(
            SetupState.ORDER_PENDING, SetupState.POSITION_OPEN,
            "POSITION_OPENED", None, timestamp,
        )
        return True

    def position_closed(self, timestamp: datetime) -> bool:
        """POSITION_OPEN → CLOSED (stage 12 / terminal)."""
        if self._setup.state != SetupState.POSITION_OPEN:
            return False
        self._transition(
            SetupState.POSITION_OPEN, SetupState.CLOSED,
            "POSITION_CLOSED", None, timestamp,
        )
        return True

    def expire(self, reason: str, timestamp: datetime) -> bool:
        """Any non-terminal state → EXPIRED."""
        if self.is_terminal:
            return False
        self._setup.rejection_reason = reason
        self._transition(self._setup.state, SetupState.EXPIRED,
                         "EXPIRED", reason, timestamp)
        return True

    def invalidate(self, reason: str, timestamp: datetime) -> bool:
        """Any non-terminal state → INVALIDATED."""
        if self.is_terminal:
            return False
        self._setup.rejection_reason = reason
        self._transition(self._setup.state, SetupState.INVALIDATED,
                         "INVALIDATED", reason, timestamp)
        return True

    # ── Internal ──────────────────────────────────────────────────────────────

    def _store_reference(self, ref: ReferenceCandle) -> None:
        c = ref.candle
        self._setup.ref_candle_time = c.time
        self._setup.ref_candle_open = c.open
        self._setup.ref_candle_high = c.high
        self._setup.ref_candle_low = c.low
        self._setup.ref_candle_close = c.close
        if self._setup.direction == SetupDirection.BULLISH:
            self._setup.trigger_level = c.high
        else:
            self._setup.trigger_level = c.low

    def _transition(
        self,
        old: SetupState,
        new: SetupState,
        event: str,
        explanation: str | None,
        timestamp: datetime,
    ) -> None:
        self._setup.state = new
        self._setup.updated_at = timestamp

        row = SetupTransition(
            setup_id=self._setup.id,
            timestamp=timestamp,
            old_state=old,
            new_state=new,
            event=event,
            explanation=explanation,
            spec_version=SPEC_VERSION,
            spec_hash=self._spec_hash,
        )
        self._db.add(row)
        self._db.add(self._setup)
        try:
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            log.error("transition_commit_failed",
                      setup_id=self.setup_id, transition_event=event, exc=str(exc))
            raise

        log.info("setup_transition",
                 id=self.setup_id, symbol=self._setup.symbol,
                 old=old.value if old else None, new=new.value, transition_event=event)


class SetupRepository:
    """CRUD for Setup rows."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, setup_id: str, fvg: FVG, now: datetime) -> Setup:
        direction = SetupDirection(fvg.direction)
        setup = Setup(
            id=setup_id,
            symbol=fvg.symbol,
            timeframe=fvg.timeframe,
            direction=direction,
            state=SetupState.FVG_DETECTED,
            created_at=now,
            updated_at=now,
            fvg_high=fvg.fvg_high,
            fvg_low=fvg.fvg_low,
            fvg_open_time=fvg.c1_time,
            fvg_c1_time=fvg.c1_time,
            fvg_c3_time=fvg.c3_time,
            fvg_atr_at_detection=fvg.atr_at_detection,
            # Store individual C1/C3 values for invalidation checks (B3 fix)
            fvg_c1_high=fvg.c1_high,
            fvg_c1_low=fvg.c1_low,
            fvg_c3_high=fvg.c3_high,
            fvg_c3_low=fvg.c3_low,
            spec_version=SPEC_VERSION,
        )
        transition = SetupTransition(
            setup_id=setup_id,
            timestamp=now,
            old_state=None,
            new_state=SetupState.FVG_DETECTED,
            event="FVG_DETECTED",
            explanation=(
                f"{'Bullish' if fvg.direction == 'BULLISH' else 'Bearish'} FVG "
                f"[{fvg.fvg_low:.5f}–{fvg.fvg_high:.5f}] "
                f"detected at C3={fvg.c3_time.isoformat()}"
            ),
            spec_version=SPEC_VERSION,
        )
        self._db.add(setup)
        self._db.add(transition)
        self._db.commit()
        return setup

    def create_part3_setup(
        self,
        setup_id: str,
        symbol: str,
        timeframe: str,
        direction: str,
        sweep: LiquiditySweep,
        now: datetime,
    ) -> Setup:
        """Create a new setup following Part 3 lifecycle starting from SWEEP_CONFIRMED."""
        setup_dir = SetupDirection(direction)
        setup = Setup(
            id=setup_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=setup_dir,
            state=SetupState.SWEEP_CONFIRMED,
            created_at=now,
            updated_at=now,
            sweep_level=sweep.swept_level,
            sweep_candle_time=sweep.sweep_candle.time,
            sweep_extreme=sweep.sweep_extreme,
            spec_version=SPEC_VERSION,
        )
        transition = SetupTransition(
            setup_id=setup_id,
            timestamp=now,
            old_state=None,
            new_state=SetupState.SWEEP_CONFIRMED,
            event="SWEEP_CONFIRMED",
            explanation=f"Part 3 setup initiated on {direction} sweep at {sweep.swept_level:.5f}",
            spec_version=SPEC_VERSION,
        )
        self._db.add(setup)
        self._db.add(transition)
        self._db.commit()
        return setup

    def get(self, setup_id: str) -> Setup | None:
        return self._db.get(Setup, setup_id)

    def get_active(self, symbol: str | None = None) -> list[Setup]:
        q = self._db.query(Setup).filter(
            Setup.state.notin_([s.value for s in _TERMINAL_STATES])
        )
        if symbol:
            q = q.filter(Setup.symbol == symbol)
        return q.all()

    def get_all(self, symbol: str | None = None, limit: int = 200) -> list[Setup]:
        q = self._db.query(Setup).order_by(Setup.created_at.desc())
        if symbol:
            q = q.filter(Setup.symbol == symbol)
        return q.limit(limit).all()
