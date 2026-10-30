"""
Multi-Account Trade Copier Engine — Single MT5 Process Fast-Switch Architecture.

Designed specifically for Windows on limited-RAM hardware (e.g. 4 GB RAM):
- Runs inside a single open MetaTrader 5 terminal.
- Master Account: Analyzes the market, detects Part 3 setups, and opens initial deal.
- Child/Slave Accounts: Sequentially switched via high-speed in-process mt5.login() (<200ms).
- Dynamic Proportional Sizing: Calculates lot sizes matching each child account's exact
  equity and 1.0% dollar risk limit.
- Synchronized Exits & Emergency Liquidation: Closes corresponding child positions
  when master closes, and supports global Kill Switch liquidation across all accounts.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from src.execution.mt5_executor import MT5Executor, MT5Position
from src.utils.credentials import BrokerCredentials
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class ChildAccountConfig:
    """Configuration for a connected child trading account."""
    account_id: int
    password: str
    server: str
    label: str = ""
    risk_pct: float = 1.0            # Risk 1.0% of child balance
    risk_multiplier: float = 1.0     # Multiplier relative to standard risk
    is_active: bool = True
    max_slippage_pips: float = 3.0   # Reject copy if market moved too far
    magic_number: int = 101002


@dataclass
class CopiedTradeRecord:
    """Audit record for a copied trade on a child account."""
    master_ticket: int
    child_account_id: int
    child_ticket: int
    symbol: str
    direction: str                   # "BULLISH" or "BEARISH"
    entry_price: float
    volume: float
    sl: float
    tp: float
    opened_at: datetime
    status: str = "OPEN"             # "OPEN", "CLOSED", "FAILED"


class MultiAccountCopier:
    """
    Manages multi-account execution without spawning multiple heavy MT5 processes.
    """

    def __init__(
        self,
        master_executor: MT5Executor,
        child_accounts: list[ChildAccountConfig] | None = None,
    ) -> None:
        self.master_executor = master_executor
        self.child_accounts: dict[int, ChildAccountConfig] = {}
        self.copied_trades: list[CopiedTradeRecord] = []

        if child_accounts:
            for acc in child_accounts:
                self.add_child_account(acc)

    def add_child_account(self, config: ChildAccountConfig) -> None:
        """Register a child account for trade copying."""
        self.child_accounts[config.account_id] = config
        log.info(
            "child_account_registered",
            account_id=config.account_id,
            server=config.server,
            label=config.label,
        )

    def remove_child_account(self, account_id: int) -> bool:
        """Unregister a child account."""
        if account_id in self.child_accounts:
            del self.child_accounts[account_id]
            log.info("child_account_removed", account_id=account_id)
            return True
        return False

    def get_child_accounts(self) -> list[ChildAccountConfig]:
        return list(self.child_accounts.values())

    def _switch_account(self, account_id: int, password: str, server: str) -> bool:
        """Fast-switch MT5 terminal session to target account in ~150-250ms."""
        import MetaTrader5 as mt5
        ok = mt5.login(login=account_id, password=password, server=server)
        if not ok:
            err = mt5.last_error()
            log.error("mt5_fast_switch_failed", account_id=account_id, error=err)
            return False
        return True

    def _restore_master(self) -> bool:
        """Restore MT5 terminal session back to Master Account."""
        master_creds = self.master_executor.credentials
        if not master_creds:
            return False
        return self._switch_account(
            account_id=master_creds.account_id,
            password=master_creds.password,
            server=master_creds.server,
        )

    def copy_order(
        self,
        master_pos: MT5Position,
        setup_id: str,
    ) -> list[CopiedTradeRecord]:
        """
        Copy an executed Master order across all active child accounts with
        individual proportional risk sizing.
        """
        import MetaTrader5 as mt5

        results: list[CopiedTradeRecord] = []
        active_children = [c for c in self.child_accounts.values() if c.is_active]
        if not active_children:
            return results

        sl_distance = abs(master_pos.entry_price - master_pos.sl)
        if sl_distance <= 0:
            log.warning("cannot_copy_zero_sl_distance", master_ticket=master_pos.ticket)
            return results

        for child in active_children:
            try:
                # 1. Switch session to child account
                switched = self._switch_account(child.account_id, child.password, child.server)
                if not switched:
                    continue

                # 2. Get Child Account balance & symbol spec
                acct_info = mt5.account_info()
                if not acct_info:
                    log.error("child_account_info_unavailable", account_id=child.account_id)
                    continue

                child_balance = acct_info.balance
                resolved_symbol = self.master_executor.resolve_symbol(master_pos.symbol)
                sym_info = mt5.symbol_info(resolved_symbol)
                if not sym_info:
                    log.error("child_symbol_info_unavailable", symbol=resolved_symbol)
                    continue

                # 3. Dynamic Proportional Position Sizing (1.0% dollar risk on child balance)
                target_risk_usd = child_balance * (child.risk_pct / 100.0) * child.risk_multiplier
                tick_size = sym_info.trade_tick_size or sym_info.point or 0.01
                tick_value = sym_info.trade_tick_value or 1.0

                ticks_at_risk = sl_distance / tick_size
                risk_per_lot = ticks_at_risk * tick_value
                if risk_per_lot <= 0:
                    continue

                raw_volume = target_risk_usd / risk_per_lot
                step = sym_info.volume_step or 0.01
                steps = math.floor(raw_volume / step)
                volume = round(steps * step, 2)
                volume = max(sym_info.volume_min, min(sym_info.volume_max, volume))

                # 4. Check Current Tick & Slippage Guard
                tick = mt5.symbol_info_tick(resolved_symbol)
                if not tick:
                    log.warning("child_tick_unavailable", symbol=resolved_symbol)
                    continue

                current_price = tick.ask if master_pos.direction == "BULLISH" else tick.bid
                slippage_distance = abs(current_price - master_pos.entry_price)
                max_allowed_slip = child.max_slippage_pips * sym_info.point * 10
                if slippage_distance > max_allowed_slip:
                    log.warning(
                        "child_copy_rejected_excessive_slippage",
                        account_id=child.account_id,
                        slippage=slippage_distance,
                        max_allowed=max_allowed_slip,
                    )
                    continue

                # 5. Build Child Deal Request with Mandatory Attached SL & TP
                order_type = mt5.ORDER_TYPE_BUY if master_pos.direction == "BULLISH" else mt5.ORDER_TYPE_SELL
                filling_mode = self.master_executor._determine_filling_type(resolved_symbol)

                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": resolved_symbol,
                    "volume": float(volume),
                    "type": order_type,
                    "price": float(current_price),
                    "sl": float(master_pos.sl),
                    "tp": float(master_pos.tp),
                    "deviation": 20,
                    "magic": int(child.magic_number),
                    "comment": f"CPY_{setup_id[:8]}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling_mode,
                }

                # 6. Pre-flight check & send
                check_res = mt5.order_check(req)
                if check_res is None or check_res.retcode != 0:
                    err_msg = check_res.comment if check_res else str(mt5.last_error())
                    log.error("child_order_check_failed", account_id=child.account_id, error=err_msg)
                    continue

                send_res = mt5.order_send(req)
                if send_res is None or send_res.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
                    err_msg = send_res.comment if send_res else str(mt5.last_error())
                    log.error("child_order_send_failed", account_id=child.account_id, error=err_msg)
                    continue

                child_ticket = send_res.order
                record = CopiedTradeRecord(
                    master_ticket=master_pos.ticket,
                    child_account_id=child.account_id,
                    child_ticket=child_ticket,
                    symbol=resolved_symbol,
                    direction=master_pos.direction,
                    entry_price=send_res.price,
                    volume=volume,
                    sl=master_pos.sl,
                    tp=master_pos.tp,
                    opened_at=datetime.now(timezone.utc),
                    status="OPEN",
                )
                self.copied_trades.append(record)
                results.append(record)
                log.info(
                    "child_order_copied_successfully",
                    account_id=child.account_id,
                    child_ticket=child_ticket,
                    volume=volume,
                    price=send_res.price,
                )

            except Exception as exc:
                log.error("child_copy_exception", account_id=child.account_id, error=str(exc))

        # Always return terminal to master account
        self._restore_master()
        return results

    def sync_position_close(self, master_ticket: int) -> dict[int, bool]:
        """
        Closes all copied child orders corresponding to a closed Master ticket.
        """
        import MetaTrader5 as mt5

        results: dict[int, bool] = {}
        targets = [t for t in self.copied_trades if t.master_ticket == master_ticket and t.status == "OPEN"]
        if not targets:
            return results

        for trade in targets:
            child = self.child_accounts.get(trade.child_account_id)
            if not child:
                continue

            try:
                switched = self._switch_account(child.account_id, child.password, child.server)
                if not switched:
                    results[trade.child_ticket] = False
                    continue

                positions = mt5.positions_get(ticket=trade.child_ticket)
                if not positions:
                    trade.status = "CLOSED"
                    results[trade.child_ticket] = True
                    continue

                p = positions[0]
                is_buy = (p.type == mt5.POSITION_TYPE_BUY)
                close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                tick = mt5.symbol_info_tick(p.symbol)
                close_price = tick.bid if is_buy else tick.ask

                req = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": trade.child_ticket,
                    "symbol": p.symbol,
                    "volume": p.volume,
                    "type": close_type,
                    "price": close_price,
                    "deviation": 20,
                    "magic": int(child.magic_number),
                    "comment": f"CPY_CLOSE_{trade.child_ticket}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": self.master_executor._determine_filling_type(p.symbol),
                }

                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    trade.status = "CLOSED"
                    results[trade.child_ticket] = True
                    log.info("child_position_closed", child_ticket=trade.child_ticket)
                else:
                    results[trade.child_ticket] = False

            except Exception as exc:
                log.error("sync_close_exception", child_ticket=trade.child_ticket, error=str(exc))
                results[trade.child_ticket] = False

        self._restore_master()
        return results

    def close_all_accounts_positions(self) -> dict[str, int]:
        """
        Emergency Global Kill Switch:
        Iterates through Master account and ALL Child accounts to close every open position.
        """
        import MetaTrader5 as mt5

        report: dict[str, int] = {}

        # 1. Liquidate Master Account
        self._restore_master()
        master_closed = self.master_executor.close_all_positions()
        master_id = str(self.master_executor.credentials.account_id) if self.master_executor.credentials else "master"
        report[master_id] = master_closed

        # 2. Liquidate Each Child Account
        for child in self.child_accounts.values():
            switched = self._switch_account(child.account_id, child.password, child.server)
            if not switched:
                report[str(child.account_id)] = 0
                continue

            open_positions = mt5.positions_get()
            closed_here = 0
            if open_positions:
                for p in open_positions:
                    is_buy = (p.type == mt5.POSITION_TYPE_BUY)
                    close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                    tick = mt5.symbol_info_tick(p.symbol)
                    close_price = tick.bid if is_buy else tick.ask

                    req = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "position": p.ticket,
                        "symbol": p.symbol,
                        "volume": p.volume,
                        "type": close_type,
                        "price": close_price,
                        "deviation": 20,
                        "magic": int(child.magic_number),
                        "comment": "GLOBAL_KILL_SWITCH",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": self.master_executor._determine_filling_type(p.symbol),
                    }
                    res = mt5.order_send(req)
                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                        closed_here += 1

            report[str(child.account_id)] = closed_here

        # Mark all tracked trades closed
        for t in self.copied_trades:
            t.status = "CLOSED"

        # Restore Master
        self._restore_master()
        log.warning("global_kill_switch_executed_across_all_accounts", report=report)
        return report

    def get_all_account_balances(self) -> dict[str, dict[str, Any]]:
        """
        Fetches current balance, equity, and margin across all accounts in ~300ms.
        """
        import MetaTrader5 as mt5

        balances: dict[str, dict[str, Any]] = {}

        # 1. Master Account
        self._restore_master()
        master_info = self.master_executor.get_account_info()
        master_id = str(self.master_executor.credentials.account_id) if self.master_executor.credentials else "master"
        balances[master_id] = {
            "label": "Master Account",
            "server": master_info.get("server", "") if master_info else "",
            "balance": master_info.get("balance", 0.0) if master_info else 0.0,
            "equity": master_info.get("equity", 0.0) if master_info else 0.0,
            "margin_free": master_info.get("margin_free", 0.0) if master_info else 0.0,
            "is_master": True,
            "is_active": True,
        }

        # 2. Child Accounts
        for child in self.child_accounts.values():
            switched = self._switch_account(child.account_id, child.password, child.server)
            if not switched:
                balances[str(child.account_id)] = {
                    "label": child.label or f"Child #{child.account_id}",
                    "server": child.server,
                    "balance": 0.0,
                    "equity": 0.0,
                    "margin_free": 0.0,
                    "is_master": False,
                    "is_active": False,
                }
                continue

            info = mt5.account_info()
            balances[str(child.account_id)] = {
                "label": child.label or f"Child #{child.account_id}",
                "server": child.server,
                "balance": info.balance if info else 0.0,
                "equity": info.equity if info else 0.0,
                "margin_free": info.margin_free if info else 0.0,
                "is_master": False,
                "is_active": child.is_active,
                "risk_multiplier": child.risk_multiplier,
            }

        self._restore_master()
        return balances
