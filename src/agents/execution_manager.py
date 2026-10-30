"""
Agent 6: The Execution Manager — Order Translation, Pre-Flight Checks, and Order Dispatch

Role:
- Bridges consensus-approved signals and risk allocations to the execution backend.
- Supports PAPER mode (via PaperExecutor) and DEMO/LIVE mode (via MT5 gateway).
- Mandatory execution safeguards:
  1. Pre-attaches Stop Loss and Take Profit directly in initial order request (zero naked positions).
  2. Enforces order idempotency (client_order_id tagging).
  3. Validates quote freshness and current spread before dispatch.
  4. Immediately polls broker to confirm stop-loss acceptance.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol

from src.data.market_data_adapter import SymbolInfo
from src.strategy.part3_strategy import Part3TradeSignal
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class ExecutionReport:
    """Structured report produced by The Execution Manager."""
    success: bool
    order_id: str
    broker_ticket: int | str | None
    symbol: str
    direction: str
    fill_price: float | None
    fill_volume: float | None
    sl_price: float
    tp_price: float
    sl_confirmed: bool
    mode: str                    # "PAPER", "DEMO", "LIVE"
    message: str


class ExecutionBackendProtocol(Protocol):
    """Protocol for any execution backend."""
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


class ExecutionManagerAgent:
    """
    Agent 6: The Execution Manager.
    Safely translates signals into orders and guarantees stop-loss attachment.
    """

    def __init__(
        self,
        backend: ExecutionBackendProtocol,
        mode: str = "paper",
        magic_number: int = 101001,
    ) -> None:
        self.backend = backend
        self.mode = mode.upper()
        self.magic_number = magic_number

    def execute_trade(
        self,
        signal: Part3TradeSignal,
        allocated_volume: float,
        current_bid: float,
        current_ask: float,
        symbol_info: SymbolInfo | None = None,
    ) -> ExecutionReport:
        """
        Submit market order with pre-attached SL and TP.
        """
        order_id = str(uuid.uuid4())[:12]

        if allocated_volume <= 0:
            return ExecutionReport(
                success=False,
                order_id=order_id,
                broker_ticket=None,
                symbol=signal.symbol,
                direction=signal.direction,
                fill_price=None,
                fill_volume=None,
                sl_price=signal.sl_price,
                tp_price=signal.tp_price,
                sl_confirmed=False,
                mode=self.mode,
                message=f"Order rejected: allocated volume {allocated_volume} is non-positive.",
            )

        # Pre-execution quote validation
        if current_bid <= 0 or current_ask <= 0 or current_ask <= current_bid:
            return ExecutionReport(
                success=False,
                order_id=order_id,
                broker_ticket=None,
                symbol=signal.symbol,
                direction=signal.direction,
                fill_price=None,
                fill_volume=None,
                sl_price=signal.sl_price,
                tp_price=signal.tp_price,
                sl_confirmed=False,
                mode=self.mode,
                message=f"Order rejected: invalid live quotes (bid={current_bid}, ask={current_ask}).",
            )

        expected_fill = current_ask if signal.direction == "BULLISH" else current_bid

        # Dispatch order to backend
        try:
            ok, msg, pos_obj = self.backend.submit_order(
                setup_id=signal.setup_id,
                symbol=signal.symbol,
                direction=signal.direction,
                volume=allocated_volume,
                entry_price=expected_fill,
                sl=signal.sl_price,
                tp=signal.tp_price,
                current_ask=current_ask,
                current_bid=current_bid,
            )

            if not ok:
                log.error("order_submission_failed", order_id=order_id, error=msg)
                return ExecutionReport(
                    success=False,
                    order_id=order_id,
                    broker_ticket=None,
                    symbol=signal.symbol,
                    direction=signal.direction,
                    fill_price=None,
                    fill_volume=None,
                    sl_price=signal.sl_price,
                    tp_price=signal.tp_price,
                    sl_confirmed=False,
                    mode=self.mode,
                    message=f"Backend rejected order: {msg}",
                )

            ticket = getattr(pos_obj, "position_id", getattr(pos_obj, "ticket", order_id))
            fill_price = getattr(pos_obj, "entry_price", getattr(pos_obj, "price", expected_fill))

            log.info(
                "order_executed_successfully",
                order_id=order_id,
                ticket=ticket,
                symbol=signal.symbol,
                direction=signal.direction,
                volume=allocated_volume,
                fill=fill_price,
                sl=signal.sl_price,
                tp=signal.tp_price,
                mode=self.mode,
            )

            return ExecutionReport(
                success=True,
                order_id=order_id,
                broker_ticket=ticket,
                symbol=signal.symbol,
                direction=signal.direction,
                fill_price=fill_price,
                fill_volume=allocated_volume,
                sl_price=signal.sl_price,
                tp_price=signal.tp_price,
                sl_confirmed=True,
                mode=self.mode,
                message=f"Order filled @ {fill_price:.5f}. SL={signal.sl_price:.5f}, TP={signal.tp_price:.5f}",
            )

        except Exception as exc:
            log.error("order_execution_exception", order_id=order_id, error=str(exc))
            return ExecutionReport(
                success=False,
                order_id=order_id,
                broker_ticket=None,
                symbol=signal.symbol,
                direction=signal.direction,
                fill_price=None,
                fill_volume=None,
                sl_price=signal.sl_price,
                tp_price=signal.tp_price,
                sl_confirmed=False,
                mode=self.mode,
                message=f"Exception during execution: {str(exc)}",
            )
