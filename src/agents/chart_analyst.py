"""
Agent 3: The Chart Analyst — Quantitative Technical Strategy Evaluator

Role:
- Executes the core mathematical trading strategy (Master Specification Part 3).
- Identifies 3-candle Fair Value Gaps (FVGs), confirmed liquidity sweeps,
  preceding-candle market confirmations, FVG retracement, entering-candle locking,
  and high/low breakout executions.
- Formulates trade proposals with structural Stop-Loss and minimum 1:2 Take-Profit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.data.candle import Candle
from src.strategy.part3_strategy import Part3StrategyEngine, Part3TradeSignal
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class ChartAnalysisReport:
    """Structured report produced by The Chart Analyst."""
    symbol: str
    timestamp: datetime
    signals: list[Part3TradeSignal]
    candidate_setups_count: int
    has_actionable_signal: bool
    summary: str


class ChartAnalystAgent:
    """
    Agent 3: The Chart Analyst.
    Runs the deterministic Part 3 technical strategy.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str = "H1",
        left_bars: int = 2,
        right_bars: int = 2,
        atr_period: int = 14,
        min_fvg_atr_factor: float = 0.1,
        min_fvg_ticks: int = 2,
        tick_size: float = 0.01,
        sl_buffer_atr_factor: float = 0.05,
        sl_buffer_min_ticks: int = 2,
        trade_stops_level: int = 0,
        point: float = 0.01,
        min_rr: float = 2.0,
        max_fvg_age_bars: int = 24,
        max_setup_age_bars_after_sweep: int = 12,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy_engine = Part3StrategyEngine(
            symbol=symbol,
            timeframe=timeframe,
            left_bars=left_bars,
            right_bars=right_bars,
            atr_period=atr_period,
            min_fvg_atr_factor=min_fvg_atr_factor,
            min_fvg_ticks=min_fvg_ticks,
            tick_size=tick_size,
            sl_buffer_atr_factor=sl_buffer_atr_factor,
            sl_buffer_min_ticks=sl_buffer_min_ticks,
            trade_stops_level=trade_stops_level,
            point=point,
            min_rr=min_rr,
            max_fvg_age_bars=max_fvg_age_bars,
            max_setup_age_bars_after_sweep=max_setup_age_bars_after_sweep,
        )

    def analyze(
        self,
        candles: list[Candle],
        live_tick: dict | None = None,
        current_time: datetime | None = None,
    ) -> ChartAnalysisReport:
        """
        Evaluate completed H1 candles and identify confirmed trade signals.
        """
        if not candles:
            raise ValueError("ChartAnalystAgent requires completed candles")

        ts = current_time or candles[-1].time
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        signals = self.strategy_engine.evaluate(candles, live_tick=live_tick, now=ts)

        summary = (
            f"Evaluated {len(candles)} candles for {self.symbol}. "
            f"Found {len(signals)} confirmed Part 3 trade signal(s)."
        )

        return ChartAnalysisReport(
            symbol=self.symbol,
            timestamp=ts,
            signals=signals,
            candidate_setups_count=len(signals),
            has_actionable_signal=len(signals) > 0,
            summary=summary,
        )
