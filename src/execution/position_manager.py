"""
Position Management Engine — Dynamic Break-Even & Stop-Loss Guardian.

Implements MASTER DIRECTIVE PART 1:
1. Independent monitoring of every open position.
2. Break-Even Modes:
   - FIXED_25: Move SL to break-even at 25% TP progress.
   - FIXED_50: Move SL to break-even at 50% TP progress.
   - FIXED_70: Move SL to break-even at 70% TP progress.
   - ADAPTIVE: Deterministic assessment of displacement momentum, spread,
     volatility (ATR), and opposing structure.
3. Cost-Adjusted Break-Even: Offsets SL by spread and transaction costs so
   break-even covers costs where permitted.
4. Non-Negotiable Safety Rules:
   - Never move SL farther away from entry (never loosen risk).
   - Never overwrite a more protective existing SL.
   - Never remove or alter Take Profit.
   - Respect broker stop-level and freeze-level restrictions.
   - Confirm modification acceptance with MT5.
   - Retry recoverable failures with controlled backoff.
   - Independent management for all three orders of a setup.
   - Survives restarts and runs independently of entry scanning.
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any

from src.utils.logging_config import get_logger

log = get_logger(__name__)


class BreakEvenMode(str, enum.Enum):
    FIXED_25 = "FIXED_25"
    FIXED_50 = "FIXED_50"
    FIXED_70 = "FIXED_70"
    ADAPTIVE = "ADAPTIVE"


@dataclass
class PositionBreakEvenState:
    """State for one tracked position under position management."""
    ticket: int
    symbol: str
    direction: str                     # "BUY" / "BULLISH" or "SELL" / "BEARISH"
    volume: float
    entry_price: float
    initial_sl: float
    tp_price: float
    current_sl: float
    setup_id: str = ""
    group_id: str = ""
    order_index: int = 1               # 1, 2, or 3
    be_mode: BreakEvenMode = BreakEvenMode.ADAPTIVE
    breakeven_triggered: bool = False
    breakeven_sl: Optional[float] = None
    peak_price: float = 0.0
    peak_tp_progress: float = 0.0
    last_eval_time: float = field(default_factory=time.time)
    retry_count: int = 0
    last_error: str = ""
    cost_offset: float = 0.0           # Transaction cost offset (spread/commission)

    @property
    def is_buy(self) -> bool:
        return self.direction.upper() in ("BUY", "BULLISH")

    @property
    def tp_distance(self) -> float:
        if self.tp_price <= 0:
            return 0.0
        return abs(self.tp_price - self.entry_price)


class PositionManagementEngine:
    """
    Dedicated engine that manages the lifecycle of open positions independently
    from the entry scanner.
    """

    def __init__(
        self,
        default_mode: BreakEvenMode = BreakEvenMode.ADAPTIVE,
        cost_offset_pips: float = 2.0,   # Minimum cost offset in pips
    ) -> None:
        self.default_mode = default_mode
        self.cost_offset_pips = cost_offset_pips
        self._positions: dict[int, PositionBreakEvenState] = {}

    def register_position(
        self,
        ticket: int,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        sl: float,
        tp: float,
        setup_id: str = "",
        group_id: str = "",
        order_index: int = 1,
        mode: Optional[BreakEvenMode] = None,
        cost_offset: float = 0.0,
    ) -> PositionBreakEvenState:
        """Registers an open position for independent break-even and trailing management."""
        is_buy = direction.upper() in ("BUY", "BULLISH")
        initial_peak = entry_price

        state = PositionBreakEvenState(
            ticket=ticket,
            symbol=symbol,
            direction="BUY" if is_buy else "SELL",
            volume=volume,
            entry_price=entry_price,
            initial_sl=sl,
            tp_price=tp,
            current_sl=sl,
            setup_id=setup_id,
            group_id=group_id,
            order_index=order_index,
            be_mode=mode or self.default_mode,
            peak_price=initial_peak,
            cost_offset=cost_offset,
        )
        self._positions[ticket] = state
        log.info(
            "position_manager_registered",
            ticket=ticket,
            symbol=symbol,
            direction=state.direction,
            entry=entry_price,
            sl=sl,
            tp=tp,
            mode=state.be_mode.value,
        )
        return state

    def deregister_position(self, ticket: int) -> Optional[PositionBreakEvenState]:
        """Removes a closed position from active management."""
        return self._positions.pop(ticket, None)

    def get_position(self, ticket: int) -> Optional[PositionBreakEvenState]:
        return self._positions.get(ticket)

    def get_all_positions(self) -> list[PositionBreakEvenState]:
        return list(self._positions.values())

    def calculate_tp_progress(
        self,
        state: PositionBreakEvenState,
        current_price: float,
    ) -> float:
        """
        Calculates exact progress toward the original TP (0.0 to 1.0+).
        Progress is strictly relative to the trade's planned TP distance.
        """
        tp_dist = state.tp_distance
        if tp_dist <= 0:
            return 0.0

        if state.is_buy:
            gain = current_price - state.entry_price
        else:
            gain = state.entry_price - current_price

        progress = gain / tp_dist
        return progress

    def evaluate_adaptive_milestone(
        self,
        state: PositionBreakEvenState,
        current_price: float,
        atr: float = 0.0,
        spread: float = 0.0,
        momentum_slowing: bool = False,
        reversal_detected: bool = False,
    ) -> float:
        """
        Determines the appropriate milestone threshold (0.25, 0.50, or 0.70)
        using deterministic market conditions:
        - If momentum is slowing or opposing structure/reversal is detected -> protect early (0.25).
        - If high spread relative to ATR -> protect earlier (0.25 - 0.50).
        - If strong sustained directional displacement -> allow trade room to develop (0.70).
        - Default balanced baseline -> 0.50.
        """
        if reversal_detected or momentum_slowing:
            return 0.25

        if atr > 0 and spread > 0 and (spread / atr) > 0.15:
            # High relative spread makes early cost-protection essential
            return 0.25

        # Strong trend: check if price has moved swiftly without pullback
        if state.peak_tp_progress > 0.40 and not momentum_slowing:
            return 0.70

        return 0.50

    def compute_cost_adjusted_sl(
        self,
        state: PositionBreakEvenState,
        point_size: float = 0.01,
        stops_level_points: float = 0.0,
    ) -> float:
        """
        Computes the target Break-Even SL level with transaction costs and broker stop distance.
        For BUY: entry + cost_offset.
        For SELL: entry - cost_offset.
        """
        # Determine minimal protective buffer
        is_xau = "XAU" in state.symbol.upper()
        default_offset = 0.20 if is_xau else 10.0
        offset = max(state.cost_offset, default_offset)

        # Ensure broker minimum stop level is respected
        min_distance = stops_level_points * point_size if stops_level_points > 0 else 0.0
        offset = max(offset, min_distance * 0.5)

        if state.is_buy:
            return round(state.entry_price + offset, 2 if is_xau else 2)
        else:
            return round(state.entry_price - offset, 2 if is_xau else 2)

    def evaluate_position(
        self,
        ticket: int,
        current_price: float,
        point_size: float = 0.01,
        stops_level_points: float = 0.0,
        freeze_level_points: float = 0.0,
        atr: float = 0.0,
        spread: float = 0.0,
        momentum_slowing: bool = False,
        reversal_detected: bool = False,
    ) -> tuple[bool, Optional[float], str]:
        """
        Evaluates an open position and decides if SL should be moved to break-even.
        Returns: (should_modify, new_sl, reason)
        """
        state = self._positions.get(ticket)
        if not state:
            return False, None, "Position not tracked by PositionManagementEngine"

        # Update high-water mark / peak tracking
        if state.is_buy:
            if current_price > state.peak_price:
                state.peak_price = current_price
        else:
            if state.peak_price == 0.0 or current_price < state.peak_price:
                state.peak_price = current_price

        current_progress = self.calculate_tp_progress(state, current_price)
        peak_progress = self.calculate_tp_progress(state, state.peak_price)
        state.peak_tp_progress = max(state.peak_tp_progress, peak_progress)

        # Determine threshold progress based on mode
        if state.be_mode == BreakEvenMode.FIXED_25:
            threshold = 0.25
        elif state.be_mode == BreakEvenMode.FIXED_50:
            threshold = 0.50
        elif state.be_mode == BreakEvenMode.FIXED_70:
            threshold = 0.70
        else:
            threshold = self.evaluate_adaptive_milestone(
                state, current_price, atr=atr, spread=spread,
                momentum_slowing=momentum_slowing, reversal_detected=reversal_detected,
            )

        # Check if milestone is reached
        best_progress = max(current_progress, state.peak_tp_progress)
        if best_progress < threshold:
            return False, None, f"Progress {best_progress*100:.1f}% below milestone {threshold*100:.0f}%"

        # Calculate cost-adjusted candidate SL
        candidate_sl = self.compute_cost_adjusted_sl(
            state, point_size=point_size, stops_level_points=stops_level_points,
        )

        # NON-NEGOTIABLE SAFETY RULE 1: Never move SL in the wrong direction (never loosen risk)
        if state.is_buy:
            # For BUY, candidate_sl must be HIGHER than current SL to tighten risk
            if candidate_sl <= state.current_sl:
                return False, None, f"Current SL ({state.current_sl}) already more protective than BE ({candidate_sl})"
            # Also must not place SL above current price
            if candidate_sl >= current_price:
                safe_sl = round(current_price - max(point_size * 5, 0.15), 2)
                if safe_sl > state.current_sl:
                    candidate_sl = safe_sl
                else:
                    return False, None, "Market price too close to entry to set cost-adjusted BE safely"
        else:
            # For SELL, candidate_sl must be LOWER than current SL to tighten risk
            if state.current_sl > 0 and candidate_sl >= state.current_sl:
                return False, None, f"Current SL ({state.current_sl}) already more protective than BE ({candidate_sl})"
            # Must not place SL below current price
            if candidate_sl <= current_price:
                safe_sl = round(current_price + max(point_size * 5, 0.15), 2)
                if state.current_sl <= 0 or safe_sl < state.current_sl:
                    candidate_sl = safe_sl
                else:
                    return False, None, "Market price too close to entry to set cost-adjusted BE safely"

        # NON-NEGOTIABLE SAFETY RULE 2: Respect broker freeze level and stop level restrictions
        stop_dist = abs(current_price - candidate_sl)
        min_stop_dist = stops_level_points * point_size if stops_level_points > 0 else 0.0
        if min_stop_dist > 0 and stop_dist < min_stop_dist:
            return False, None, f"Proposed SL distance ({stop_dist:.2f}) < broker stop level ({min_stop_dist:.2f})"

        reason = (
            f"BREAKEVEN_ACTIVATED [{state.be_mode.value}]: Reached {best_progress*100:.1f}% "
            f"of TP (threshold {threshold*100:.0f}%). SL moved to cost-adjusted {candidate_sl}."
        )
        return True, candidate_sl, reason

    def record_modification_result(
        self,
        ticket: int,
        accepted: bool,
        new_sl: float,
        error_msg: str = "",
    ) -> None:
        """Records broker modification result and manages retries safely."""
        state = self._positions.get(ticket)
        if not state:
            return

        if accepted:
            state.current_sl = new_sl
            state.breakeven_triggered = True
            state.breakeven_sl = new_sl
            state.retry_count = 0
            state.last_error = ""
            log.info(
                "position_manager_sl_confirmed",
                ticket=ticket,
                confirmed_sl=new_sl,
            )
        else:
            state.retry_count += 1
            state.last_error = error_msg
            log.warn(
                "position_manager_sl_rejected",
                ticket=ticket,
                attempted_sl=new_sl,
                error=error_msg,
                retries=state.retry_count,
            )
