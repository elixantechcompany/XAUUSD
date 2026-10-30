"""
Agent 1: The Scout — Market Structure, Volatility, and Session Timing Analyst

Role:
- Scans price action and market structure without lookahead.
- Identifies active trading session and liquidity regimes (London, NY, Asian, Rollover).
- Classifies volatility state (LOW, NORMAL, HIGH) via ATR.
- Identifies confirmed Swing Highs and Swing Lows.
- Alerts on potential liquidity sweeps approaching key structural levels.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.data.candle import Candle
from src.data.indicators import atr as compute_atr
from src.strategy.strategy_core import Swing, SwingDetector
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class ScoutReport:
    """Structured report produced by The Scout."""
    symbol: str
    timestamp: datetime
    session_name: str
    is_core_session: bool       # True during London / NY liquid sessions
    is_rollover_window: bool    # True during 21:00-23:59 UTC (spread widening risk)
    atr: float
    current_range: float
    volatility_regime: str      # "LOW", "NORMAL", "HIGH"
    latest_swing_high: float | None
    latest_swing_low: float | None
    swing_highs_count: int
    swing_lows_count: int
    notes: str


class ScoutAgent:
    """
    Agent 1: The Scout.
    Evaluates market environment and session conditions deterministically.
    """

    def __init__(
        self,
        symbol: str,
        atr_period: int = 14,
        left_bars: int = 2,
        right_bars: int = 2,
    ) -> None:
        self.symbol = symbol
        self.atr_period = atr_period
        self.swing_detector = SwingDetector(left_bars=left_bars, right_bars=right_bars)

    def analyze(self, candles: list[Candle], current_time: datetime | None = None) -> ScoutReport:
        """
        Analyze current completed candles and produce a ScoutReport.
        Candles must be closed H1 bars in chronological order.
        """
        if not candles:
            raise ValueError("ScoutAgent requires at least one candle")

        last_candle = candles[-1]
        ts = current_time if current_time is not None else last_candle.time
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # 1. Trading Session Detection (UTC)
        hour = ts.hour
        session_name = "Asian"
        is_core = False
        is_rollover = False

        if 12 <= hour < 16:
            session_name = "London/NY Overlap"
            is_core = True
        elif 7 <= hour < 16:
            session_name = "London"
            is_core = True
        elif 12 <= hour < 21:
            session_name = "New York"
            is_core = True
        elif 21 <= hour <= 23:
            session_name = "Rollover/Illiquid"
            is_rollover = True
        else:
            session_name = "Asian"

        # 2. Volatility Analysis
        atr_val = compute_atr(candles, self.atr_period)
        if atr_val is None or atr_val <= 0:
            atr_val = max(last_candle.high - last_candle.low, 0.01)

        curr_range = last_candle.high - last_candle.low
        ratio = curr_range / atr_val

        if ratio < 0.6:
            vol_regime = "LOW"
        elif ratio > 1.8:
            vol_regime = "HIGH"
        else:
            vol_regime = "NORMAL"

        # 3. Swing High / Swing Low Structural Levels
        swings = self.swing_detector.find_swings(candles)
        swing_highs = [s for s in swings if s.direction == "HIGH"]
        swing_lows = [s for s in swings if s.direction == "LOW"]

        latest_high = swing_highs[-1].level if swing_highs else None
        latest_low = swing_lows[-1].level if swing_lows else None

        notes = (
            f"Session: {session_name} ({'Core' if is_core else 'Non-Core'}). "
            f"Volatility: {vol_regime} (ATR={atr_val:.4f}, Range={curr_range:.4f}). "
            f"Swings: {len(swing_highs)} highs, {len(swing_lows)} lows."
        )

        return ScoutReport(
            symbol=self.symbol,
            timestamp=ts,
            session_name=session_name,
            is_core_session=is_core,
            is_rollover_window=is_rollover,
            atr=atr_val,
            current_range=curr_range,
            volatility_regime=vol_regime,
            latest_swing_high=latest_high,
            latest_swing_low=latest_low,
            swing_highs_count=len(swing_highs),
            swing_lows_count=len(swing_lows),
            notes=notes,
        )
