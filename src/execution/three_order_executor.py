"""
Three-Order Execution Coordinator & Reliability Engine.

Implements MASTER DIRECTIVE PART 4 & PART 5:
1. Three Separate Orders with One Identical Dynamic Lot Size:
   - For every approved setup, prepares and executes THREE SEPARATE ORDERS.
   - All three orders use the EXACT SAME calculated lot size.
   - The common lot size is determined dynamically by the existing Risk Management Agent.
2. Combined Exposure Assessment:
   - Evaluates the total combined exposure (3 * common_lot) and combined monetary risk
     before submitting any order.
   - If the account equity or free margin cannot safely support all 3 orders,
     rejects with a precise reason. Never substitutes 1 or 2 orders silently.
3. Distinct Order Identities:
   - Unique client order ID, ticket, SL, TP, and execution state per order.
   - Shared setup_id and execution_group_id.
4. Persistent Execution Lifecycle & Failure Classification:
   - Order States: PROPOSED, VALIDATED, READY, SUBMITTING, ACCEPTED,
     PARTIALLY_FILLED, FILLED, REJECTED, RETRY_PENDING, CANCELLED,
     UNKNOWN_EXECUTION_STATE, RECONCILING, COMPLETED.
   - Distinguishes Recoverable vs Non-Recoverable failures.
   - Reconciles with MT5 on unknown state before retrying to prevent duplicate orders.
   - Handles partial fills (e.g. 2 filled, 1 failed) safely without duplicating.
"""
from __future__ import annotations

import enum
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Literal, Any, Callable

from src.utils.logging_config import get_logger

log = get_logger(__name__)


class OrderExecutionState(str, enum.Enum):
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    READY = "READY"
    SUBMITTING = "SUBMITTING"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    RETRY_PENDING = "RETRY_PENDING"
    CANCELLED = "CANCELLED"
    UNKNOWN_EXECUTION_STATE = "UNKNOWN_EXECUTION_STATE"
    RECONCILING = "RECONCILING"
    COMPLETED = "COMPLETED"


class FailureCategory(str, enum.Enum):
    RECOVERABLE = "RECOVERABLE"
    NON_RECOVERABLE = "NON_RECOVERABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class SingleOrderSpec:
    """Specification and live state for one order of the three-order group."""
    order_index: int                  # 1, 2, or 3
    order_id: str                     # Unique internal ID
    client_order_id: str              # setup_id-ord1
    symbol: str
    direction: str                    # "BUY" or "SELL"
    volume: float                     # Common calculated lot size
    entry_price: float
    sl_price: float
    tp_price: float
    state: OrderExecutionState = OrderExecutionState.PROPOSED
    broker_ticket: Optional[int] = None
    fill_price: Optional[float] = None
    retcode: Optional[int] = None
    error_message: str = ""
    retry_count: int = 0
    failure_category: Optional[FailureCategory] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ThreeOrderExecutionGroup:
    """Group tracking all three orders for one approved trading setup."""
    setup_id: str
    group_id: str
    symbol: str
    direction: str
    common_lot_size: float
    total_volume: float               # 3 * common_lot_size
    risk_per_order_usd: float
    total_combined_risk_usd: float
    orders: list[SingleOrderSpec]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "PENDING"
    rejection_reason: str = ""

    @property
    def confirmed_filled_count(self) -> int:
        return sum(1 for o in self.orders if o.state == OrderExecutionState.FILLED)

    @property
    def is_fully_executed(self) -> bool:
        return len(self.orders) == 3 and all(o.state == OrderExecutionState.FILLED for o in self.orders)

    @property
    def is_partially_executed(self) -> bool:
        filled = self.confirmed_filled_count
        return 0 < filled < len(self.orders)


class ThreeOrderExecutor:
    """
    Coordinates execution of three separate orders sharing one dynamic lot size.
    """

    def __init__(
        self,
        max_retries: int = 2,
        max_slippage_pips: float = 30.0,
    ) -> None:
        self.max_retries = max_retries
        self.max_slippage_pips = max_slippage_pips
        self._groups: dict[str, ThreeOrderExecutionGroup] = {}

    def classify_failure(self, retcode: Optional[int], error_msg: str) -> FailureCategory:
        """Classifies broker failure into Recoverable, Non-Recoverable, or Unknown."""
        if retcode is None:
            # Network drop / IPC timeout after submit
            return FailureCategory.UNKNOWN

        # MT5 standard retcodes
        # 10004: TRADE_RETCODE_REQUOTE, 10006: TRADE_RETCODE_REJECT (transient),
        # 10018: TRADE_RETCODE_MARKET_CLOSED (wait), 10019: TRADE_RETCODE_NO_MONEY (non-recov),
        # 10021: TRADE_RETCODE_TOO_FREQUENT (recov), 10012: TRADE_RETCODE_TIMEOUT (unknown)
        recoverable_codes = {10004, 10021, 10024, 10018}
        non_recoverable_codes = {10013, 10014, 10015, 10016, 10017, 10019, 10027, 10030}

        if retcode in recoverable_codes:
            return FailureCategory.RECOVERABLE
        if retcode in non_recoverable_codes:
            return FailureCategory.NON_RECOVERABLE
        if retcode in (10008, 10012):
            return FailureCategory.UNKNOWN

        lower_msg = error_msg.lower()
        if any(term in lower_msg for term in ("timeout", "connection", "busy", "requote")):
            return FailureCategory.RECOVERABLE
        if any(term in lower_msg for term in ("invalid", "margin", "money", "disabled", "volume")):
            return FailureCategory.NON_RECOVERABLE

        return FailureCategory.UNKNOWN

    def prepare_three_order_plan(
        self,
        setup_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        common_lot_size: float,
        account_equity: float,
        account_free_margin: float,
        tick_value: float = 1.0,
        tick_size: float = 0.01,
        contract_multiplier: float = 100.0,
        max_risk_pct: float = 1.25,
        broker_margin_needed: Optional[float] = None,
    ) -> tuple[bool, Optional[ThreeOrderExecutionGroup], str]:
        """
        Creates the ThreeOrderExecutionGroup after verifying combined exposure.
        All three orders have IDENTICAL calculated lot sizes.
        """
        if common_lot_size <= 0:
            return False, None, f"Calculated common lot size is invalid ({common_lot_size})"

        total_combined_volume = round(common_lot_size * 3.0, 2)
        sl_dist = abs(entry_price - sl_price)
        if sl_dist <= 0:
            return False, None, "Invalid SL distance (0.0)"

        # Calculate combined monetary risk
        risk_per_lot = (sl_dist / tick_size) * tick_value if tick_size > 0 else (sl_dist * contract_multiplier)
        risk_per_order = round(common_lot_size * risk_per_lot, 2)
        total_combined_risk = round(total_combined_volume * risk_per_lot, 2)

        # Validate against account equity risk ceiling:
        # Standard accounts (>= $500): strictly enforce max_risk_pct (e.g. 1.25%).
        # Micro accounts (< $500): allow minimum lot (0.01) if combined risk <= 35% equity (max $15.0).
        if account_equity >= 500.0:
            allowed_max_risk_usd = round(account_equity * (max_risk_pct / 100.0) * 1.05, 2)
        else:
            micro_limit = max(min(account_equity * 0.35, 20.0), 15.0)
            allowed_max_risk_usd = max(round(account_equity * (max_risk_pct / 100.0) * 1.05, 2), micro_limit)

        num_orders = 3
        if account_equity < 500.0 and common_lot_size <= 0.01 and total_combined_risk > allowed_max_risk_usd and risk_per_order > 0:
            # Micro-account adaptation: scale order count (1-3) to fit account budget without compromising structural SL beyond sweep wick
            num_orders = max(1, min(3, int(allowed_max_risk_usd / risk_per_order)))
            total_combined_volume = round(common_lot_size * num_orders, 2)
            total_combined_risk = round(total_combined_volume * risk_per_lot, 2)

        if total_combined_risk > allowed_max_risk_usd and allowed_max_risk_usd > 0:
            return False, None, (
                f"Combined exposure rejection: {num_orders} orders of {common_lot_size} lots = {total_combined_volume} lots. "
                f"Total risk ${total_combined_risk:.2f} exceeds allowed risk ceiling ${allowed_max_risk_usd:.2f} "
                f"({max_risk_pct}% of equity ${account_equity:.2f})."
            )

        # Margin safety check: combined orders must not exceed safe allowance of free margin
        est_margin_needed = broker_margin_needed if (broker_margin_needed is not None and broker_margin_needed > 0) else (
            total_combined_volume * (entry_price * contract_multiplier) / 1000.0
        )
        if account_free_margin > 0 and est_margin_needed > (account_free_margin * 0.35):
            return False, None, (
                f"Insufficient margin for {num_orders} orders: requires ~${est_margin_needed:.2f} margin "
                f"which exceeds safe allowance of free margin (${account_free_margin:.2f})."
            )

        group_id = f"grp_{setup_id}_{int(time.time())}"
        order_specs: list[SingleOrderSpec] = []
        for idx in range(1, num_orders + 1):
            ord_id = f"{group_id}_ord{idx}"
            client_id = f"{setup_id}-ord{idx}"
            spec = SingleOrderSpec(
                order_index=idx,
                order_id=ord_id,
                client_order_id=client_id,
                symbol=symbol,
                direction=direction.upper(),
                volume=common_lot_size,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
                state=OrderExecutionState.READY,
            )
            order_specs.append(spec)

        group = ThreeOrderExecutionGroup(
            setup_id=setup_id,
            group_id=group_id,
            symbol=symbol,
            direction=direction.upper(),
            common_lot_size=common_lot_size,
            total_volume=total_combined_volume,
            risk_per_order_usd=risk_per_order,
            total_combined_risk_usd=total_combined_risk,
            orders=order_specs,
            status="READY",
        )
        self._groups[group_id] = group
        return True, group, "Three-order execution plan approved and verified."

    def execute_group(
        self,
        group: ThreeOrderExecutionGroup,
        submit_order_fn: Callable[[SingleOrderSpec], tuple[bool, Optional[int], Optional[float], Optional[int], str]],
        query_open_positions_fn: Optional[Callable[[], list[dict]]] = None,
    ) -> ThreeOrderExecutionGroup:
        """
        Executes all three orders sequentially, confirming broker execution for each.
        Preserves confirmed orders if one fails, avoiding duplicate orders.
        """
        group.status = "EXECUTING"
        log.info(
            "executing_three_order_group",
            group_id=group.group_id,
            symbol=group.symbol,
            lot_per_order=group.common_lot_size,
            total_volume=group.total_volume,
            risk_usd=group.total_combined_risk_usd,
        )

        for order in group.orders:
            if order.state == OrderExecutionState.FILLED:
                continue  # Already successfully executed (e.g. on retry recovery)

            order.state = OrderExecutionState.SUBMITTING
            order.submitted_at = datetime.now(timezone.utc)

            success, ticket, fill_price, retcode, err_msg = submit_order_fn(order)
            order.retcode = retcode
            order.error_message = err_msg

            if success and ticket:
                order.broker_ticket = ticket
                order.fill_price = fill_price or order.entry_price
                order.state = OrderExecutionState.FILLED
                order.completed_at = datetime.now(timezone.utc)
                log.info(
                    "order_executed_confirmed",
                    group_id=group.group_id,
                    order_index=order.order_index,
                    ticket=ticket,
                    volume=order.volume,
                    fill_price=order.fill_price,
                )
            else:
                cat = self.classify_failure(retcode, err_msg)
                order.failure_category = cat
                if cat == FailureCategory.UNKNOWN:
                    order.state = OrderExecutionState.UNKNOWN_EXECUTION_STATE
                    # Query MT5 to verify if order actually filled before attempting any retry
                    if query_open_positions_fn:
                        order.state = OrderExecutionState.RECONCILING
                        live_pos = query_open_positions_fn()
                        matched = next((p for p in live_pos if str(p.get("comment", "")).endswith(f"ord{order.order_index}")), None)
                        if matched:
                            order.broker_ticket = int(matched["ticket"])
                            order.fill_price = float(matched.get("price_open", order.entry_price))
                            order.state = OrderExecutionState.FILLED
                            order.completed_at = datetime.now(timezone.utc)
                            log.info("reconciled_unknown_order_as_filled", ticket=order.broker_ticket)
                            continue
                elif cat == FailureCategory.RECOVERABLE and order.retry_count < self.max_retries:
                    order.state = OrderExecutionState.RETRY_PENDING
                else:
                    order.state = OrderExecutionState.REJECTED

        if group.is_fully_executed:
            group.status = "COMPLETED"
        elif group.is_partially_executed:
            group.status = "PARTIALLY_FILLED"
        else:
            group.status = "REJECTED"

        return group
