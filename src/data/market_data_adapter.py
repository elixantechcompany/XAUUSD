"""
Market data adapter — abstracts MT5 behind a clean interface.

Key guarantees:
- Only COMPLETED (closed) candles are returned by get_candles().
- The most-recent candle in any MT5 response is the live/forming bar;
  it is always stripped before returning.
- Ticks are returned as-is for tick-break trigger mode.
- Symbol discovery lists all available symbols and matches user-chosen names.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Protocol, Sequence

import pandas as pd

from src.data.candle import Candle
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# ── MT5 timeframe constants (imported lazily to keep tests importable) ────────
_MT5_TIMEFRAME_MAP: dict[str, int] = {
    "M1":  1,
    "M5":  5,
    "M15": 15,
    "M30": 30,
    "H1":  16385,
    "H4":  16388,
    "D1":  16408,
    "W1":  32769,
    "MN1": 49153,
}


class SymbolInfo:
    """Broker symbol specification extracted from MT5."""
    def __init__(
        self,
        name: str,
        digits: int,
        point: float,
        tick_size: float,
        tick_value: float,
        contract_size: float,
        volume_min: float,
        volume_max: float,
        volume_step: float,
        trade_stops_level: int,   # min distance in points
        spread: int,              # in points
        currency_profit: str,
        currency_margin: str,
    ) -> None:
        self.name = name
        self.digits = digits
        self.point = point
        self.tick_size = tick_size
        self.tick_value = tick_value
        self.contract_size = contract_size
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.volume_step = volume_step
        self.trade_stops_level = trade_stops_level
        self.spread = spread
        self.currency_profit = currency_profit
        self.currency_margin = currency_margin

    @property
    def spread_pips(self) -> float:
        """Spread expressed as pips (1 pip = 1 point for 5-digit brokers)."""
        return self.spread * self.point

    def __repr__(self) -> str:
        return (
            f"SymbolInfo({self.name}, digits={self.digits}, "
            f"vol_min={self.volume_min}, vol_step={self.volume_step})"
        )


class MarketDataProtocol(Protocol):
    """Interface any market data adapter must satisfy."""

    def connect(self) -> bool: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def get_candles(
        self, symbol: str, timeframe: str, count: int
    ) -> list[Candle]: ...
    def get_symbol_info(self, symbol: str) -> SymbolInfo | None: ...
    def get_available_symbols(self) -> list[str]: ...
    def get_tick(self, symbol: str) -> dict | None: ...
    def get_account_info(self) -> dict | None: ...


class MT5DataAdapter:
    """
    Live adapter using the official MetaTrader5 Python package.

    - Only returns COMPLETED candles (strips the forming bar).
    - Raises RuntimeError if MT5 is unavailable rather than returning empty data.
    """

    def __init__(self, terminal_path: str | None = None) -> None:
        self._terminal_path = terminal_path
        self._connected = False

    def connect(self) -> bool:
        try:
            import MetaTrader5 as mt5
            kwargs: dict = {"timeout": 3000}
            if self._terminal_path:
                kwargs["path"] = self._terminal_path
            ok = mt5.initialize(**kwargs)
            if not ok:
                err = mt5.last_error()
                log.error("mt5_init_failed", error=err)
                return False
            self._connected = True
            info = mt5.account_info()
            log.info(
                "mt5_connected",
                login=info.login if info else "unknown",
                server=info.server if info else "unknown",
            )
            return True
        except ImportError:
            log.error("mt5_not_installed")
            return False
        except Exception as exc:
            log.error("mt5_connect_error", exc=str(exc))
            return False

    def disconnect(self) -> None:
        try:
            import MetaTrader5 as mt5
            mt5.shutdown()
        except Exception:
            pass
        self._connected = False

    def is_connected(self) -> bool:
        if not self._connected:
            return False
        try:
            import MetaTrader5 as mt5
            return mt5.terminal_info() is not None
        except Exception:
            return False

    def get_candles(
        self, symbol: str, timeframe: str, count: int
    ) -> list[Candle]:
        """
        Return the last `count` COMPLETED H1 candles for `symbol`.

        The live bar (last element in MT5's response) is always stripped.
        Raises RuntimeError if MT5 is unreachable or returns no data.
        """
        import MetaTrader5 as mt5
        tf_int = _MT5_TIMEFRAME_MAP.get(timeframe)
        if tf_int is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        # Request count+1 so after stripping the live bar we still have `count`
        rates = mt5.copy_rates_from_pos(symbol, tf_int, 0, count + 1)
        if rates is None or len(rates) == 0:
            err = mt5.last_error()
            raise RuntimeError(
                f"MT5 returned no data for {symbol}/{timeframe}: {err}"
            )

        # Strip last (forming) bar
        completed = rates[:-1]

        candles: list[Candle] = []
        for r in completed:
            ts = datetime.fromtimestamp(r["time"], tz=timezone.utc)
            candles.append(
                Candle(
                    time=ts,
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r["tick_volume"]),
                    symbol=symbol,
                    timeframe=timeframe,
                )
            )
        return candles

    def get_symbol_info(self, symbol: str) -> SymbolInfo | None:
        import MetaTrader5 as mt5
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        return SymbolInfo(
            name=info.name,
            digits=info.digits,
            point=info.point,
            tick_size=info.trade_tick_size,
            tick_value=info.trade_tick_value,
            contract_size=info.trade_contract_size,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
            volume_step=info.volume_step,
            trade_stops_level=info.trade_stops_level,
            spread=info.spread,
            currency_profit=info.currency_profit,
            currency_margin=info.currency_margin,
        )

    def get_available_symbols(self) -> list[str]:
        import MetaTrader5 as mt5
        symbols = mt5.symbols_get()
        if symbols is None:
            return []
        return sorted(s.name for s in symbols)

    def get_tick(self, symbol: str) -> dict | None:
        import MetaTrader5 as mt5
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "time": datetime.fromtimestamp(tick.time, tz=timezone.utc),
            "volume": tick.volume,
        }

    def get_account_info(self) -> dict | None:
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
            "free_margin": info.margin_free,
            "currency": info.currency,
            "leverage": info.leverage,
        }


class HistoricalDataAdapter:
    """
    Offline adapter wrapping pre-loaded DataFrames.

    Used by the backtesting engine and unit tests. Never touches MT5.
    """

    def __init__(self, candles_by_symbol: dict[str, list[Candle]]) -> None:
        self._data = candles_by_symbol

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        pass

    def is_connected(self) -> bool:
        return True

    def get_candles(
        self, symbol: str, timeframe: str, count: int
    ) -> list[Candle]:
        candles = self._data.get(symbol, [])
        return candles[-count:] if count < len(candles) else list(candles)

    def get_symbol_info(self, symbol: str) -> SymbolInfo | None:
        # Return sensible defaults for back-test use
        if "GOLD" in symbol.upper() or "XAU" in symbol.upper():
            return SymbolInfo(
                name=symbol, digits=2, point=0.01, tick_size=0.01,
                tick_value=1.0, contract_size=100.0,
                volume_min=0.01, volume_max=500.0, volume_step=0.01,
                trade_stops_level=0, spread=20, currency_profit="USD",
                currency_margin="USD",
            )
        if "BTC" in symbol.upper():
            return SymbolInfo(
                name=symbol, digits=2, point=0.01, tick_size=0.01,
                tick_value=1.0, contract_size=1.0,
                volume_min=0.01, volume_max=10.0, volume_step=0.01,
                trade_stops_level=0, spread=5000, currency_profit="USD",
                currency_margin="USD",
            )
        return None

    def get_available_symbols(self) -> list[str]:
        return list(self._data.keys())

    def get_tick(self, symbol: str) -> dict | None:
        candles = self._data.get(symbol)
        if not candles:
            return None
        last = candles[-1]
        return {
            "bid": last.close,
            "ask": last.close,
            "last": last.close,
            "time": last.time,
            "volume": last.volume,
        }

    def get_account_info(self) -> dict | None:
        return {
            "login": 0,
            "server": "backtest",
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
            "currency": "USD",
            "leverage": 100,
        }
