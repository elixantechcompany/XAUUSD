"""
Market Clarity Engine — STRATEGY_SPEC.md v1.2

Evaluates the quality of an existing trading setup on a 0–100 scale.
Does NOT independently generate entry signals.
A high score is NOT a probability of winning.

Rules implemented: R97–R100 (v1.2)

All components are independently calculated and individually logged.
The score is deterministic: same inputs → same score every time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.data.candle import Candle
from src.data.indicators import atr as compute_atr
from src.strategy.strategy_core import (
    FVG, LiquiditySweep, ReferenceCandle, Swing, SwingDetector,
)
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# ── Score component IDs ───────────────────────────────────────────────────────
MCS_FVG_VALID          = "MCS-1"
MCS_SWEEP_CONFIRMED    = "MCS-2"
MCS_STRUCTURE_BREAK    = "MCS-3"
MCS_DISTANCE_TO_OPP    = "MCS-4"
MCS_DISPLACEMENT       = "MCS-5"
MCS_H4_ALIGNMENT       = "MCS-6"
MCS_SPREAD_VOLATILITY  = "MCS-7"

COMPONENT_MAX_SCORES = {
    MCS_FVG_VALID:       20,
    MCS_SWEEP_CONFIRMED: 20,
    MCS_STRUCTURE_BREAK: 20,
    MCS_DISTANCE_TO_OPP: 15,
    MCS_DISPLACEMENT:    10,
    MCS_H4_ALIGNMENT:    10,
    MCS_SPREAD_VOLATILITY: 5,
}


@dataclass
class ClarityComponent:
    """Result for one scoring component."""
    component_id: str
    points_awarded: int
    points_max: int
    passed: bool
    reason: str


@dataclass
class ClarityResult:
    """
    Full Market Clarity Score result for one setup evaluation.

    A high score is NOT a probability of winning.
    """
    score: int                          # 0–100
    components: list[ClarityComponent]
    grade: Literal["A", "B", "C", "REJECTED"]
    positions_permitted: int            # 0, 1, or 2
    rejection_reason: str               # empty string when not rejected

    # Derived clarity thresholds used (for audit trail)
    threshold_reject: int
    threshold_one:    int
    threshold_two:    int
    threshold_high:   int

    @property
    def approved(self) -> bool:
        return self.grade != "REJECTED"

    def component_by_id(self, cid: str) -> ClarityComponent | None:
        for c in self.components:
            if c.component_id == cid:
                return c
        return None


class MarketClarityEngine:
    """
    Computes the Market Clarity Score (MCS) for a validated trading setup.

    Usage:
        engine = MarketClarityEngine(settings)
        result = engine.evaluate(
            fvg, sweep, ref_candle, trigger_fired,
            entry_price, sl_price, tp1_price,
            h1_candles, h4_candles, current_spread_pips, atr_period
        )

    Rules: R97–R100 (spec v1.2)
    """

    def __init__(
        self,
        clarity_reject_below: int = 60,
        clarity_one_position: int = 60,
        clarity_two_positions: int = 75,
        clarity_high_confluence: int = 85,
        grade_a_min_score: int = 85,
        grade_b_min_score: int = 60,
        grade_a_risk_pct: float = 1.5,
        grade_b_risk_pct: float = 1.0,
        grade_a_risk_pct_max: float = 1.5,
        displacement_body_pct: float = 0.60,
        tp1_min_rr: float = 2.0,
        h4_trend_filter_enabled: bool = True,
        atr_period: int = 14,
    ) -> None:
        self.reject_below        = clarity_reject_below
        self.one_position_min    = clarity_one_position
        self.two_positions_min   = clarity_two_positions
        self.high_confluence_min = clarity_high_confluence
        self.grade_a_min         = grade_a_min_score
        self.grade_b_min         = grade_b_min_score
        self.grade_a_risk        = grade_a_risk_pct
        self.grade_b_risk        = grade_b_risk_pct
        self.grade_a_max         = grade_a_risk_pct_max
        self.displacement_body   = displacement_body_pct
        self.tp1_min_rr          = tp1_min_rr
        self.h4_filter_enabled   = h4_trend_filter_enabled
        self.atr_period          = atr_period

    # ── Public API ─────────────────────────────────────────────────────────────

    def evaluate(
        self,
        fvg: FVG,
        sweep: LiquiditySweep | None,
        ref_candle: ReferenceCandle | None,
        trigger_fired: bool,
        entry_price: float,
        sl_price: float,
        tp1_price: float | None,
        h1_candles: list[Candle],
        h4_candles: list[Candle],
        current_spread_pips: float,
        max_spread_pips: float,
    ) -> ClarityResult:
        """
        Evaluate Market Clarity Score for a setup.

        Args:
            fvg:                  Confirmed H1 FVG object
            sweep:                Confirmed liquidity sweep (or None)
            ref_candle:           Frozen reference candle (or None)
            trigger_fired:        Whether M15/H1 trigger has fired
            entry_price:          Proposed entry price
            sl_price:             Calculated SL price
            tp1_price:            Calculated TP1 price (or None if unavailable)
            h1_candles:           Completed H1 candles (for ATR, swing detection)
            h4_candles:           Completed H4 candles (for trend detection)
            current_spread_pips:  Live spread in pips
            max_spread_pips:      Configured maximum spread limit

        Returns:
            ClarityResult with score, grade, positions_permitted
        """
        direction = fvg.direction
        components: list[ClarityComponent] = []

        # MCS-1: Valid H1 FVG (20 pts)
        components.append(self._score_fvg(fvg))

        # MCS-2: Confirmed liquidity sweep (20 pts)
        components.append(self._score_sweep(sweep))

        # MCS-3: Confirmed structure break / trigger (20 pts)
        components.append(self._score_structure_break(trigger_fired, ref_candle))

        # MCS-4: Distance to opposing liquidity (15 pts)
        components.append(
            self._score_distance_to_opposing(
                direction, entry_price, sl_price, tp1_price, h1_candles
            )
        )

        # MCS-5: Strong displacement candle (10 pts)
        components.append(self._score_displacement(sweep))

        # MCS-6: H4 directional alignment (10 pts)
        components.append(self._score_h4_alignment(direction, h4_candles))

        # MCS-7: Spread and volatility (5 pts)
        components.append(
            self._score_spread_volatility(current_spread_pips, max_spread_pips, h1_candles)
        )

        total_score = sum(c.points_awarded for c in components)

        grade, risk_pct = self._determine_grade(total_score)
        positions = self._determine_positions(total_score)

        rejection_reason = ""
        if grade == "REJECTED":
            rejection_reason = (
                f"Insufficient market clarity: score={total_score} < "
                f"threshold={self.reject_below}"
            )

        result = ClarityResult(
            score=total_score,
            components=components,
            grade=grade,
            positions_permitted=positions,
            rejection_reason=rejection_reason,
            threshold_reject=self.reject_below,
            threshold_one=self.one_position_min,
            threshold_two=self.two_positions_min,
            threshold_high=self.high_confluence_min,
        )

        log.info(
            "clarity_score_computed",
            symbol=fvg.symbol,
            direction=direction,
            score=total_score,
            grade=grade,
            positions=positions,
            components={c.component_id: c.points_awarded for c in components},
        )

        return result

    # ── Component scorers ──────────────────────────────────────────────────────

    def _score_fvg(self, fvg: FVG) -> ClarityComponent:
        """MCS-1: Valid H1 FVG — 20 pts if FVG exists and size filter passes."""
        passed = fvg is not None and fvg.size > 0
        return ClarityComponent(
            MCS_FVG_VALID,
            points_awarded=20 if passed else 0,
            points_max=20,
            passed=passed,
            reason="Valid H1 FVG confirmed" if passed else "No valid FVG",
        )

    def _score_sweep(self, sweep: LiquiditySweep | None) -> ClarityComponent:
        """MCS-2: Confirmed liquidity sweep — 20 pts."""
        passed = sweep is not None
        return ClarityComponent(
            MCS_SWEEP_CONFIRMED,
            points_awarded=20 if passed else 0,
            points_max=20,
            passed=passed,
            reason="Liquidity sweep confirmed" if passed else "No confirmed sweep",
        )

    def _score_structure_break(
        self, trigger_fired: bool, ref_candle: ReferenceCandle | None
    ) -> ClarityComponent:
        """MCS-3: Confirmed structure break — 20 pts when trigger has fired."""
        passed = trigger_fired and ref_candle is not None and ref_candle.frozen
        return ClarityComponent(
            MCS_STRUCTURE_BREAK,
            points_awarded=20 if passed else 0,
            points_max=20,
            passed=passed,
            reason=(
                "Structure break confirmed (trigger fired)" if passed
                else "Trigger not yet fired or reference candle not frozen"
            ),
        )

    def _score_distance_to_opposing(
        self,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp1_price: float | None,
        candles: list[Candle],
    ) -> ClarityComponent:
        """MCS-4: Sufficient distance to opposing liquidity — 15 pts if TP1 ≥ 2×SL distance."""
        if tp1_price is None:
            return ClarityComponent(
                MCS_DISTANCE_TO_OPP, 0, 15, False,
                "No structural TP1 identified",
            )
        sl_dist = abs(entry_price - sl_price)
        tp_dist = abs(tp1_price - entry_price)
        rr = tp_dist / sl_dist if sl_dist > 0 else 0.0
        passed = rr >= self.tp1_min_rr
        return ClarityComponent(
            MCS_DISTANCE_TO_OPP,
            points_awarded=15 if passed else 0,
            points_max=15,
            passed=passed,
            reason=(
                f"TP1 R:R={rr:.2f} >= min {self.tp1_min_rr:.1f}" if passed
                else f"TP1 R:R={rr:.2f} < min {self.tp1_min_rr:.1f}"
            ),
        )

    def _score_displacement(
        self, sweep: LiquiditySweep | None
    ) -> ClarityComponent:
        """
        MCS-5: Strong displacement candle — 10 pts.

        Displacement = sweep candle body ≥ 60% of candle range.
        R99: displacement_body_pct threshold.
        """
        if sweep is None:
            return ClarityComponent(MCS_DISPLACEMENT, 0, 10, False, "No sweep candle")

        candle = sweep.sweep_candle
        candle_range = candle.high - candle.low
        if candle_range <= 0:
            return ClarityComponent(MCS_DISPLACEMENT, 0, 10, False, "Zero-range sweep candle")

        body = abs(candle.close - candle.open)
        body_pct = body / candle_range
        passed = body_pct >= self.displacement_body
        return ClarityComponent(
            MCS_DISPLACEMENT,
            points_awarded=10 if passed else 0,
            points_max=10,
            passed=passed,
            reason=(
                f"Sweep candle body={body_pct:.1%} >= {self.displacement_body:.0%}" if passed
                else f"Weak displacement: body={body_pct:.1%} < {self.displacement_body:.0%}"
            ),
        )

    def _score_h4_alignment(
        self, direction: str, h4_candles: list[Candle]
    ) -> ClarityComponent:
        """
        MCS-6: H4 directional alignment — 10 pts.

        R97: H4 bullish trend = higher highs + higher lows on confirmed swings.
        """
        if not self.h4_filter_enabled:
            return ClarityComponent(
                MCS_H4_ALIGNMENT, 10, 10, True,
                "H4 trend filter disabled — full points awarded"
            )

        trend = _detect_h4_trend(h4_candles, left_bars=2, right_bars=2)

        if direction == "BULLISH":
            passed = trend == "BULLISH"
        else:
            passed = trend == "BEARISH"

        return ClarityComponent(
            MCS_H4_ALIGNMENT,
            points_awarded=10 if passed else 0,
            points_max=10,
            passed=passed,
            reason=(
                f"H4 trend={trend} aligns with {direction}" if passed
                else f"H4 trend={trend} does not align with {direction} (R97)"
            ),
        )

    def _score_spread_volatility(
        self,
        spread_pips: float,
        max_spread_pips: float,
        candles: list[Candle],
    ) -> ClarityComponent:
        """
        MCS-7: Spread and volatility — 5 pts.

        Passes when spread ≤ max_spread AND ATR is computable (market is active).
        """
        spread_ok = spread_pips <= max_spread_pips
        atr_val = compute_atr(candles, self.atr_period)
        atr_ok  = atr_val is not None and atr_val > 0

        passed = spread_ok and atr_ok
        reason_parts = []
        if not spread_ok:
            reason_parts.append(f"Spread {spread_pips:.1f} > limit {max_spread_pips:.1f}")
        if not atr_ok:
            reason_parts.append("ATR unavailable")
        if passed:
            reason_parts.append(f"Spread {spread_pips:.1f} OK, ATR {atr_val:.4f}")

        return ClarityComponent(
            MCS_SPREAD_VOLATILITY,
            points_awarded=5 if passed else 0,
            points_max=5,
            passed=passed,
            reason="; ".join(reason_parts),
        )

    # ── Grade and position determination ──────────────────────────────────────

    def _determine_grade(
        self, score: int
    ) -> tuple[Literal["A", "B", "C", "REJECTED"], float]:
        if score < self.reject_below:
            return "REJECTED", 0.0
        if score >= self.grade_a_min:
            return "A", self.grade_a_risk
        return "B", self.grade_b_risk

    def _determine_positions(self, score: int) -> int:
        if score < self.reject_below:
            return 0
        if score >= self.two_positions_min:
            return 2
        return 1

    def risk_pct_for_grade(self, grade: str) -> float:
        """Return the risk percentage for a given grade."""
        if grade == "A":
            return min(self.grade_a_risk, self.grade_a_max)
        if grade == "B":
            return self.grade_b_risk
        return 0.0


# ── H4 trend detection (R97) ──────────────────────────────────────────────────

def _detect_h4_trend(
    h4_candles: list[Candle],
    left_bars: int = 2,
    right_bars: int = 2,
) -> Literal["BULLISH", "BEARISH", "NEUTRAL"]:
    """
    R97: detect H4 trend from confirmed swing structure.

    Bullish: most recent confirmed swing low > previous swing low
             AND most recent confirmed swing high > previous swing high.
    Bearish: lower highs AND lower lows.
    Neutral: insufficient data or mixed structure.
    """
    if len(h4_candles) < (left_bars + 1 + right_bars) * 2:
        return "NEUTRAL"

    detector = SwingDetector(left_bars=left_bars, right_bars=right_bars)
    swings = detector.find_swings(h4_candles)

    highs = [s for s in swings if s.direction == "HIGH"]
    lows  = [s for s in swings if s.direction == "LOW"]

    if len(highs) < 2 or len(lows) < 2:
        return "NEUTRAL"

    # Compare two most recent confirmed highs and lows
    prev_high, last_high = highs[-2], highs[-1]
    prev_low,  last_low  = lows[-2],  lows[-1]

    higher_highs = last_high.level > prev_high.level
    higher_lows  = last_low.level  > prev_low.level
    lower_highs  = last_high.level < prev_high.level
    lower_lows   = last_low.level  < prev_low.level

    if higher_highs and higher_lows:
        return "BULLISH"
    if lower_highs and lower_lows:
        return "BEARISH"
    return "NEUTRAL"
