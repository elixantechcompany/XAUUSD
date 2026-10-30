"""
Trading Engine — STRATEGY_SPEC.md v1.0

This is the main evaluation loop. It:
  1. Fetches completed H1 candles from MT5 (or HistoricalDataAdapter in backtest).
  2. Runs FVG detection, swing detection, sweep detection on each symbol.
  3. Advances active setup state machines step by step.
  4. Calls the risk engine before any order submission.
  5. Delegates execution to PaperExecutor (PAPER mode) or a future DemoExecutor.
  6. Persists every decision and state change before submitting orders.

The engine is deterministic when fed the same candles and config.
It does NOT read the system clock for trading decisions — clock is injected.
It does NOT call MT5 order functions directly — all broker interaction
goes through the execution gateway interface.

Live trading is permanently disabled (IMPL7).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from typing import Protocol

from sqlalchemy.orm import Session

from src.config.settings import AppSettings, get_settings
from src.data.candle import Candle
from src.data.indicators import atr as compute_atr
from src.data.market_data_adapter import MarketDataProtocol, SymbolInfo
from src.execution.paper_executor import PaperExecutor
from src.journal.models import DailyRiskState, JournalEntry
from src.risk.engine import RiskEngine, SizingResult
from src.state.models import (
    Setup, SetupState, SetupDirection, SetupTransition, Order, DecisionLog,
)
from src.state.state_machine import SetupStateMachine, SetupRepository
from src.strategy.strategy_core import (
    FVGDetector, SwingDetector, LiquiditySweepDetector,
    ReferenceCandleSelector, GapExitChecker, EntryTriggerChecker,
    StopLossCalculator, TakeProfitCalculator, SetupExpiryChecker,
    FVG, LiquiditySweep, ReferenceCandle, Swing,
    SPEC_VERSION, SPEC_HASH_PLACEHOLDER,
)
from src.utils.ids import order_client_id
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# ── How many completed H1 candles to fetch per evaluation ────────────────────
CANDLE_LOOKBACK = 200


# ═══════════════════════════════════════════════════════════════════════════════
# Engine output types
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EvaluationResult:
    """Summary of one full engine evaluation cycle."""
    symbol: str
    timestamp: datetime
    candles_evaluated: int
    new_fvgs: int
    setups_advanced: int
    signals_generated: int
    orders_submitted: int
    orders_rejected: int
    errors: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Execution gateway protocol (IMPL7)
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionGatewayProtocol(Protocol):
    """Interface any execution backend must satisfy."""
    MODE: str

    def submit_order(
        self,
        setup_id: str,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        sl: float,
        tp: float,
        current_ask: float,
        current_bid: float,
    ) -> tuple[bool, str, object | None]: ...

    def get_positions(self, symbol: str | None = None) -> list: ...


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TradingEngine:
    """
    Main evaluation loop.

    Call evaluate_symbol() once per candle close for each approved symbol.
    The method is designed to be called from a scheduler or replay runner.

    State is persisted to SQLite after every transition (R73).
    All decisions are logged before order submission (IMPL2).
    """

    def __init__(
        self,
        settings: AppSettings,
        market_data: MarketDataProtocol,
        db_session_factory,          # callable → Session
        executor: ExecutionGatewayProtocol,
        now_fn=None,                 # injected clock for determinism
        git_commit: str | None = None,
        spec_hash: str | None = None,
    ) -> None:
        if settings.execution_mode == "live":
            raise ValueError("Live trading is permanently disabled (IMPL7, R88)")

        self._settings = settings
        self._market_data = market_data
        self._db_factory = db_session_factory
        self._executor = executor
        self._now_fn = now_fn or (lambda: datetime.now(tz=timezone.utc))
        self._git_commit = git_commit or "unknown"
        self._spec_hash = spec_hash or SPEC_HASH_PLACEHOLDER

        s = settings.strategy
        r = settings.risk

        # Per-symbol detectors (re-used across evaluations)
        self._symbol_specs: dict[str, SymbolInfo] = {}
        self._fvg_detectors: dict[str, FVGDetector] = {}
        self._swing_detectors: dict[str, SwingDetector] = {}
        self._gap_exit_checkers: dict[str, GapExitChecker] = {}

        self._sweep_detector = LiquiditySweepDetector()
        self._expiry_checker = SetupExpiryChecker(
            max_fvg_age_bars=s.max_fvg_age_bars,
            max_setup_age_bars_after_sweep=s.max_setup_age_bars_after_sweep,
        )
        self._risk_engine = RiskEngine(
            settings=r,
            account_label=settings.execution_mode,
        )

    # ── Public ────────────────────────────────────────────────────────────────

    def initialise_symbols(self) -> dict[str, bool]:
        """
        R4: Discover and validate broker symbol specs at startup.
        Returns {symbol: ok} mapping.
        """
        results = {}
        for base_symbol in self._settings.strategy.symbols:
            ok, info = self._resolve_symbol(base_symbol)
            if ok and info is not None:
                self._symbol_specs[base_symbol] = info
                s = self._settings.strategy
                self._fvg_detectors[base_symbol] = FVGDetector(
                    symbol=base_symbol,
                    timeframe=s.timeframe,
                    atr_period=s.atr_period,
                    min_fvg_atr_factor=s.min_fvg_atr_factor,
                    min_fvg_ticks=s.min_fvg_ticks,
                    tick_size=info.tick_size,
                )
                self._swing_detectors[base_symbol] = SwingDetector(
                    left_bars=s.pivot_left_bars,
                    right_bars=s.pivot_right_bars,
                )
                self._gap_exit_checkers[base_symbol] = GapExitChecker(
                    mode=s.gap_exit_mode,
                )
                log.info("symbol_initialised", symbol=base_symbol,
                         digits=info.digits, tick_size=info.tick_size,
                         volume_min=info.volume_min, spread=info.spread)
            else:
                log.error("symbol_init_failed", symbol=base_symbol)
            results[base_symbol] = ok
        return results

    def evaluate_symbol(self, symbol: str, now: datetime | None = None) -> EvaluationResult:
        """
        Run one full evaluation cycle for a symbol.

        This is the deterministic core: same candles + same config → same result.
        """
        if now is None:
            now = self._now_fn()

        result = EvaluationResult(
            symbol=symbol, timestamp=now,
            candles_evaluated=0, new_fvgs=0,
            setups_advanced=0, signals_generated=0,
            orders_submitted=0, orders_rejected=0,
        )

        if symbol not in self._symbol_specs:
            result.errors.append(f"Symbol {symbol} not initialised (R1, R4)")
            return result

        info = self._symbol_specs[symbol]
        db: Session = self._db_factory()

        try:
            # ── 1. Fetch completed candles (R3) ───────────────────────────────
            try:
                candles = self._market_data.get_candles(
                    symbol, self._settings.strategy.timeframe, CANDLE_LOOKBACK
                )
            except Exception as exc:
                result.errors.append(f"Candle fetch failed: {exc}")
                log.error("candle_fetch_failed", symbol=symbol, exc=str(exc))
                return result

            if len(candles) < 20:
                result.errors.append(f"Insufficient candles: {len(candles)}")
                return result

            result.candles_evaluated = len(candles)

            # ── 2. Account info ───────────────────────────────────────────────
            account = self._market_data.get_account_info()
            equity = account["equity"] if account else None
            tick = self._market_data.get_tick(symbol)

            # ── 3. Detect new FVGs (R5, R6, R7, R8) ──────────────────────────
            repo = SetupRepository(db)
            all_setups = repo.get_all(symbol=symbol, limit=1000)
            known_fvg_ids = {s.id for s in all_setups}

            fvg_det = self._fvg_detectors[symbol]
            new_fvgs = fvg_det.find_new_fvgs(candles, known_fvg_ids, now=now)

            for fvg in new_fvgs:
                repo.create(setup_id=fvg.id, fvg=fvg, now=now)
                result.new_fvgs += 1
                log.info("fvg_detected", symbol=symbol, direction=fvg.direction,
                         fvg_low=fvg.fvg_low, fvg_high=fvg.fvg_high)

            # ── 4. Advance all active setups ──────────────────────────────────
            active_setups = repo.get_active(symbol=symbol)
            swing_det = self._swing_detectors[symbol]
            all_swings = swing_det.find_swings(candles)
            gap_checker = self._gap_exit_checkers[symbol]

            for setup_row in active_setups:
                machine = SetupStateMachine(setup_row, db)
                advanced = self._advance_setup(
                    machine=machine,
                    candles=candles,
                    all_swings=all_swings,
                    gap_checker=gap_checker,
                    info=info,
                    equity=equity,
                    tick=tick,
                    now=now,
                    db=db,
                    result=result,
                )
                if advanced:
                    result.setups_advanced += 1

        finally:
            db.close()

        return result

    # ── Private: setup lifecycle ──────────────────────────────────────────────

    def _advance_setup(
        self,
        machine: SetupStateMachine,
        candles: list[Candle],
        all_swings,
        gap_checker: GapExitChecker,
        info: SymbolInfo,
        equity: float | None,
        tick: dict | None,
        now: datetime,
        db: Session,
        result: EvaluationResult,
    ) -> bool:
        """Step the setup state machine forward as far as possible on this candle."""
        setup = machine.setup
        symbol = setup.symbol
        s = self._settings.strategy
        r = self._settings.risk

        # ── Check expiry / invalidation on latest candle ──────────────────────
        if candles:
            last = candles[-1]
            # Reconstruct FVG object from ORM row for checker
            fvg = self._fvg_from_row(setup)
            sweep = self._sweep_from_row(setup)

            expired, exp_reason = self._expiry_checker.check_expiry(fvg, sweep, candles)
            if expired:
                machine.expire(exp_reason, now)
                self._journal(db, "EXPIRED", setup, notes=exp_reason)
                return True

            invalid, inv_reason = self._expiry_checker.check_invalidation(fvg, sweep, last)
            if invalid:
                machine.invalidate(inv_reason, now)
                self._journal(db, "INVALIDATED", setup, notes=inv_reason)
                return True

        state = machine.state

        # ── FVG_DETECTED → wait for sweep ────────────────────────────────────
        if state == SetupState.FVG_DETECTED:
            fvg = self._fvg_from_row(setup)
            sweeps = self._sweep_detector.find_sweeps_for_fvg(fvg, candles, all_swings)
            if sweeps:
                sweep = sweeps[-1]   # most recent qualifying sweep
                machine.confirm_sweep(sweep, now)
                machine.begin_retracement_watch(now)
                return True

        # ── WAITING_FOR_RETRACEMENT → find reference candle ──────────────────
        elif state == SetupState.WAITING_FOR_RETRACEMENT:
            fvg = self._fvg_from_row(setup)
            sweep = self._sweep_from_row(setup)
            if sweep is None:
                return False
            # Only candles after the sweep candle are retracement candidates
            retrace_candles = [
                c for c in candles if c.time > sweep.sweep_candle.time
            ]
            ref = ReferenceCandleSelector.find_reference_candle(fvg, retrace_candles)
            if ref is not None:
                machine.save_reference_candle(ref, now)
                return True

        # ── REFERENCE_CANDLE_SAVED → update ref OR confirm gap exit ──────────
        elif state == SetupState.REFERENCE_CANDLE_SAVED:
            fvg = self._fvg_from_row(setup)
            sweep = self._sweep_from_row(setup)
            if sweep is None:
                return False
            retrace_candles = [
                c for c in candles if c.time > sweep.sweep_candle.time
            ]
            # Check if gap has been exited
            last = candles[-1] if candles else None
            if last and gap_checker.is_gap_exited(fvg, last):
                machine.confirm_gap_exit(now)
                machine.confirm_ready_to_trigger(now)
                return True
            # Otherwise update reference candle to most recent qualifying
            ref = ReferenceCandleSelector.find_reference_candle(fvg, retrace_candles)
            if ref is not None:
                existing_time = setup.ref_candle_time
                if ref.candle.time != existing_time:
                    machine.update_reference_candle(ref, now)
                    return True

        # ── WAITING_FOR_GAP_EXIT / GAP_EXITED → handled in state machine ─────
        elif state == SetupState.WAITING_FOR_GAP_EXIT:
            fvg = self._fvg_from_row(setup)
            last = candles[-1] if candles else None
            if last and gap_checker.is_gap_exited(fvg, last):
                machine.confirm_gap_exit(now)
                machine.confirm_ready_to_trigger(now)
                return True

        # ── WAITING_FOR_TRIGGER → check entry trigger ─────────────────────────
        elif state == SetupState.WAITING_FOR_TRIGGER:
            if setup.trigger_level is None or setup.ref_candle_high is None:
                return False

            fvg = self._fvg_from_row(setup)
            ref = self._ref_from_row(setup)
            last = candles[-1] if candles else None
            triggered = False

            if s.entry_trigger_mode == "CANDLE_CLOSE" and last:
                triggered = EntryTriggerChecker.check_candle_close(fvg, ref, last)
            elif s.entry_trigger_mode == "TICK_BREAK" and tick:
                triggered, _ = EntryTriggerChecker.check_tick_break(
                    fvg, ref,
                    bid=tick["bid"], ask=tick["ask"],
                    tick_time=tick["time"],
                    max_tick_age_seconds=s.max_tick_age_seconds,
                    now=now,
                )

            if triggered:
                if equity is None:
                    machine.invalidate("Cannot get equity for signal", now)
                    return True
                sl_calc = self._make_sl_calc(info, s)
                tp_calc = TakeProfitCalculator(
                    min_rr=r.min_reward_to_risk,
                    tick_size=info.tick_size,
                )
                sweep = self._sweep_from_row(setup)
                if sweep is None:
                    machine.invalidate("Sweep missing at trigger", now)
                    return True

                entry_price = tick["ask"] if fvg.direction == "BULLISH" else tick["bid"]
                if entry_price is None:
                    entry_price = last.close if last else 0.0

                sl, sl_reason = sl_calc.calculate(fvg, sweep, entry_price, candles)
                if sl is None:
                    # B5/B6 fix: invalidate cleanly from WAITING_FOR_TRIGGER state
                    machine.invalidate(f"SL calculation failed: {sl_reason}", now)
                    self._journal(db, "REJECTION", setup, notes=sl_reason)
                    result.orders_rejected += 1
                    return True

                tp, rr, tp_reason = tp_calc.calculate(fvg, entry_price, sl)
                if tp is None:
                    machine.invalidate(f"TP/R:R check failed: {tp_reason}", now)
                    result.orders_rejected += 1
                    return True

                # Sizing
                sizing = self._risk_engine.calculate_size(
                    symbol_info=info,
                    direction=fvg.direction,
                    entry_price=entry_price,
                    sl_price=sl,
                    equity=equity,
                )
                if not sizing.approved:
                    machine.invalidate(
                        f"Position sizing rejected: {sizing.rejection_reason}", now
                    )
                    result.orders_rejected += 1
                    return True

                machine.signal_ready(
                    proposed_entry=entry_price,
                    proposed_sl=sl,
                    proposed_tp=tp,
                    proposed_volume=sizing.volume,
                    estimated_risk_usd=sizing.risk_usd,
                    estimated_rr=rr,
                    timestamp=now,
                )
                result.signals_generated += 1
                return True

        # ── SIGNAL_READY → risk check → submit ────────────────────────────────
        elif state == SetupState.SIGNAL_READY:
            machine.begin_risk_check(now)
            today = now.date()
            daily_check = self._risk_engine.check_daily_limits(
                db=db,
                symbol=symbol,
                sizing=SizingResult(
                    approved=True,
                    volume=setup.proposed_volume or 0,
                    risk_usd=setup.estimated_risk_usd or 0,
                    reward_usd=0, rr_ratio=0,
                    sl_distance_pips=0, tp_distance_pips=0,
                ),
                current_equity=equity or 0,
                today=today,
            )
            if not daily_check.approved:
                machine.risk_rejected(daily_check.rejection_reason, now)
                self._write_decision_log(db, setup, "REJECTED",
                                         daily_check.rejection_reason,
                                         equity, tick, now)
                result.orders_rejected += 1
                return True

            # Late-entry guard (R33)
            if tick and setup.trigger_level is not None:
                fvg = self._fvg_from_row(setup)
                atr_val = compute_atr(candles, self._settings.strategy.atr_period)
                if atr_val:
                    guard = self._settings.strategy.late_entry_atr_factor * atr_val
                    entry_px = tick["ask"] if fvg.direction == "BULLISH" else tick["bid"]
                    if fvg.direction == "BULLISH" and entry_px > setup.trigger_level + guard:
                        reason = (f"Late-entry guard: ask {entry_px:.5f} > "
                                  f"trigger {setup.trigger_level:.5f} + {guard:.5f} (R33)")
                        machine.risk_rejected(reason, now)
                        result.orders_rejected += 1
                        return True
                    elif fvg.direction == "BEARISH" and entry_px < setup.trigger_level - guard:
                        reason = (f"Late-entry guard: bid {entry_px:.5f} < "
                                  f"trigger {setup.trigger_level:.5f} - {guard:.5f} (R33)")
                        machine.risk_rejected(reason, now)
                        result.orders_rejected += 1
                        return True

            machine.risk_approved(now)

            # Submit order
            if self._settings.execution_mode == "paper":
                ask = tick["ask"] if tick else (setup.proposed_entry or 0)
                bid = tick["bid"] if tick else (setup.proposed_entry or 0)
                ok, msg, pos = self._executor.submit_order(
                    setup_id=setup.id,
                    symbol=symbol,
                    direction=setup.direction.value,
                    volume=setup.proposed_volume,
                    entry_price=setup.proposed_entry,
                    sl=setup.proposed_sl,
                    tp=setup.proposed_tp,
                    current_ask=ask,
                    current_bid=bid,
                )
                if ok:
                    # Record order in DB
                    order = Order(
                        id=order_client_id(setup.id, attempt=0),
                        setup_id=setup.id,
                        symbol=symbol,
                        direction=setup.direction.value,
                        execution_mode=self._settings.execution_mode,
                        requested_at=now,
                        requested_volume=setup.proposed_volume,
                        requested_entry=setup.proposed_entry,
                        requested_sl=setup.proposed_sl,
                        requested_tp=setup.proposed_tp,
                        client_order_id=order_client_id(setup.id, 0),
                        filled_at=now,
                        filled_price=setup.proposed_entry,
                        filled_volume=setup.proposed_volume,
                        is_paper=True,
                        sl_confirmed_by_broker=True,   # paper: always confirmed
                        status="FILLED",
                        spec_version=SPEC_VERSION,
                        spec_hash=self._spec_hash,
                    )
                    db.add(order)
                    db.commit()
                    machine.position_opened(now)
                    self._risk_engine.record_new_entry(db, symbol, today)
                    self._journal(db, "FILL", setup,
                                  price=setup.proposed_entry,
                                  volume=setup.proposed_volume,
                                  sl=setup.proposed_sl,
                                  tp=setup.proposed_tp,
                                  notes=msg)
                    self._write_decision_log(db, setup, "SIGNAL",
                                             "Order filled (paper)", equity, tick, now)
                    result.orders_submitted += 1
                else:
                    machine.risk_rejected(msg, now)
                    result.orders_rejected += 1
                return True

        return False

    # ── Private helpers ────────────────────────────────────────────────────────

    def _resolve_symbol(self, base: str) -> tuple[bool, SymbolInfo | None]:
        """R4: try exact match, then suffix-tolerant match."""
        info = self._market_data.get_symbol_info(base)
        if info is not None:
            return True, info
        available = self._market_data.get_available_symbols()
        for sym in available:
            if sym.startswith(base):
                info = self._market_data.get_symbol_info(sym)
                if info and info.tick_size > 0 and info.volume_step > 0:
                    log.info("symbol_resolved_with_suffix",
                             base=base, resolved=sym)
                    return True, info
        return False, None

    @staticmethod
    def _ensure_utc(dt: datetime | None) -> datetime:
        if dt is None:
            return datetime.now(tz=timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _fvg_from_row(self, setup: Setup) -> FVG:
        """
        Reconstruct a FVG object from an ORM Setup row.
        Uses the individually stored C1/C3 values (B3 fix — R11, R66–R68).
        """
        return FVG(
            id=setup.id,
            symbol=setup.symbol,
            timeframe=setup.timeframe,
            direction=setup.direction.value,
            fvg_low=setup.fvg_low,
            fvg_high=setup.fvg_high,
            c1_time=self._ensure_utc(setup.fvg_c1_time),
            c3_time=self._ensure_utc(setup.fvg_c3_time),
            c1_high=setup.fvg_c1_high or setup.fvg_high,
            c1_low=setup.fvg_c1_low or setup.fvg_low,
            c3_high=setup.fvg_c3_high or setup.fvg_high,
            c3_low=setup.fvg_c3_low or setup.fvg_low,
            atr_at_detection=setup.fvg_atr_at_detection or 0.0,
            created_at=self._ensure_utc(setup.created_at),
        )

    def _sweep_from_row(self, setup: Setup) -> LiquiditySweep | None:
        """
        Reconstruct a minimal LiquiditySweep from persisted ORM fields.

        B4 fix: dummy Candle values must satisfy OHLC invariants so that
        Candle.__post_init__ does not raise.  The only fields actually used
        downstream are sweep_candle.time and sweep_extreme, so we build the
        candle to be a single-pip doji around sweep_extreme.
        """
        if setup.sweep_level is None or setup.sweep_candle_time is None:
            return None

        extreme = setup.sweep_extreme if setup.sweep_extreme is not None else setup.sweep_level
        direction = setup.direction.value  # "BULLISH" or "BEARISH"

        # Build a minimal valid candle that contains sweep_extreme in its range
        if direction == "BULLISH":
            # sweep_extreme is the candle LOW (wick below swing low)
            lo = extreme
            hi = max(extreme + 0.01, setup.sweep_level + 0.01)
        else:
            # sweep_extreme is the candle HIGH (wick above swing high)
            hi = extreme
            lo = min(extreme - 0.01, setup.sweep_level - 0.01)

        mid = (lo + hi) / 2
        sweep_ts = self._ensure_utc(setup.sweep_candle_time)
        dummy_candle = Candle(
            time=sweep_ts,
            open=mid, high=hi, low=lo, close=mid,
            volume=0.0,
            symbol=setup.symbol,
            timeframe=setup.timeframe,
        )
        dummy_swing = Swing(
            candle=dummy_candle,
            level=setup.sweep_level,
            direction="LOW" if direction == "BULLISH" else "HIGH",
            confirmed_at=sweep_ts,
        )
        return LiquiditySweep(
            swing=dummy_swing,
            sweep_candle=dummy_candle,
            direction=direction,
            swept_level=setup.sweep_level,
            sweep_extreme=extreme,
        )

    def _ref_from_row(self, setup: Setup) -> ReferenceCandle:
        """
        Reconstruct a ReferenceCandle from persisted ORM fields.
        Only call this when ref_candle_time is not None.
        """
        if setup.ref_candle_time is None:
            raise ValueError(
                f"Setup {setup.id} has no reference candle — "
                "do not call _ref_from_row before REFERENCE_CANDLE_SAVED state"
            )
        # Guard against partially-written rows producing invalid OHLC
        hi = setup.ref_candle_high or 0.01
        lo = setup.ref_candle_low or 0.0
        op = setup.ref_candle_open or lo
        cl = setup.ref_candle_close or lo
        # Ensure OHLC invariants hold — clamp if storage corruption
        hi = max(hi, lo, op, cl)
        lo = min(lo, op, cl)
        c = Candle(
            time=self._ensure_utc(setup.ref_candle_time),
            open=op,
            high=hi,
            low=lo,
            close=cl,
            volume=0.0,
            symbol=setup.symbol,
            timeframe=setup.timeframe,
        )
        return ReferenceCandle(candle=c, frozen=setup.ref_candle_frozen)

    def _make_sl_calc(self, info: SymbolInfo, s) -> StopLossCalculator:
        r = self._settings.risk
        return StopLossCalculator(
            atr_period=s.atr_period,
            sl_buffer_atr_factor=r.sl_buffer_atr_factor,
            sl_buffer_min_ticks=r.sl_buffer_min_ticks,
            tick_size=info.tick_size,
            trade_stops_level=info.trade_stops_level,
            point=info.point,
        )

    def _journal(
        self, db: Session, event_type: str, setup: Setup,
        price: float | None = None,
        volume: float | None = None,
        sl: float | None = None,
        tp: float | None = None,
        notes: str | None = None,
    ) -> None:
        entry = JournalEntry(
            timestamp=self._now_fn(),
            event_type=event_type,
            setup_id=setup.id,
            symbol=setup.symbol,
            direction=setup.direction.value,
            execution_mode=self._settings.execution_mode,
            price=price,
            volume=volume,
            sl=sl,
            tp=tp,
            notes=notes,
        )
        db.add(entry)
        db.commit()

    def _write_decision_log(
        self,
        db: Session,
        setup: Setup,
        decision: str,
        reason: str,
        equity: float | None,
        tick: dict | None,
        now: datetime,
    ) -> None:
        log_row = DecisionLog(
            created_at=now,
            spec_version=SPEC_VERSION,
            spec_hash=self._spec_hash,
            git_commit=self._git_commit,
            symbol=setup.symbol,
            timeframe=setup.timeframe,
            setup_id=setup.id,
            prev_state=None,
            new_state=setup.state.value,
            rules_evaluated=json.dumps([
                "R32", "R33", "R44", "R50", "R54", "R58", "R59"
            ]),
            rule_results=None,
            final_decision=decision,
            decision_reason=reason,
            spread_at_decision=(
                (tick["ask"] - tick["bid"]) / (self._symbol_specs.get(setup.symbol, None).point or 0.01)
                if tick and self._symbol_specs.get(setup.symbol) else None
            ),
            quote_timestamp=tick["time"] if tick else None,
            equity_at_decision=equity,
        )
        db.add(log_row)
        db.commit()
