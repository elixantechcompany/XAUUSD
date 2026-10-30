"""
Core candle data structure.

A Candle is an immutable value object representing one completed OHLCV bar.
It must never be constructed from an unfinished (live) bar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Candle:
    """One completed OHLCV bar."""
    time: datetime    # bar open time (UTC)
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    timeframe: str

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(
                f"Candle high ({self.high}) < low ({self.low}) at {self.time}"
            )
        if self.high < self.open or self.high < self.close:
            raise ValueError(
                f"Candle high ({self.high}) is not the highest value at {self.time}"
            )
        if self.low > self.open or self.low > self.close:
            raise ValueError(
                f"Candle low ({self.low}) is not the lowest value at {self.time}"
            )

    @property
    def body_high(self) -> float:
        return max(self.open, self.close)

    @property
    def body_low(self) -> float:
        return min(self.open, self.close)

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def range(self) -> float:
        return self.high - self.low
