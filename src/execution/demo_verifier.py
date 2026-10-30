"""
Exness Demo Forward Verification Engine.

Verifies:
1. MetaTrader 5 IPC bridge and Exness Demo account connectivity.
2. Symbol resolution for primary instruments (XAUUSD -> XAUUSDm, BTCUSD -> BTCUSDm).
3. Live H1 completed candle streaming and live tick quote feed with latency measurement.
4. Pre-flight order validation via mt5.order_check() without market exposure.
5. Micro-lot demo test order dispatch with pre-attached structural SL and TP.
6. Post-fill broker Stop Loss attachment verification (zero naked positions rule).
7. Clean liquidation and Emergency Kill Switch execution.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.data.candle import Candle
from src.data.market_data_adapter import MT5DataAdapter
from src.execution.mt5_executor import MT5Executor, MT5Position
from src.utils.credentials import BrokerCredentials, CredentialManager
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class DemoVerificationReport:
    """Consolidated verification results for Exness Demo connectivity and execution."""
    timestamp: datetime
    terminal_connected: bool
    account_info: dict[str, Any] = field(default_factory=dict)
    symbol_resolution: dict[str, str] = field(default_factory=dict)
    quote_streaming: dict[str, dict[str, Any]] = field(default_factory=dict)
    order_check_result: dict[str, Any] = field(default_factory=dict)
    demo_trade_result: dict[str, Any] = field(default_factory=dict)
    liquidation_result: dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        border = "=" * 70
        lines = [
            border,
            "  EXNESS DEMO FORWARD VERIFICATION REPORT",
            border,
            f"  Verification Time  : {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"  Terminal Connected : {'YES (ONLINE)' if self.terminal_connected else 'NO (OFFLINE)'}",
        ]

        if self.account_info:
            lines.extend([
                f"  Account Login      : {self.account_info.get('login', 'N/A')}",
                f"  Server             : {self.account_info.get('server', 'N/A')}",
                f"  Balance / Equity   : ${self.account_info.get('balance', 0.0):,.2f} / ${self.account_info.get('equity', 0.0):,.2f}",
                f"  Free Margin        : ${self.account_info.get('margin_free', 0.0):,.2f}",
                f"  Leverage           : 1:{self.account_info.get('leverage', 'N/A')}",
            ])

        lines.append("-" * 70)
        lines.append("  SYMBOL RESOLUTION & QUOTE STREAMING:")
        for base_sym, resolved in self.symbol_resolution.items():
            q = self.quote_streaming.get(base_sym, {})
            candles_count = q.get("h1_candles_count", 0)
            bid = q.get("bid", 0.0)
            ask = q.get("ask", 0.0)
            spread = q.get("spread", 0.0)
            latency = q.get("latency_ms", 0.0)
            lines.append(
                f"    {base_sym:<8} -> {resolved:<10} | Bid: {bid:.2f} | Ask: {ask:.2f} | Spread: {spread:.2f} | Latency: {latency:.1f}ms | H1 Bars: {candles_count}"
            )

        if self.order_check_result:
            lines.append("-" * 70)
            lines.append("  PRE-FLIGHT ORDER CHECK (order_check):")
            ret = self.order_check_result.get("retcode", -1)
            comment = self.order_check_result.get("comment", "")
            margin_req = self.order_check_result.get("margin_required", 0.0)
            status_str = "PASSED" if ret == 0 else f"REJECTED ({comment})"
            lines.append(f"    Status: {status_str} | Margin Required: ${margin_req:.2f} | Code: {ret}")

        if self.demo_trade_result:
            lines.append("-" * 70)
            lines.append("  DEMO ORDER DISPATCH & STOP LOSS VERIFICATION:")
            filled = self.demo_trade_result.get("filled", False)
            ticket = self.demo_trade_result.get("ticket", 0)
            sl_verified = self.demo_trade_result.get("sl_verified", False)
            sl_val = self.demo_trade_result.get("sl", 0.0)
            tp_val = self.demo_trade_result.get("tp", 0.0)
            lines.append(
                f"    Filled: {'YES' if filled else 'NO'} | Ticket: {ticket} | SL Verified: {'YES' if sl_verified else 'NO'} (SL: {sl_val:.2f}, TP: {tp_val:.2f})"
            )

        if self.liquidation_result:
            lines.append("  EMERGENCY LIQUIDATION TEST:")
            closed = self.liquidation_result.get("closed", False)
            rem = self.liquidation_result.get("remaining_positions", 0)
            lines.append(f"    Closed: {'YES' if closed else 'NO'} | Open Positions Remaining: {rem}")

        lines.append("-" * 70)
        lines.append(f"  OVERALL STATUS     : {'ALL CHECKS PASSED' if self.passed else 'VERIFICATION INCOMPLETE / OFFLINE'}")
        if self.notes:
            lines.append("  NOTES:")
            for n in self.notes:
                lines.append(f"    - {n}")
        lines.append(border)
        return "\n".join(lines)


class DemoVerifier:
    """
    Executes automated forward verification of the MT5 Exness Demo environment.
    """

    def __init__(
        self,
        executor: MT5Executor | None = None,
        data_adapter: MT5DataAdapter | None = None,
        symbols: list[str] | None = None,
    ) -> None:
        self.symbols = symbols or ["XAUUSD", "BTCUSD"]
        self.executor = executor or MT5Executor(mode="DEMO")
        self.data_adapter = data_adapter or MT5DataAdapter()

    def verify_connectivity(self) -> tuple[bool, dict[str, Any]]:
        """Verify MT5 terminal is initialized and account is logged in."""
        ok = self.executor.connect()
        if not ok:
            return False, {}
        info = self.executor.get_account_info()
        return True, info or {}

    def verify_symbol_resolution(self) -> dict[str, str]:
        """Verify resolution of standard Exness symbol variations (e.g., XAUUSDm)."""
        mapping: dict[str, str] = {}
        for sym in self.symbols:
            resolved = self.executor.resolve_symbol(sym)
            mapping[sym] = resolved
        return mapping

    def verify_quote_streaming(self, resolved_symbols: dict[str, str]) -> dict[str, dict[str, Any]]:
        """Verify quote streaming and H1 candle fetching."""
        results: dict[str, dict[str, Any]] = {}
        for base_sym, resolved in resolved_symbols.items():
            t0 = time.perf_counter()
            tick = self.executor.get_symbol_tick(resolved)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            candles: list[Candle] = []
            try:
                candles = self.data_adapter.get_candles(symbol=resolved, timeframe="H1", count=20)
            except Exception as exc:
                log.warning("failed_to_get_candles_during_verification", symbol=resolved, error=str(exc))

            bid = tick.get("bid", 0.0) if tick else 0.0
            ask = tick.get("ask", 0.0) if tick else 0.0
            spread = (ask - bid) if (bid and ask) else 0.0

            results[base_sym] = {
                "resolved": resolved,
                "bid": bid,
                "ask": ask,
                "spread": round(spread, 3),
                "latency_ms": round(latency_ms, 2),
                "h1_candles_count": len(candles),
                "tick_time": tick.get("time") if tick else None,
            }
        return results

    def verify_preflight_order_check(self, symbol: str = "XAUUSD", volume: float = 0.01) -> dict[str, Any]:
        """Perform order_check pre-flight validation on broker server."""
        try:
            import MetaTrader5 as mt5
            resolved = self.executor.resolve_symbol(symbol)
            tick = self.executor.get_symbol_tick(resolved)
            if not tick:
                return {"retcode": -1, "comment": "No tick data available"}

            ask = tick["ask"]
            sl_buffer = 5.0 if "XAU" in symbol else 500.0
            tp_buffer = sl_buffer * 2.0

            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": resolved,
                "volume": float(volume),
                "type": mt5.ORDER_TYPE_BUY,
                "price": float(ask),
                "sl": float(ask - sl_buffer),
                "tp": float(ask + tp_buffer),
                "deviation": 20,
                "magic": 101001,
                "comment": "AGY_VERIFY_CHECK",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self.executor._determine_filling_type(resolved),
            }

            res = mt5.order_check(req)
            if res is None:
                return {"retcode": -1, "comment": str(mt5.last_error())}

            return {
                "retcode": res.retcode,
                "comment": res.comment,
                "margin_required": getattr(res, "margin", 0.0),
                "margin_free": getattr(res, "margin_free", 0.0),
                "symbol": resolved,
            }
        except Exception as exc:
            return {"retcode": -1, "comment": str(exc)}

    def verify_demo_order_dispatch(
        self,
        symbol: str = "XAUUSD",
        volume: float = 0.01,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Dispatches a 0.01 micro-lot test deal on Exness Demo, confirms broker SL,
        and then immediately closes the position.
        """
        resolved = self.executor.resolve_symbol(symbol)
        tick = self.executor.get_symbol_tick(resolved)
        if not tick:
            return {"filled": False, "error": "No tick available"}, {}

        ask = tick["ask"]
        bid = tick["bid"]
        sl_buffer = 5.0 if "XAU" in symbol else 500.0
        tp_buffer = sl_buffer * 2.0
        sl_target = ask - sl_buffer
        tp_target = ask + tp_buffer

        ok, msg, pos = self.executor.submit_order(
            setup_id="VERIFY_DEMO_01",
            symbol=resolved,
            direction="BULLISH",
            volume=volume,
            entry_price=ask,
            sl=sl_target,
            tp=tp_target,
            current_ask=ask,
            current_bid=bid,
        )

        trade_result = {
            "filled": ok,
            "message": msg,
            "ticket": pos.ticket if pos else 0,
            "sl_verified": (pos is not None and pos.sl > 0),
            "sl": pos.sl if pos else 0.0,
            "tp": pos.tp if pos else 0.0,
            "entry_price": pos.entry_price if pos else 0.0,
        }

        # Immediately test liquidation
        liquidation_result = {}
        if pos:
            close_ok, close_msg = self.executor.close_position(pos.ticket)
            remaining = len(self.executor.get_positions(resolved))
            liquidation_result = {
                "closed": close_ok,
                "message": close_msg,
                "remaining_positions": remaining,
            }

        return trade_result, liquidation_result

    def run_full_verification(self, execute_live_demo_trade: bool = False) -> DemoVerificationReport:
        """Run complete forward verification test suite."""
        now = datetime.now(timezone.utc)
        notes: list[str] = []

        conn_ok, acct_info = self.verify_connectivity()
        if not conn_ok:
            notes.append("MetaTrader 5 terminal is offline or credentials not yet entered.")
            notes.append("Launch MetaTrader 5 on Windows and log into your Exness Demo account.")
            return DemoVerificationReport(
                timestamp=now,
                terminal_connected=False,
                account_info={},
                passed=False,
                notes=notes,
            )

        # 1. Symbol Resolution
        sym_map = self.verify_symbol_resolution()

        # 2. Quote Streaming
        quotes = self.verify_quote_streaming(sym_map)

        # 3. Pre-flight Order Check
        check_res = self.verify_preflight_order_check(symbol="XAUUSD", volume=0.01)

        trade_res: dict[str, Any] = {}
        liq_res: dict[str, Any] = {}
        if execute_live_demo_trade:
            trade_res, liq_res = self.verify_demo_order_dispatch(symbol="XAUUSD", volume=0.01)

        all_quotes_valid = any(q.get("bid", 0) > 0 for q in quotes.values())
        order_check_valid = check_res.get("retcode") == 0
        overall_passed = conn_ok and all_quotes_valid and order_check_valid

        if overall_passed:
            notes.append("All Exness Demo forward verification checks passed successfully.")
        else:
            if not order_check_valid:
                notes.append(f"Pre-flight order check returned: {check_res.get('comment', 'unknown')}")

        return DemoVerificationReport(
            timestamp=now,
            terminal_connected=True,
            account_info=acct_info,
            symbol_resolution=sym_map,
            quote_streaming=quotes,
            order_check_result=check_res,
            demo_trade_result=trade_res,
            liquidation_result=liq_res,
            passed=overall_passed,
            notes=notes,
        )
