"""
Technical indicators computed from completed candle data.

All functions are pure: given the same candle list they return the same value.
No external state, no clock reads, no MT5 calls.
"""
from __future__ import annotations

from src.data.candle import Candle


def true_range(prev_close: float, high: float, low: float) -> float:
    """
    Wilder true range for a single bar.

    TR = max(high - low,
             abs(high - prev_close),
             abs(low  - prev_close))
    """
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(candles: list[Candle], period: int = 14) -> float | None:
    """
    Simple (non-Wilder-smoothed) ATR over `period` completed candles.

    Returns None when there are fewer than `period + 1` candles (need
    at least one previous close to compute the first true range).

    The last candle in the list must be a completed bar (callers must
    strip the forming bar first — see R3).

    Args:
        candles: List of completed Candle objects, oldest first.
        period:  Number of bars to average (default 14 per R8).

    Returns:
        Average True Range as a float, or None if insufficient data.
    """
    if period < 1:
        raise ValueError(f"ATR period must be >= 1, got {period}")
    # Need `period` true ranges, each requiring a previous close → period+1 candles
    if len(candles) < period + 1:
        return None

    # Use the most recent `period + 1` candles
    window = candles[-(period + 1):]
    trs: list[float] = []
    for i in range(1, len(window)):
        tr = true_range(
            prev_close=window[i - 1].close,
            high=window[i].high,
            low=window[i].low,
        )
        trs.append(tr)

    return sum(trs) / len(trs)
