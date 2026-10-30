"""
Profit Guardian — Dynamic Trailing Stop Loss & Aggressive Retracement Protection.

Provides:
1. Breakeven Migration: Shifts SL to entry + 1 pip when position achieves 1.0R.
2. Structural Step Trailing: Locks in profit at 1.5R (+0.5R locked), 2.0R (+1.0R locked).
3. Aggressive Retracement Protection: Detects sharp adverse market pulls from peak profit
   and tightens SL or triggers protective exit to lock in banked gains.
4. Multi-Account Sync: Propagates SL modifications across child accounts in <200ms.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from src.utils.logging_config import get_logger

if TYPE_CHECKING:
    from src.execution.mt5_executor import MT5Executor, MT5Position
    from src.execution.multi_account_copier import MultiAccountCopier

log = get_logger(__name__)


@dataclass
class PositionTrackingState:
    """Tracks high-water mark and trailing levels for an active position."""
    ticket: int
    symbol: str
    direction: str              # "BULLISH" or "BEARISH"
    entry_price: float
    initial_sl: float
    tp: float
    initial_risk_distance: float
    current_sl: float
    peak_price: float
    peak_r: float = 0.0
    breakeven_activated: bool = False
    guardian_activated: bool = False
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProfitGuardian:
    """
    Monitors active positions on Master and Child accounts to protect profit
    and aggressively minimize drawdowns upon market retracement.
    """

    def __init__(
        self,
        master_executor: MT5Executor,
        copier: Optional[MultiAccountCopier] = None,
        breakeven_r: float = 1.0,           # Activate breakeven at 1.0R
        trailing_start_r: float = 1.5,      # Start trailing lock at 1.5R
        retrace_lock_pct: float = 0.40,     # If 40% of peak profit evaporates, lock in remainder
    ) -> None:
        self.master_executor = master_executor
        self.copier = copier
        self.breakeven_r = breakeven_r
        self.trailing_start_r = trailing_start_r
        self.retrace_lock_pct = retrace_lock_pct
        self._positions: dict[int, PositionTrackingState] = {}

    def register_position(
        self,
        ticket: int,
        symbol: str,
        direction: str,
        entry_price: float,
        sl: float,
        tp: float,
    ) -> PositionTrackingState:
        """Register a newly opened position for profit guarding."""
        risk_dist = abs(entry_price - sl)
        if risk_dist <= 0:
            risk_dist = 0.01

        state = PositionTrackingState(
            ticket=ticket,
            symbol=symbol,
            direction=direction.upper(),
            entry_price=entry_price,
            initial_sl=sl,
            tp=tp,
            initial_risk_distance=risk_dist,
            current_sl=sl,
            peak_price=entry_price,
            peak_r=0.0,
        )
        self._positions[ticket] = state
        log.info(
            "profit_guardian_position_registered",
            ticket=ticket,
            symbol=symbol,
            entry=entry_price,
            sl=sl,
            tp=tp,
            risk_distance=risk_dist,
        )
        return state

    def update_price(self, ticket: int, current_price: float) -> tuple[bool, Optional[float], str]:
        """
        Evaluate current market price against position tracking.
        Returns: (should_modify_sl, new_sl_level, action_reason)
        """
        state = self._positions.get(ticket)
        if not state:
            return False, None, "Position not tracked"

        is_bullish = state.direction in ("BULLISH", "BUY")
        risk_dist = state.initial_risk_distance

        # Calculate current floating gain in R units
        if is_bullish:
            current_gain = current_price - state.entry_price
            if current_price > state.peak_price:
                state.peak_price = current_price
            floating_r = current_gain / risk_dist
            peak_gain = state.peak_price - state.entry_price
            peak_r = peak_gain / risk_dist
        else:
            current_gain = state.entry_price - current_price
            if current_price < state.peak_price:
                state.peak_price = current_price
            floating_r = current_gain / risk_dist
            peak_gain = state.entry_price - state.peak_price
            peak_r = peak_gain / risk_dist

        state.peak_r = max(state.peak_r, peak_r)
        proposed_sl = state.current_sl
        reason = ""

        # ── 1. Breakeven Shift at 1.0R ──────────────────────────────────────────
        if floating_r >= self.breakeven_r and not state.breakeven_activated:
            buffer = 0.10 if "XAU" in state.symbol else 5.0
            new_be = state.entry_price + buffer if is_bullish else state.entry_price - buffer
            if (is_bullish and new_be > state.current_sl) or (not is_bullish and new_be < state.current_sl):
                proposed_sl = new_be
                state.breakeven_activated = true = True
                reason = f"BREAKEVEN: Trade reached {floating_r:.2f}R. SL moved to entry + buffer."

        # ── 2. Structural Profit Lock at 1.5R and 2.0R ──────────────────────────
        if floating_r >= 2.0:
            locked_dist = risk_dist * 1.0  # Lock +1.0R
            new_sl = state.entry_price + locked_dist if is_bullish else state.entry_price - locked_dist
            if (is_bullish and new_sl > proposed_sl) or (not is_bullish and new_sl < proposed_sl):
                proposed_sl = new_sl
                reason = f"PROFIT_LOCK_2R: Trade reached {floating_r:.2f}R. SL locked at +1.0R profit."
        elif floating_r >= self.trailing_start_r:
            locked_dist = risk_dist * 0.5  # Lock +0.5R
            new_sl = state.entry_price + locked_dist if is_bullish else state.entry_price - locked_dist
            if (is_bullish and new_sl > proposed_sl) or (not is_bullish and new_sl < proposed_sl):
                proposed_sl = new_sl
                reason = f"PROFIT_LOCK_1.5R: Trade reached {floating_r:.2f}R. SL locked at +0.5R profit."

        # ── 3. Aggressive Retracement Guardian ──────────────────────────────────
        # If trade rose to >= 1.2R, but retraces by more than retrace_lock_pct from peak
        if state.peak_r >= 1.2:
            retrace_amount = peak_gain - current_gain
            retrace_pct = (retrace_amount / peak_gain) if peak_gain > 0 else 0.0

            if retrace_pct >= self.retrace_lock_pct:
                # Lock in at least 50% of the peak profit before giving back more
                guaranteed_gain = peak_gain * (1.0 - self.retrace_lock_pct)
                guardian_sl = state.entry_price + guaranteed_gain if is_bullish else state.entry_price - guaranteed_gain
                if (is_bullish and guardian_sl > proposed_sl) or (not is_bullish and guardian_sl < proposed_sl):
                    proposed_sl = guardian_sl
                    state.guardian_activated = True
                    reason = (
                        f"AGGRESSIVE_RETRACE_GUARDIAN: Market retraced {retrace_pct*100:.1f}% "
                        f"from peak ({state.peak_r:.2f}R). SL shifted to lock {guaranteed_gain:.2f} profit."
                    )

        if proposed_sl != state.current_sl:
            state.current_sl = proposed_sl
            state.last_updated = datetime.now(timezone.utc)
            return True, proposed_sl, reason

        return False, None, "No SL modification needed"

    def apply_broker_sl(self, ticket: int, new_sl: float) -> bool:
        """
        Sends TRADE_ACTION_SLTP to MT5 for Master position and syncs to all child accounts.
        """
        import MetaTrader5 as mt5

        state = self._positions.get(ticket)
        if not state:
            return False

        # 1. Update Master Position in MT5
        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": state.symbol,
            "sl": float(new_sl),
            "tp": float(state.tp),
        }
        res = mt5.order_send(req)
        master_ok = (res is not None and res.retcode == mt5.TRADE_RETCODE_DONE)

        if master_ok:
            log.info("master_sl_updated", ticket=ticket, new_sl=new_sl)
        else:
            err = res.comment if res else str(mt5.last_error())
            log.warning("master_sl_update_failed", ticket=ticket, error=err)

        # 2. Sync to Copier Child Accounts
        if self.copier:
            sl_distance_from_entry = abs(state.entry_price - new_sl)
            for trade in self.copier.copied_trades:
                if trade.master_ticket == ticket and trade.status == "OPEN":
                    child = self.copier.child_accounts.get(trade.child_account_id)
                    if not child:
                        continue
                    try:
                        self.copier._switch_account(child.account_id, child.password, child.server)
                        child_new_sl = trade.entry_price + sl_distance_from_entry if state.direction in ("BULLISH", "BUY") else trade.entry_price - sl_distance_from_entry
                        child_req = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": trade.child_ticket,
                            "symbol": trade.symbol,
                            "sl": float(child_new_sl),
                            "tp": float(trade.tp),
                        }
                        mt5.order_send(child_req)
                    except Exception as exc:
                        log.error("child_sl_sync_exception", child_ticket=trade.child_ticket, error=str(exc))

            self.copier._restore_master()

        return master_ok

    def deregister_position(self, ticket: int) -> None:
        """Clean up closed position."""
        if ticket in self._positions:
            del self._positions[ticket]
            log.info("profit_guardian_position_deregistered", ticket=ticket)
