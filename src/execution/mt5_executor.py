"""
MetaTrader 5 & Exness Live/Demo Execution Engine.

Role:
- Executes orders via official MetaTrader 5 Python IPC bridge.
- Auto-detects Exness symbol variants (e.g., XAUUSDm on Standard vs XAUUSD on Pro).
- Enforces strict safety rules:
  1. Mandatory SL and TP attached directly in the initial TRADE_ACTION_DEAL request.
  2. Immediate post-fill verification of broker Stop Loss (zero naked positions).
  3. Pre-flight margin and account sufficiency checks via order_check().
  4. Emergency Kill Switch liquidation (close_all_positions).
  5. Live execution safety switch (demo/paper default).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.utils.credentials import BrokerCredentials, CredentialManager
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class MT5Position:
    """Represents an active MT5 broker position."""
    ticket: int
    symbol: str
    direction: str              # "BULLISH" or "BEARISH"
    volume: float
    entry_price: float
    current_price: float
    sl: float
    tp: float
    pnl: float
    swap: float
    magic: int
    comment: str
    opened_at: datetime


class MT5Executor:
    """
    MetaTrader 5 broker order execution engine.
    Satisfies ExecutionBackendProtocol.
    """
    MODE = "DEMO"

    def __init__(
        self,
        credentials: BrokerCredentials | None = None,
        mode: str = "DEMO",
        magic_number: int = 101001,
        deviation: int = 20,
        live_armed: bool = False,
    ) -> None:
        self.credentials = credentials
        self.mode = mode.upper()
        self.magic_number = magic_number
        self.deviation = deviation
        self.live_armed = live_armed
        self._connected = False
        self._symbol_cache: dict[str, str] = {}

        if self.mode == "LIVE" and not self.live_armed:
            raise PermissionError("LIVE execution mode blocked: live_armed is False.")

    def connect(self) -> bool:
        """Initialize MT5 and authenticate with Exness account."""
        try:
            import MetaTrader5 as mt5

            init_kwargs: dict = {"timeout": 3000}
            if self.credentials and self.credentials.path:
                init_kwargs["path"] = self.credentials.path

            if not mt5.initialize(**init_kwargs):
                err = mt5.last_error()
                log.error("mt5_initialize_failed", error=err)
                return False

            if self.credentials:
                login_ok = mt5.login(
                    login=self.credentials.account_id,
                    password=self.credentials.password,
                    server=self.credentials.server,
                )
                if not login_ok:
                    err = mt5.last_error()
                    log.error("mt5_login_failed", error=err, server=self.credentials.server)
                    mt5.shutdown()
                    return False

            self._connected = True
            info = mt5.account_info()
            log.info(
                "mt5_executor_connected",
                login=info.login if info else "unknown",
                server=info.server if info else "unknown",
                balance=info.balance if info else 0.0,
                equity=info.equity if info else 0.0,
                mode=self.mode,
            )
            return True
        except ImportError:
            log.error("metatrader5_package_not_installed")
            return False
        except Exception as exc:
            log.error("mt5_connection_exception", error=str(exc))
            return False

    def disconnect(self) -> None:
        """Cleanly shutdown MT5 connection."""
        try:
            import MetaTrader5 as mt5
            mt5.shutdown()
        except Exception:
            pass
        self._connected = False
        log.info("mt5_executor_disconnected")

    def is_connected(self) -> bool:
        if not self._connected:
            return False
        try:
            import MetaTrader5 as mt5
            return mt5.terminal_info() is not None
        except Exception:
            return False

    def get_account_info(self) -> dict | None:
        """Fetch live account status."""
        try:
            import MetaTrader5 as mt5
            info = mt5.account_info()
            if info is None:
                return None
            return {
                "login": info.login,
                "server": info.server,
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "margin_free": info.margin_free,
                "leverage": info.leverage,
                "currency": info.currency,
                "trade_mode": getattr(info, "trade_mode", 0),
            }
        except Exception as exc:
            log.error("mt5_get_account_info_error", error=str(exc))
            return None

    def get_symbol_tick(self, symbol: str) -> dict | None:
        """Fetch current bid/ask tick for symbol."""
        try:
            import MetaTrader5 as mt5
            resolved = self.resolve_symbol(symbol)
            tick = mt5.symbol_info_tick(resolved)
            if tick is None:
                return None
            return {
                "symbol": resolved,
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
                "volume": tick.volume,
                "time": datetime.fromtimestamp(tick.time, tz=timezone.utc),
            }
        except Exception as exc:
            log.error("mt5_get_symbol_tick_error", symbol=symbol, error=str(exc))
            return None

    def resolve_symbol(self, base_symbol: str) -> str:
        """
        Auto-detect Exness symbol naming variations.
        Checks for base name and Exness Standard suffix (e.g. 'm', '.').
        """
        if base_symbol in self._symbol_cache:
            return self._symbol_cache[base_symbol]

        import MetaTrader5 as mt5
        symbols = mt5.symbols_get()
        if not symbols:
            return base_symbol

        avail = {s.name.upper(): s.name for s in symbols}

        # Candidate names in priority order
        candidates = [
            base_symbol.upper(),
            f"{base_symbol.upper()}M",   # Exness Standard account suffix
            f"{base_symbol.upper()}.",   # Exness variant
            f"{base_symbol.upper()}C",   # Exness Cent account
        ]

        resolved = base_symbol
        for c in candidates:
            if c in avail:
                resolved = avail[c]
                break

        # Ensure symbol is selected in MarketWatch
        mt5.symbol_select(resolved, True)
        self._symbol_cache[base_symbol] = resolved
        log.info("symbol_resolved", base=base_symbol, resolved=resolved)
        return resolved

    def _determine_filling_type(self, symbol_name: str) -> int:
        """Determine appropriate order filling mode from broker symbol properties."""
        import MetaTrader5 as mt5
        info = mt5.symbol_info(symbol_name)
        if info is None:
            return mt5.ORDER_FILLING_IOC

        # Bitmask check for filling mode
        modes = info.filling_mode
        if modes & 1:  # FOK
            return mt5.ORDER_FILLING_FOK
        elif modes & 2:  # IOC
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

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
    ) -> tuple[bool, str, MT5Position | None]:
        """
        Submit market order with mandatory attached SL and TP.
        Enforces immediate post-fill stop-loss verification.
        """
        import MetaTrader5 as mt5

        if not self.is_connected():
            if not self.connect():
                return False, "Cannot connect to MetaTrader 5 terminal.", None

        resolved_symbol = self.resolve_symbol(symbol)
        order_type = mt5.ORDER_TYPE_BUY if direction == "BULLISH" else mt5.ORDER_TYPE_SELL
        exec_price = current_ask if direction == "BULLISH" else current_bid
        filling_mode = self._determine_filling_type(resolved_symbol)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": resolved_symbol,
            "volume": float(volume),
            "type": order_type,
            "price": float(exec_price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": int(self.deviation),
            "magic": int(self.magic_number),
            "comment": f"AGY_{setup_id[:8]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        # 1. Pre-flight validation
        check_res = mt5.order_check(request)
        if check_res is None or check_res.retcode != 0:
            err_msg = check_res.comment if check_res else str(mt5.last_error())
            log.error("order_check_rejected", error=err_msg, symbol=resolved_symbol)
            return False, f"Pre-flight order_check failed: {err_msg}", None

        # 2. Dispatch Order
        res = mt5.order_send(request)
        if res is None:
            err = mt5.last_error()
            log.error("order_send_returned_none", error=err)
            return False, f"order_send failed: {err}", None

        if res.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
            log.error("order_send_failed", retcode=res.retcode, comment=res.comment)
            return False, f"Broker rejected order: {res.comment} (retcode={res.retcode})", None

        ticket = res.order
        log.info(
            "order_filled_by_broker",
            ticket=ticket,
            symbol=resolved_symbol,
            price=res.price,
            volume=res.volume,
        )

        # 3. Post-Fill Stop-Loss Verification (CRITICAL SAFETY RULE)
        time.sleep(0.1)  # Allow MT5 database state to propagate
        pos = self._verify_broker_sl(ticket=ticket, expected_sl=sl, symbol=resolved_symbol)
        if pos is None:
            return False, f"Position {ticket} filled but broker SL verification failed.", None

        return True, f"Filled @ {pos.entry_price:.5f}", pos

    def _verify_broker_sl(self, ticket: int, expected_sl: float, symbol: str) -> MT5Position | None:
        """
        Poll positions to confirm Stop Loss is active on broker server.
        If SL is missing, attempts emergency modification or immediate liquidation.
        """
        import MetaTrader5 as mt5
        positions = mt5.positions_get(ticket=ticket)

        if not positions:
            log.critical("position_not_found_after_fill", ticket=ticket)
            return None

        p = positions[0]
        pos_sl = p.sl

        # If broker opened position without SL -> Emergency SL attachment
        if pos_sl <= 0 or abs(pos_sl - expected_sl) > 0.05:
            log.warning("missing_sl_detected_attempting_fix", ticket=ticket, expected_sl=expected_sl)
            mod_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": float(expected_sl),
                "tp": float(p.tp),
            }
            mod_res = mt5.order_send(mod_request)
            if mod_res is None or mod_res.retcode != mt5.TRADE_RETCODE_DONE:
                log.critical(
                    "EMERGENCY_LIQUIDATION_FIRED: Could not set SL on position!",
                    ticket=ticket,
                )
                self.close_position(ticket)
                return None

        opened_dt = datetime.fromtimestamp(p.time, tz=timezone.utc)
        return MT5Position(
            ticket=p.ticket,
            symbol=p.symbol,
            direction="BULLISH" if p.type == mt5.POSITION_TYPE_BUY else "BEARISH",
            volume=p.volume,
            entry_price=p.price_open,
            current_price=p.price_current,
            sl=p.sl,
            tp=p.tp,
            pnl=p.profit,
            swap=p.swap,
            magic=p.magic,
            comment=p.comment,
            opened_at=opened_dt,
        )

    def get_positions(self, symbol: str | None = None) -> list[MT5Position]:
        """Query currently open positions from MT5."""
        import MetaTrader5 as mt5

        if not self.is_connected():
            return []

        resolved = self.resolve_symbol(symbol) if symbol else None
        kwargs = {"symbol": resolved} if resolved else {}
        raw_positions = mt5.positions_get(**kwargs)
        if not raw_positions:
            return []

        results: list[MT5Position] = []
        for p in raw_positions:
            opened_dt = datetime.fromtimestamp(p.time, tz=timezone.utc)
            results.append(
                MT5Position(
                    ticket=p.ticket,
                    symbol=p.symbol,
                    direction="BULLISH" if p.type == mt5.POSITION_TYPE_BUY else "BEARISH",
                    volume=p.volume,
                    entry_price=p.price_open,
                    current_price=p.price_current,
                    sl=p.sl,
                    tp=p.tp,
                    pnl=p.profit,
                    swap=p.swap,
                    magic=p.magic,
                    comment=p.comment,
                    opened_at=opened_dt,
                )
            )
        return results

    def close_position(self, ticket: int) -> tuple[bool, str]:
        """Liquidate a single position at market."""
        import MetaTrader5 as mt5
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False, f"Position ticket {ticket} not found."

        p = positions[0]
        is_buy = (p.type == mt5.POSITION_TYPE_BUY)
        close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(p.symbol)
        price = tick.bid if is_buy else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": close_type,
            "price": price,
            "deviation": int(self.deviation),
            "magic": int(self.magic_number),
            "comment": f"AGY_CLOSE_{ticket}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._determine_filling_type(p.symbol),
        }

        res = mt5.order_send(request)
        if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
            err = res.comment if res else str(mt5.last_error())
            log.error("close_position_failed", ticket=ticket, error=err)
            return False, err

        log.info("position_closed_at_market", ticket=ticket, price=price)
        return True, f"Closed position {ticket} @ {price:.5f}"

    def close_all_positions(self, symbol: str | None = None) -> int:
        """Emergency Kill Switch: Liquidate all open positions immediately."""
        positions = self.get_positions(symbol=symbol)
        closed_count = 0
        for p in positions:
            ok, _ = self.close_position(p.ticket)
            if ok:
                closed_count += 1
        log.warning("emergency_close_all_executed", closed=closed_count, total=len(positions))
        return closed_count
