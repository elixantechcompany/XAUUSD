"""
Unit tests for TwoPositionPlanner and TwoPositionSizer.

Covers R104–R110 (spec v1.2).
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from src.data.market_data_adapter import SymbolInfo
from src.strategy.market_clarity import ClarityResult, ClarityComponent
from src.strategy.structural_tp import StructuralTPResult, StructuralTarget
from src.execution.two_position_executor import TwoPositionPlanner, TwoPositionSizer


def _xauusd_info() -> SymbolInfo:
    return SymbolInfo(
        name="XAUUSD", digits=2, point=0.01,
        tick_size=0.01, tick_value=1.0, contract_size=100.0,
        volume_min=0.01, volume_max=500.0, volume_step=0.01,
        trade_stops_level=0, spread=20,
        currency_profit="USD", currency_margin="USD",
    )


def _clarity(score: int, grade: str, positions: int) -> ClarityResult:
    return ClarityResult(
        score=score, components=[], grade=grade,
        positions_permitted=positions, rejection_reason="" if grade != "REJECTED" else "low score",
        threshold_reject=60, threshold_one=60, threshold_two=75, threshold_high=85,
    )


def _tp_result(
    tp1_price: float | None, tp2_price: float | None,
    entry: float, sl: float,
) -> StructuralTPResult:
    sl_dist = abs(entry - sl)

    def _target(price: float, idx: int) -> StructuralTarget:
        rr = abs(price - entry) / sl_dist if sl_dist > 0 else 0.0
        return StructuralTarget(
            price=price, structure_type="swing_high",
            candle_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            rr_ratio=round(rr, 3), meets_minimum=rr >= 2.0,
        )

    t1 = _target(tp1_price, 0) if tp1_price else None
    t2 = _target(tp2_price, 1) if tp2_price else None
    return StructuralTPResult(
        tp1=t1, tp2=t2, all_barriers=[t for t in [t1, t2] if t],
        rejection_reason="" if t1 else "No valid TP1",
    )


def _planner(**kwargs) -> TwoPositionPlanner:
    defaults = dict(
        tp1_min_rr=2.0, tp2_min_rr=3.0,
        tp2_min_atr_distance=3.0,
        two_position_mode_enabled=True,
        partial_execution_policy="leave_a_open",
    )
    defaults.update(kwargs)
    return TwoPositionPlanner(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# R105/R106: Position A and B specification
# ─────────────────────────────────────────────────────────────────────────────

class TestPositionSpec:
    def test_two_positions_built_when_all_conditions_met(self) -> None:
        """R104: all conditions pass → 2 positions."""
        planner = _planner()
        plan = planner.build_plan(
            setup_id="abc123",
            symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0,
            equity=10_000.0,
            clarity=_clarity(score=80, grade="B", positions=2),
            tp_result=_tp_result(tp1_price=2040.0, tp2_price=2055.0, entry=2020.0, sl=2010.0),
            info=_xauusd_info(),
        )
        assert plan.approved
        assert plan.positions_count == 2
        assert plan.position_a is not None
        assert plan.position_b is not None

    def test_position_a_uses_tp1(self) -> None:
        planner = _planner()
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        assert plan.position_a.tp_price == pytest.approx(2040.0)

    def test_position_b_uses_tp2(self) -> None:
        planner = _planner()
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        assert plan.position_b.tp_price == pytest.approx(2055.0)

    def test_positions_share_setup_id(self) -> None:
        """R106: both positions share same setup_id."""
        planner = _planner()
        plan = planner.build_plan(
            setup_id="xyz999", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        assert plan.position_a.setup_id == "xyz999"
        assert plan.position_b.setup_id == "xyz999"

    def test_positions_have_different_client_order_ids(self) -> None:
        """IMPL4: each position has independent idempotent ID."""
        planner = _planner()
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        assert plan.position_a.client_order_id != plan.position_b.client_order_id


# ─────────────────────────────────────────────────────────────────────────────
# R107: Total risk budget
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskBudget:
    def test_total_risk_does_not_exceed_grade_budget(self) -> None:
        """R107: combined risk ≤ equity × grade_risk_pct."""
        planner = _planner()
        equity = 10_000.0
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=equity,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        # Grade B = 1.0% → max total = $100
        assert plan.total_risk_usd <= equity * 1.0 / 100 * 1.001  # 0.1% tolerance

    def test_grade_a_risk_higher_than_grade_b(self) -> None:
        planner = _planner()
        equity = 10_000.0
        plan_b = planner.build_plan(
            setup_id="b1", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=equity,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        plan_a = planner.build_plan(
            setup_id="a1", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=equity,
            clarity=_clarity(90, "A", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
            risk_pct_override=1.5,
        )
        assert plan_a.total_risk_usd >= plan_b.total_risk_usd


# ─────────────────────────────────────────────────────────────────────────────
# R104 fallback conditions
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackConditions:
    def test_falls_back_to_one_position_when_tp2_none(self) -> None:
        """R104: TP2 unavailable → one position."""
        planner = _planner()
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(tp1_price=2040.0, tp2_price=None, entry=2020.0, sl=2010.0),
            info=_xauusd_info(),
        )
        assert plan.positions_count == 1
        assert plan.position_b is None
        assert plan.position_a is not None

    def test_rejected_when_clarity_below_threshold(self) -> None:
        """R104: score < 60 → full rejection."""
        planner = _planner()
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(50, "REJECTED", 0),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        assert not plan.approved
        assert plan.rejection_reason != ""

    def test_two_position_mode_disabled_forces_one(self) -> None:
        """R104: two_position_mode_enabled=False → always one position."""
        planner = _planner(two_position_mode_enabled=False)
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(90, "A", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        assert plan.positions_count == 1
        assert plan.position_b is None

    def test_rejected_when_tp1_none(self) -> None:
        """R104: no valid TP1 → rejection."""
        planner = _planner()
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(80, "B", 2),
            tp_result=StructuralTPResult(None, None, [], "No valid TP1"),
            info=_xauusd_info(),
        )
        assert not plan.approved

    def test_min_volume_rejection(self) -> None:
        """R104: min broker volume exceeds risk budget → rejection."""
        # Very small equity → computed volume < volume_min
        planner = _planner()
        tiny_info = SymbolInfo(
            name="XAUUSD", digits=2, point=0.01,
            tick_size=0.01, tick_value=1.0, contract_size=100.0,
            volume_min=10.0,   # very high minimum
            volume_max=500.0, volume_step=0.01,
            trade_stops_level=0, spread=20,
            currency_profit="USD", currency_margin="USD",
        )
        plan = planner.build_plan(
            setup_id="abc123", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0,
            equity=100.0,   # tiny equity
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=tiny_info,
        )
        assert not plan.approved
        assert "minimum" in plan.rejection_reason.lower()


# ─────────────────────────────────────────────────────────────────────────────
# R110: daily counter
# ─────────────────────────────────────────────────────────────────────────────

class TestDailyCounter:
    def test_two_positions_count_as_one_setup(self) -> None:
        """R110: one setup = one daily entry, regardless of position count."""
        # This is tested at the engine level; here just confirm the plan
        # carries one setup_id
        planner = _planner()
        plan = planner.build_plan(
            setup_id="single_setup", symbol="XAUUSD", direction="BULLISH",
            entry_price=2020.0, sl_price=2010.0, equity=10_000.0,
            clarity=_clarity(80, "B", 2),
            tp_result=_tp_result(2040.0, 2055.0, 2020.0, 2010.0),
            info=_xauusd_info(),
        )
        if plan.position_b:
            assert plan.position_a.setup_id == plan.position_b.setup_id
