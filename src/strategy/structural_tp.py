"""
Structural Take-Profit Detection — STRATEGY_SPEC.md v1.2

Identifies TP1 and TP2 from actual market structure.
Does NOT use arbitrary pip distances.
Does NOT fabricate a target when structure cannot be found.

Rules: R101, R102, R103 (v1.2)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from src.data.candle import Candle
from src.data.indicators import atr as compute_atr
from src.strategy.strategy_core import FVG, Swing, SwingDetector
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class StructuralTarget:
    """One identified structural take-profit target."""
    price: float
    structure_type: str       # "swing_high", "swing_low", "fvg_boundary", "liquidity"
    candle_time: object       # datetime — time of the structural candle
    rr_ratio: float           # actual R:R against the setup SL
    meets_minimum: bool       # True when rr_ratio >= required minimum


@dataclass
class StructuralTPResult:
    """
    Output of structural TP detection for one setup.

    tp1 and tp2 may be None when no valid structure is found.
    rejection_reason is non-empty when neither TP qualifies.
    """
    tp1: StructuralTarget | None
    tp2: StructuralTarget | None
    # All identified barriers between entry and TP2, for the decision log
    all_barriers: list[StructuralTarget]
    rejection_reason: str   # empty when at least TP1 found


class StructuralTPDetector:
    """
    Identifies TP1 and TP2 from H1 swing structure and FVGs.

    R101: For bullish setups, finds the nearest H1 swing high above entry.
    R102: TP1 = 2 ticks before the first structural barrier, minimum 1:2 R:R.
    R103: TP2 = 2 ticks before the second structural barrier, minimum 1:3 R:R.
    """

    def __init__(
        self,
        tp1_min_rr: float = 2.0,
        tp2_min_rr: float = 3.0,
        tp2_min_atr_distance: float = 3.0,
        tick_size: float = 0.01,
        atr_period: int = 14,
        pivot_left_bars: int = 2,
        pivot_right_bars: int = 2,
    ) -> None:
        self.tp1_min_rr           = tp1_min_rr
        self.tp2_min_rr           = tp2_min_rr
        self.tp2_min_atr_distance = tp2_min_atr_distance
        self.tick_size            = tick_size
        self.atr_period           = atr_period
        self._swing_det = SwingDetector(
            left_bars=pivot_left_bars,
            right_bars=pivot_right_bars,
        )

    # ── Public ─────────────────────────────────────────────────────────────────

    def detect(
        self,
        direction: str,
        entry_price: float,
        sl_price: float,
        h1_candles: list[Candle],
        active_fvgs: list[FVG] | None = None,
    ) -> StructuralTPResult:
        """
        Find TP1 and TP2 from market structure.

        R101: Identifies opposing swing highs/lows and FVG boundaries above/below entry.
        R102/R103: Applies 2-tick conservative offset and R:R filter.

        Returns StructuralTPResult.
        """
        sl_distance = abs(entry_price - sl_price)
        if sl_distance <= 0:
            return StructuralTPResult(
                None, None, [],
                "SL distance is zero — cannot compute TP targets",
            )

        atr_val = compute_atr(h1_candles, self.atr_period)

        # Collect all structural barriers in the direction of the trade
        barriers = self._collect_barriers(
            direction, entry_price, h1_candles, active_fvgs or []
        )

        if not barriers:
            return StructuralTPResult(
                None, None, [],
                f"No valid opposing structure found above/below entry {entry_price:.5f} (R101)",
            )

        # Sort by distance from entry (nearest first)
        if direction == "BULLISH":
            barriers.sort(key=lambda b: b.price)
        else:
            barriers.sort(key=lambda b: b.price, reverse=True)

        # Compute R:R for each barrier and tag the result
        tagged: list[StructuralTarget] = []
        for b in barriers:
            tp_dist = abs(b.price - entry_price)
            rr = tp_dist / sl_distance if sl_distance > 0 else 0.0
            tagged.append(StructuralTarget(
                price=b.price,
                structure_type=b.structure_type,
                candle_time=b.candle_time,
                rr_ratio=round(rr, 3),
                meets_minimum=rr >= self.tp1_min_rr,
            ))

        # TP1 — nearest barrier meeting tp1_min_rr
        tp1 = next((t for t in tagged if t.rr_ratio >= self.tp1_min_rr), None)
        if tp1 is None:
            return StructuralTPResult(
                None, None, tagged,
                f"No structural barrier meets minimum {self.tp1_min_rr}:1 R:R "
                f"(nearest R:R={tagged[0].rr_ratio:.2f}) — setup rejected (R102)",
            )

        # TP2 — next barrier beyond TP1 that meets tp2_min_rr
        remaining = [t for t in tagged if t.price != tp1.price]
        if direction == "BULLISH":
            remaining = [t for t in remaining if t.price > tp1.price]
        else:
            remaining = [t for t in remaining if t.price < tp1.price]

        tp2_candidates = [t for t in remaining if t.rr_ratio >= self.tp2_min_rr]

        tp2 = None
        if tp2_candidates:
            tp2_candidate = tp2_candidates[0]
            # R104: TP2 distance must also be ≥ tp2_min_atr_distance × ATR
            if atr_val is not None:
                tp2_atr_dist = abs(tp2_candidate.price - entry_price) / atr_val
                if tp2_atr_dist >= self.tp2_min_atr_distance:
                    tp2 = tp2_candidate
                else:
                    log.debug(
                        "tp2_atr_distance_too_small",
                        tp2_atr_dist=tp2_atr_dist,
                        required=self.tp2_min_atr_distance,
                    )
            else:
                tp2 = tp2_candidate   # ATR unavailable — accept without ATR check

        log.info(
            "structural_tp_detected",
            direction=direction,
            entry=entry_price,
            sl=sl_price,
            tp1_price=tp1.price if tp1 else None,
            tp1_rr=tp1.rr_ratio if tp1 else None,
            tp2_price=tp2.price if tp2 else None,
            tp2_rr=tp2.rr_ratio if tp2 else None,
            barriers_found=len(tagged),
        )

        return StructuralTPResult(
            tp1=tp1,
            tp2=tp2,
            all_barriers=tagged,
            rejection_reason="",
        )

    # ── Internal ───────────────────────────────────────────────────────────────

    def _collect_barriers(
        self,
        direction: str,
        entry_price: float,
        candles: list[Candle],
        active_fvgs: list[FVG],
    ) -> list[StructuralTarget]:
        """
        R101: Collect all structural barriers in the direction of the trade.

        For bullish: swing highs above entry, bearish FVG lower boundaries above entry.
        For bearish: swing lows below entry, bullish FVG upper boundaries below entry.
        """
        barriers: list[StructuralTarget] = []
        offset = self.tick_size * 2   # 2-tick conservative offset

        # ── Swing structure (R101) ────────────────────────────────────────────
        swings = self._swing_det.find_swings(candles)

        for swing in swings:
            if direction == "BULLISH" and swing.direction == "HIGH":
                # Place TP just before the swing high (conservative)
                tp_price = swing.level - offset
                if tp_price > entry_price:
                    barriers.append(StructuralTarget(
                        price=tp_price,
                        structure_type="swing_high",
                        candle_time=swing.confirmed_at,
                        rr_ratio=0.0,   # computed later
                        meets_minimum=False,
                    ))

            elif direction == "BEARISH" and swing.direction == "LOW":
                tp_price = swing.level + offset
                if tp_price < entry_price:
                    barriers.append(StructuralTarget(
                        price=tp_price,
                        structure_type="swing_low",
                        candle_time=swing.confirmed_at,
                        rr_ratio=0.0,
                        meets_minimum=False,
                    ))

        # ── Opposing FVG boundaries (R101) ────────────────────────────────────
        for fvg in active_fvgs:
            if direction == "BULLISH" and fvg.direction == "BEARISH":
                # Bearish FVG above entry = potential resistance
                # Place TP before the bottom of the bearish FVG
                tp_price = fvg.fvg_low - offset
                if tp_price > entry_price:
                    barriers.append(StructuralTarget(
                        price=tp_price,
                        structure_type="fvg_boundary",
                        candle_time=fvg.c3_time,
                        rr_ratio=0.0,
                        meets_minimum=False,
                    ))

            elif direction == "BEARISH" and fvg.direction == "BULLISH":
                # Bullish FVG below entry = potential support
                tp_price = fvg.fvg_high + offset
                if tp_price < entry_price:
                    barriers.append(StructuralTarget(
                        price=tp_price,
                        structure_type="fvg_boundary",
                        candle_time=fvg.c3_time,
                        rr_ratio=0.0,
                        meets_minimum=False,
                    ))

        # Deduplicate by price (keep the first occurrence)
        seen: set[float] = set()
        unique: list[StructuralTarget] = []
        for b in barriers:
            rnd = round(b.price, 5)
            if rnd not in seen:
                seen.add(rnd)
                unique.append(b)

        return unique
