"""
Agent 4: The Skeptic — Adversarial Trade Validator with VETO Authority

Role:
- Acts as an independent counter-argument challenger.
- Exercises explicit VETO authority to kill flawed trade proposals before risk allocation.
- Checks for:
  1. Overextended price action (chasing market far from mean).
  2. Adverse spread-to-SL ratio (spread eating excessive portion of stop loss).
  3. Unfavorable session timing (illiquid rollover windows 21:00–23:59 UTC).
  4. Contradictory price action (exhaustion wicks on trigger candle).
  5. Macroeconomic blackout alignment (reinforcing News Analyst).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.agents.news_analyst import NewsReport
from src.agents.scout import ScoutReport
from src.data.candle import Candle
from src.strategy.part3_strategy import Part3TradeSignal
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class SkepticReport:
    """Structured report produced by The Skeptic."""
    veto: bool                  # True if The Skeptic blocks the trade
    confidence_score: float     # 0.0 (unconfident/rejected) to 1.0 (high confidence)
    concerns: list[str]
    approval_recommendation: bool
    reasoning: str


class SkepticAgent:
    """
    Agent 4: The Skeptic.
    Has full VETO authority. If veto=True, Coordinator must reject the setup.
    """

    def __init__(
        self,
        max_spread_sl_ratio: float = 0.15,      # Spread should not exceed 15% of SL distance
        max_exhaustion_wick_ratio: float = 0.50, # Rejection wick should not exceed 50% of candle range
        prohibit_rollover: bool = True,          # Prohibit entries during 21:00-23:59 UTC
    ) -> None:
        self.max_spread_sl_ratio = max_spread_sl_ratio
        self.max_exhaustion_wick_ratio = max_exhaustion_wick_ratio
        self.prohibit_rollover = prohibit_rollover

    def challenge(
        self,
        signal: Part3TradeSignal,
        candles: list[Candle],
        scout_report: ScoutReport | None = None,
        news_report: NewsReport | None = None,
        current_spread_pips: float = 0.0,
    ) -> SkepticReport:
        """
        Interrogate the trade proposal and determine whether to exercise VETO.
        """
        concerns: list[str] = []
        veto = False
        confidence = 1.0

        sl_distance = abs(signal.entry_price - signal.sl_price)

        # 1. Macroeconomic Event Check
        if news_report is not None:
            if news_report.blackout_active:
                concerns.append(f"VETO: News blackout active for '{news_report.active_blackout_event.name if news_report.active_blackout_event else 'Unknown'}'")
                veto = True
                confidence = 0.0
            elif news_report.status == "UNKNOWN":
                concerns.append("WARNING: Economic calendar is stale or unavailable. High caution.")
                confidence -= 0.25

        # 2. Session & Rollover Check
        if scout_report is not None:
            if scout_report.is_rollover_window and self.prohibit_rollover:
                concerns.append("VETO: Trade occurs during illiquid rollover window (21:00-23:59 UTC). High slippage risk.")
                veto = True
                confidence = 0.0
            elif not scout_report.is_core_session:
                concerns.append(f"CAUTION: Non-core trading session ({scout_report.session_name}). Volume may be subdued.")
                confidence -= 0.15

        # 3. Spread-to-SL Distance Check
        if current_spread_pips > 0 and sl_distance > 0:
            # Estimate pip spread in price terms (for 5-digit / 2-digit)
            # Assuming point = 0.01 for gold/crypto, spread_price = current_spread_pips * 0.01
            spread_ratio = (current_spread_pips * 0.01) / sl_distance
            if spread_ratio > self.max_spread_sl_ratio:
                concerns.append(
                    f"VETO: Spread-to-SL ratio ({spread_ratio:.1%}) exceeds maximum threshold ({self.max_spread_sl_ratio:.1%})."
                )
                veto = True
                confidence = 0.0
            elif spread_ratio > 0.08:
                concerns.append(f"CAUTION: Elevated spread ratio ({spread_ratio:.1%}).")
                confidence -= 0.10

        # 4. Trigger Candle Exhaustion Wick Check
        if candles:
            last = candles[-1]
            candle_range = last.high - last.low
            if candle_range > 0:
                if signal.direction == "BULLISH":
                    upper_wick = last.high - max(last.open, last.close)
                    wick_ratio = upper_wick / candle_range
                    if wick_ratio > self.max_exhaustion_wick_ratio:
                        concerns.append(
                            f"VETO: Bullish trigger candle shows {wick_ratio:.1%} upper exhaustion wick."
                        )
                        veto = True
                        confidence = 0.0
                elif signal.direction == "BEARISH":
                    lower_wick = min(last.open, last.close) - last.low
                    wick_ratio = lower_wick / candle_range
                    if wick_ratio > self.max_exhaustion_wick_ratio:
                        concerns.append(
                            f"VETO: Bearish trigger candle shows {wick_ratio:.1%} lower exhaustion wick."
                        )
                        veto = True
                        confidence = 0.0

        # 5. Overextended Price Action Check (distance from 20-period moving average)
        if len(candles) >= 20:
            sma20 = sum(c.close for c in candles[-20:]) / 20.0
            atr_est = scout_report.atr if scout_report else (candles[-1].high - candles[-1].low)
            dist_from_mean = abs(signal.entry_price - sma20)
            if atr_est > 0 and (dist_from_mean / atr_est) > 3.5:
                concerns.append(
                    f"VETO: Price is overextended {dist_from_mean / atr_est:.1f}x ATR from 20-bar mean ({sma20:.2f})."
                )
                veto = True
                confidence = 0.0

        confidence = max(min(confidence, 1.0), 0.0)
        approved = not veto

        reasoning = (
            f"Skeptic Decision: {'APPROVED' if approved else 'VETOED'}. "
            f"Confidence: {confidence:.2f}. "
            f"Concerns: {'; '.join(concerns) if concerns else 'None. Structure is clean.'}"
        )

        return SkepticReport(
            veto=veto,
            confidence_score=confidence,
            concerns=concerns,
            approval_recommendation=approved,
            reasoning=reasoning,
        )
