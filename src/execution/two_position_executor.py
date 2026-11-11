"""
Two-Position Execution Coordinator — STRATEGY_SPEC.md v1.2

Manages the execution of Position A (TP1) and Position B (TP2) from
a single trading setup. Both positions share the same FVG/sweep setup,
entry price, SL, and setup_id.

Rules: R104–R110 (v1.2)

Safety guarantees:
  - Both positions must never together exceed the grade risk budget.
  - Each position has an independent client order ID (IMPL4).
  - If Position A fills but Position B fails, the recovery policy is applied.
  - No live trading enabled.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from src.data.market_data_adapter import SymbolInfo
from src.strategy.market_clarity import ClarityResult
from src.strategy.structural_tp import StructuralTPResult, StructuralTarget
from src.utils.ids import order_client_id
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class PositionSpec:
    """Fully-calculated specification for one position before submission."""
    label: Literal["A", "B"]
    setup_id: str
    client_order_id: str
    symbol: str
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    volume: float
    risk_usd: float
    rr_ratio: float
    risk_pct: float


@dataclass
class TwoPositionPlan:
    """
    Complete execution plan for one setup.

    Contains Position A and optionally Position B,
    along with the total risk and the clarity score that produced it.
    """
    setup_id: str
    clarity: ClarityResult
    positions_count: int        # 1 or 2
    position_a: PositionSpec | None
    position_b: PositionSpec | None
    total_risk_usd: float
    total_risk_pct: float
    rejection_reason: str       # empty when plan is valid

    @property
    def approved(self) -> bool:
        return self.position_a is not None and not self.rejection_reason


@dataclass
class ExecutionOutcome:
    """Result after submitting one position to the executor."""
    label: Literal["A", "B"]
    submitted: bool
    filled: bool
    fill_price: float | None
    fill_volume: float | None
    broker_ticket: int | None
    sl_confirmed: bool
    rejection_reason: str
    retcode: int | None


@dataclass
class TwoPositionOutcome:
    """Combined result after executing both positions."""
    setup_id: str
    position_a: ExecutionOutcome | None
    position_b: ExecutionOutcome | None
    partial_execution: bool     # True when A filled but B failed
    total_risk_usd: float

    @property
    def fully_executed(self) -> bool:
        a_ok = self.position_a is not None and self.position_a.filled
        b_ok = self.position_b is None or self.position_b.filled
        return a_ok and b_ok


class TwoPositionSizer:
    """
    Calculates volumes for Position A and Position B.

    R105/R106: Each position gets 50% of the total setup risk budget.
    R107: Total A+B risk must never exceed the grade budget.
    """

    def __init__(self, info: SymbolInfo) -> None:
        self.info = info

    def calculate_volumes(
        self,
        entry_price: float,
        sl_price: float,
        equity: float,
        total_risk_pct: float,  # e.g. 1.0 for grade B, 1.5 for grade A
    ) -> tuple[float, float, float]:
        """
        Calculate volume for each position (A = 50%, B = 50%).

        Returns (volume_a, volume_b, actual_total_risk_usd).
        Each volume is independently rounded down to volume_step.
        """
        si = self.info
        sl_distance = abs(entry_price - sl_price)
        if sl_distance <= 0 or si.tick_size <= 0:
            return 0.0, 0.0, 0.0

        # Each position gets half the risk budget
        each_risk_usd = equity * (total_risk_pct / 100.0) * 0.5

        sl_ticks   = sl_distance / si.tick_size
        risk_per_lot = sl_ticks * si.tick_value
        if risk_per_lot <= 0:
            return 0.0, 0.0, 0.0

        raw_vol = each_risk_usd / risk_per_lot
        vol = self._round_down(raw_vol, si.volume_step, si.volume_min)
        vol = min(vol, si.volume_max)

        actual_risk_a = vol * sl_ticks * si.tick_value
        actual_risk_b = actual_risk_a  # same volume, same SL

        return vol, vol, actual_risk_a + actual_risk_b

    @staticmethod
    def _round_down(raw: float, step: float, minimum: float) -> float:
        if step <= 0:
            return max(minimum, raw)
        steps = math.floor(raw / step)
        return round(steps * step, 8)


class TwoPositionPlanner:
    """
    Builds the execution plan for a setup.

    Evaluates all R104 conditions, calculates volumes, and produces
    a TwoPositionPlan — or a rejected plan with a reason.
    """

    def __init__(
        self,
        tp1_min_rr: float = 2.0,
        tp2_min_rr: float = 3.0,
        tp2_min_atr_distance: float = 3.0,
        two_position_mode_enabled: bool = True,
        partial_execution_policy: str = "leave_a_open",
    ) -> None:
        self.tp1_min_rr            = tp1_min_rr
        self.tp2_min_rr            = tp2_min_rr
        self.tp2_min_atr_dist      = tp2_min_atr_distance
        self.two_position_enabled  = two_position_mode_enabled
        self.partial_policy        = partial_execution_policy

    def build_plan(
        self,
        setup_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        equity: float,
        clarity: ClarityResult,
        tp_result: StructuralTPResult,
        info: SymbolInfo,
        risk_pct_override: float | None = None,
    ) -> TwoPositionPlan:
        """
        Build a TwoPositionPlan.

        Returns an approved plan with position specs, or a rejected plan with reason.
        """
        # Determine risk % from grade
        risk_pct = risk_pct_override or self._risk_for_grade(clarity.grade)
        if risk_pct <= 0:
            return self._reject(setup_id, clarity, f"Grade {clarity.grade} has 0% risk allocation")

        sizer = TwoPositionSizer(info)

        # ── Check if two positions are warranted ──────────────────────────────
        can_two = (
            self.two_position_enabled
            and clarity.positions_permitted >= 2
            and tp_result.tp1 is not None
            and tp_result.tp2 is not None
        )

        if not can_two:
            # One position only
            if tp_result.tp1 is None:
                return self._reject(setup_id, clarity, tp_result.rejection_reason or "No valid TP1")

            vol, _, actual_risk = sizer.calculate_volumes(
                entry_price, sl_price, equity, risk_pct
            )
            # For single position, use full budget (not 50%)
            each_risk = equity * (risk_pct / 100.0)
            sl_ticks  = abs(entry_price - sl_price) / info.tick_size if info.tick_size > 0 else 0
            risk_per_lot = sl_ticks * info.tick_value if sl_ticks > 0 else 0
            full_vol = TwoPositionSizer._round_down(
                each_risk / risk_per_lot if risk_per_lot > 0 else 0,
                info.volume_step, info.volume_min
            )
            full_vol = min(full_vol, info.volume_max)

            if full_vol < info.volume_min:
                return self._reject(
                    setup_id, clarity,
                    f"Minimum volume {info.volume_min} exceeds risk budget — Minimum broker volume exceeds allowed risk"
                )

            rr_a = abs(tp_result.tp1.price - entry_price) / abs(entry_price - sl_price)
            pos_a = PositionSpec(
                label="A",
                setup_id=setup_id,
                client_order_id=order_client_id(setup_id, attempt=0),
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_result.tp1.price,
                volume=full_vol,
                risk_usd=full_vol * sl_ticks * info.tick_value,
                rr_ratio=round(rr_a, 3),
                risk_pct=risk_pct,
            )
            return TwoPositionPlan(
                setup_id=setup_id,
                clarity=clarity,
                positions_count=1,
                position_a=pos_a,
                position_b=None,
                total_risk_usd=pos_a.risk_usd,
                total_risk_pct=risk_pct,
                rejection_reason="",
            )

        # ── Two positions ─────────────────────────────────────────────────────
        vol_a, vol_b, total_risk = sizer.calculate_volumes(
            entry_price, sl_price, equity, risk_pct
        )

        if vol_a < info.volume_min:
            return self._reject(
                setup_id, clarity,
                f"Minimum volume {info.volume_min} exceeds 50% risk allocation — "
                "Minimum broker volume exceeds allowed risk"
            )

        sl_ticks     = abs(entry_price - sl_price) / info.tick_size if info.tick_size > 0 else 0
        risk_per_lot = sl_ticks * info.tick_value

        rr_a = abs(tp_result.tp1.price - entry_price) / abs(entry_price - sl_price)
        rr_b = abs(tp_result.tp2.price - entry_price) / abs(entry_price - sl_price)

        pos_a = PositionSpec(
            label="A",
            setup_id=setup_id,
            client_order_id=order_client_id(setup_id, attempt=0),
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_result.tp1.price,
            volume=vol_a,
            risk_usd=vol_a * risk_per_lot,
            rr_ratio=round(rr_a, 3),
            risk_pct=risk_pct / 2,
        )
        pos_b = PositionSpec(
            label="B",
            setup_id=setup_id,
            client_order_id=order_client_id(setup_id, attempt=1),
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_result.tp2.price,
            volume=vol_b,
            risk_usd=vol_b * risk_per_lot,
            rr_ratio=round(rr_b, 3),
            risk_pct=risk_pct / 2,
        )

        log.info(
            "two_position_plan_built",
            setup_id=setup_id,
            clarity_score=clarity.score,
            grade=clarity.grade,
            positions=2,
            vol_a=vol_a, tp1=tp_result.tp1.price, rr_a=rr_a,
            vol_b=vol_b, tp2=tp_result.tp2.price, rr_b=rr_b,
            total_risk=total_risk,
        )

        return TwoPositionPlan(
            setup_id=setup_id,
            clarity=clarity,
            positions_count=2,
            position_a=pos_a,
            position_b=pos_b,
            total_risk_usd=total_risk,
            total_risk_pct=risk_pct,
            rejection_reason="",
        )

    def _risk_for_grade(self, grade: str) -> float:
        """Default risk percentages from R100."""
        return {"A": 1.5, "B": 1.0, "REJECTED": 0.0, "C": 0.0}.get(grade, 0.0)

    def _reject(
        self, setup_id: str, clarity: ClarityResult, reason: str
    ) -> TwoPositionPlan:
        log.warning("two_position_plan_rejected", setup_id=setup_id, reason=reason)
        return TwoPositionPlan(
            setup_id=setup_id,
            clarity=clarity,
            positions_count=0,
            position_a=None,
            position_b=None,
            total_risk_usd=0.0,
            total_risk_pct=0.0,
            rejection_reason=reason,
        )
