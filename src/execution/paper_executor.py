"""
Paper Trading Executor.

Simulates order fills without touching MT5. Maintains an isolated simulated
ledger. CANNOT call any MT5 order-submission function — this is enforced
architecturally by not importing MetaTrader5 here at all.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from src.utils.logging_config import get_logger

log = get_logger(__name__)


class PaperPosition:
    """Represents a single simulated open position."""

    def __init__(
        self,
        position_id: str,
        setup_id: str,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        sl: float,
        tp: float,
        opened_at: datetime,
    ) -> None:
        self.position_id = position_id
        self.setup_id = setup_id
        self.symbol = symbol
        self.direction = direction
        self.volume = volume
        self.entry_price = entry_price
        self.sl = sl
        self.tp = tp
        self.opened_at = opened_at
        self.is_open = True
        self.close_price: float | None = None
        self.closed_at: datetime | None = None
        self.pnl: float = 0.0

    def current_pnl(self, current_price: float, pip_value_per_lot: float, pip_size: float) -> float:
        if self.direction == "BULLISH":
            pips = (current_price - self.entry_price) / pip_size
        else:
            pips = (self.entry_price - current_price) / pip_size
        return pips * pip_value_per_lot * self.volume


class PaperLedger:
    """
    Simulated account ledger for paper trading.
    Tracks balance, equity, positions, and trade history.
    """

    def __init__(self, initial_balance: float = 10_000.0) -> None:
        self._balance = initial_balance
        self._positions: dict[str, PaperPosition] = {}
        self._closed: list[PaperPosition] = []

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def open_positions(self) -> list[PaperPosition]:
        return list(self._positions.values())

    @property
    def closed_trades(self) -> list[PaperPosition]:
        return list(self._closed)

    def equity(self, prices: dict[str, float], pip_values: dict[str, float], pip_sizes: dict[str, float]) -> float:
        unrealized = sum(
            p.current_pnl(prices.get(p.symbol, p.entry_price), pip_values.get(p.symbol, 1.0), pip_sizes.get(p.symbol, 0.01))
            for p in self._positions.values()
        )
        return self._balance + unrealized

    def open_position(self, pos: PaperPosition) -> None:
        self._positions[pos.position_id] = pos
        log.info("paper_position_opened", symbol=pos.symbol, direction=pos.direction,
                 volume=pos.volume, entry=pos.entry_price, sl=pos.sl, tp=pos.tp)

    def close_position(self, position_id: str, close_price: float, closed_at: datetime,
                       pip_value_per_lot: float, pip_size: float) -> float:
        pos = self._positions.pop(position_id, None)
        if pos is None:
            raise KeyError(f"No open paper position {position_id}")
        pos.close_price = close_price
        pos.closed_at = closed_at
        pos.is_open = False
        if pos.direction == "BULLISH":
            pips = (close_price - pos.entry_price) / pip_size
        else:
            pips = (pos.entry_price - close_price) / pip_size
        pos.pnl = pips * pip_value_per_lot * pos.volume
        self._balance += pos.pnl
        self._closed.append(pos)
        log.info("paper_position_closed", symbol=pos.symbol, pnl=pos.pnl, close_price=close_price)
        return pos.pnl

    def check_sl_tp(self, prices: dict[str, float]) -> list[str]:
        """Return position IDs that have hit SL or TP at current prices."""
        triggered = []
        for pid, pos in self._positions.items():
            price = prices.get(pos.symbol)
            if price is None:
                continue
            if pos.direction == "BULLISH":
                if price <= pos.sl or price >= pos.tp:
                    triggered.append(pid)
            else:
                if price >= pos.sl or price <= pos.tp:
                    triggered.append(pid)
        return triggered


class PaperExecutor:
    """
    Executes trades in paper mode only.
    Cannot be used to send real orders — MetaTrader5 is never imported here.
    """
    MODE = "paper"

    def __init__(self, initial_balance: float = 10_000.0) -> None:
        self._ledger = PaperLedger(initial_balance)

    @property
    def ledger(self) -> PaperLedger:
        return self._ledger

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
    ) -> tuple[bool, str, PaperPosition | None]:
        """
        Simulate an immediate market fill at ask (buy) or bid (sell).
        Returns (success, message, position).
        """
        fill_price = current_ask if direction == "BULLISH" else current_bid
        pos = PaperPosition(
            position_id=str(uuid.uuid4())[:8],
            setup_id=setup_id,
            symbol=symbol,
            direction=direction,
            volume=volume,
            entry_price=fill_price,
            sl=sl,
            tp=tp,
            opened_at=datetime.now(tz=timezone.utc),
        )
        self._ledger.open_position(pos)
        return True, f"Paper fill @ {fill_price:.5f}", pos

    def get_positions(self, symbol: str | None = None) -> list[PaperPosition]:
        positions = self._ledger.open_positions
        if symbol:
            positions = [p for p in positions if p.symbol == symbol]
        return positions

    def close_position(self, position_id: str, close_price: float,
                       pip_value_per_lot: float, pip_size: float) -> float:
        return self._ledger.close_position(
            position_id, close_price, datetime.now(tz=timezone.utc),
            pip_value_per_lot, pip_size
        )
