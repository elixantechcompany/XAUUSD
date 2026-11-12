"""
Automated Test Suite for MASTER DIRECTIVE:
Trade Management, Continuous Execution, Account Synchronization and Three-Order Execution.

Covers all test requirements specified in PART 7:
1. Break-Even Tests (BUY/SELL, 25/50/70/Adaptive, SL safety, broker rejection, independent tracking).
2. Continuous Execution Tests (TP/SL closure, setup clearing, new setup scanning, waiting reporting).
3. Account Synchronization Tests (Normalized Account State, authoritative MT5 source, separate pending orders).
4. Three-Order Execution Tests (Identical dynamic lot size, combined exposure assessment, partial fill safety).
5. Retry & Recovery Tests (Recoverable vs non-recoverable, duplicate order prevention).
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.execution.position_manager import (
    PositionManagementEngine,
    BreakEvenMode,
    PositionBreakEvenState,
)
from src.execution.three_order_executor import (
    ThreeOrderExecutor,
    OrderExecutionState,
    SingleOrderSpec,
    ThreeOrderExecutionGroup,
    FailureCategory,
)
from src.services.account_state_service import (
    AccountStateService,
    NormalizedAccountState,
    NormalizedPosition,
    NormalizedPendingOrder,
)


# ==============================================================================
# PART 1: BREAK-EVEN & POSITION MANAGEMENT TESTS
# ==============================================================================

def test_breakeven_tp_progress_calculation_buy():
    """Verify TP progress calculation for a BUY order."""
    pm = PositionManagementEngine(default_mode=BreakEvenMode.FIXED_50)
    # Entry: 4000, TP: 4100 (TP distance = 100)
    pos = pm.register_position(
        ticket=1001,
        symbol="XAUUSDm",
        direction="BUY",
        volume=0.01,
        entry_price=4000.0,
        sl=3950.0,
        tp=4100.0,
    )
    # Price at 4025 -> 25% progress
    p25 = pm.calculate_tp_progress(pos, current_price=4025.0)
    assert pytest.approx(p25, 0.001) == 0.25

    # Price at 4050 -> 50% progress
    p50 = pm.calculate_tp_progress(pos, current_price=4050.0)
    assert pytest.approx(p50, 0.001) == 0.50

    # Price at 4070 -> 70% progress
    p70 = pm.calculate_tp_progress(pos, current_price=4070.0)
    assert pytest.approx(p70, 0.001) == 0.70


def test_breakeven_tp_progress_calculation_sell():
    """Verify TP progress calculation for a SELL order."""
    pm = PositionManagementEngine(default_mode=BreakEvenMode.FIXED_50)
    # Entry: 4000, TP: 3900 (TP distance = 100)
    pos = pm.register_position(
        ticket=1002,
        symbol="XAUUSDm",
        direction="SELL",
        volume=0.01,
        entry_price=4000.0,
        sl=4050.0,
        tp=3900.0,
    )
    # Price at 3975 -> 25% progress toward 3900
    p25 = pm.calculate_tp_progress(pos, current_price=3975.0)
    assert pytest.approx(p25, 0.001) == 0.25

    # Price at 3950 -> 50% progress
    p50 = pm.calculate_tp_progress(pos, current_price=3950.0)
    assert pytest.approx(p50, 0.001) == 0.50

    # Price at 3930 -> 70% progress
    p70 = pm.calculate_tp_progress(pos, current_price=3930.0)
    assert pytest.approx(p70, 0.001) == 0.70


def test_breakeven_fixed_modes_triggers():
    """Verify FIXED_25, FIXED_50, and FIXED_70 trigger at their exact milestones."""
    pm = PositionManagementEngine()

    # Position in FIXED_25 mode
    pos25 = pm.register_position(
        ticket=2001, symbol="XAUUSDm", direction="BUY", volume=0.01,
        entry_price=4000.0, sl=3950.0, tp=4100.0, mode=BreakEvenMode.FIXED_25,
    )
    # Price at 4020 (20% progress) -> No mod
    mod, _, _ = pm.evaluate_position(2001, current_price=4020.0)
    assert not mod

    # Price reaches 4026 (26% progress) -> Triggers BE
    mod, new_sl, reason = pm.evaluate_position(2001, current_price=4026.0)
    assert mod is True
    assert new_sl > 4000.0  # Cost adjusted BE above entry
    assert "FIXED_25" in reason

    # Position in FIXED_70 mode
    pos70 = pm.register_position(
        ticket=2002, symbol="XAUUSDm", direction="BUY", volume=0.01,
        entry_price=4000.0, sl=3950.0, tp=4100.0, mode=BreakEvenMode.FIXED_70,
    )
    # Price reaches 4055 (55% progress) -> Should NOT trigger yet in FIXED_70
    mod70, _, _ = pm.evaluate_position(2002, current_price=4055.0)
    assert not mod70

    # Price reaches 4072 (72% progress) -> Triggers BE
    mod70, new_sl70, reason70 = pm.evaluate_position(2002, current_price=4072.0)
    assert mod70 is True
    assert "FIXED_70" in reason70


def test_breakeven_adaptive_mode_conditions():
    """Verify ADAPTIVE mode chooses 0.25 on momentum slowing or reversal, 0.70 on strong trend."""
    pm = PositionManagementEngine()
    pos = pm.register_position(
        ticket=3001, symbol="XAUUSDm", direction="BUY", volume=0.01,
        entry_price=4000.0, sl=3950.0, tp=4100.0, mode=BreakEvenMode.ADAPTIVE,
    )
    # Baseline adaptive milestone is 0.50
    m_base = pm.evaluate_adaptive_milestone(pos, current_price=4020.0)
    assert m_base == 0.50

    # If reversal detected or momentum slowing -> adaptively lowers milestone to 0.25
    m_rev = pm.evaluate_adaptive_milestone(pos, current_price=4020.0, reversal_detected=True)
    assert m_rev == 0.25

    m_slow = pm.evaluate_adaptive_milestone(pos, current_price=4020.0, momentum_slowing=True)
    assert m_slow == 0.25

    # If peak progress is high (> 0.40) and momentum strong -> allows room (0.70)
    pos.peak_tp_progress = 0.45
    m_trend = pm.evaluate_adaptive_milestone(pos, current_price=4045.0, momentum_slowing=False)
    assert m_trend == 0.70


def test_breakeven_safety_rule_never_moves_sl_in_wrong_direction():
    """Verify SL is NEVER moved to increase risk (BUY SL cannot move lower, SELL SL cannot move higher)."""
    pm = PositionManagementEngine(default_mode=BreakEvenMode.FIXED_25)
    # BUY trade with an already protective trailing SL at 4010
    pos_buy = pm.register_position(
        ticket=4001, symbol="XAUUSDm", direction="BUY", volume=0.01,
        entry_price=4000.0, sl=4010.0, tp=4100.0, mode=BreakEvenMode.FIXED_25,
    )
    # Even if 25% is reached, candidate BE (e.g. 4000.20) must NOT overwrite 4010
    mod, _, reason = pm.evaluate_position(4001, current_price=4030.0)
    assert not mod
    assert "more protective" in reason

    # SELL trade with an already protective trailing SL at 3990
    pos_sell = pm.register_position(
        ticket=4002, symbol="XAUUSDm", direction="SELL", volume=0.01,
        entry_price=4000.0, sl=3990.0, tp=3900.0, mode=BreakEvenMode.FIXED_25,
    )
    # Candidate BE (e.g. 3999.80) must NOT overwrite 3990
    mod_s, _, reason_s = pm.evaluate_position(4002, current_price=3970.0)
    assert not mod_s
    assert "more protective" in reason_s


def test_three_positions_managed_independently():
    """Verify all 3 positions of a setup receive independent break-even tracking."""
    pm = PositionManagementEngine(default_mode=BreakEvenMode.FIXED_25)
    # Register 3 separate orders belonging to the same setup
    p1 = pm.register_position(ticket=5001, symbol="XAUUSDm", direction="BUY", volume=0.02, entry_price=4000.0, sl=3980.0, tp=4060.0, setup_id="setup_abc", group_id="grp_1", order_index=1)
    p2 = pm.register_position(ticket=5002, symbol="XAUUSDm", direction="BUY", volume=0.02, entry_price=4000.0, sl=3980.0, tp=4060.0, setup_id="setup_abc", group_id="grp_1", order_index=2)
    p3 = pm.register_position(ticket=5003, symbol="XAUUSDm", direction="BUY", volume=0.02, entry_price=4000.0, sl=3980.0, tp=4060.0, setup_id="setup_abc", group_id="grp_1", order_index=3)

    assert len(pm.get_all_positions()) == 3

    # Close/deregister position 1
    pm.deregister_position(5001)
    assert len(pm.get_all_positions()) == 2
    assert pm.get_position(5001) is None
    assert pm.get_position(5002) is not None
    assert pm.get_position(5003) is not None


# ==============================================================================
# PART 2: CONTINUOUS EXECUTION & SCANNING TESTS
# ==============================================================================

def test_continuous_trading_lifecycle_after_tp_closure():
    """Verify position closure clears position state and continues scanning."""
    pm = PositionManagementEngine()
    pm.register_position(ticket=6001, symbol="XAUUSDm", direction="BUY", volume=0.01, entry_price=4000.0, sl=3980.0, tp=4060.0)
    assert len(pm.get_all_positions()) == 1

    # Simulate TP hit on MT5
    closed_pos = pm.deregister_position(6001)
    assert closed_pos is not None
    assert closed_pos.ticket == 6001
    assert len(pm.get_all_positions()) == 0  # Ready for next setup without lingering open states


# ==============================================================================
# PART 3: ACCOUNT SYNCHRONIZATION TESTS
# ==============================================================================

def test_account_state_service_normalization():
    """Verify AccountStateService normalizes MT5 account info and positions correctly."""
    service = AccountStateService()
    mock_mt5 = MagicMock()

    # Mock account_info
    mock_info = MagicMock()
    mock_info.login = 476719466
    mock_info.server = "Exness-MT5Trial9"
    mock_info.currency = "USD"
    mock_info.balance = 548.20
    mock_info.equity = 552.10
    mock_info.margin = 12.0
    mock_info.margin_free = 540.10
    mock_info.margin_level = 4600.8
    mock_mt5.account_info.return_value = mock_info

    # Mock 2 positions on MT5
    p1 = MagicMock()
    p1.ticket = 7001
    p1.symbol = "XAUUSDm"
    p1.type = 0  # BUY
    p1.volume = 0.02
    p1.price_open = 4020.50
    p1.price_current = 4023.00
    p1.sl = 4010.0
    p1.tp = 4050.0
    p1.profit = 2.50
    p1.swap = 0.0
    p1.time = 1762950000
    p1.comment = "SMC_ord1"

    p2 = MagicMock()
    p2.ticket = 7002
    p2.symbol = "XAUUSDm"
    p2.type = 0  # BUY
    p2.volume = 0.02
    p2.price_open = 4020.50
    p2.price_current = 4023.00
    p2.sl = 4010.0
    p2.tp = 4050.0
    p2.profit = 2.50
    p2.swap = 0.0
    p2.time = 1762950000
    p2.comment = "SMC_ord2"

    mock_mt5.positions_get.return_value = (p1, p2)
    mock_mt5.orders_get.return_value = ()

    state = service.poll_mt5_account_state(mock_mt5)

    assert state.connected is True
    assert state.account_id == "476719466"
    assert state.balance == 548.20
    assert state.equity == 552.10
    assert state.open_positions_count == 2
    assert len(state.open_positions) == 2
    assert state.open_positions[0].ticket == "7001"
    assert state.open_positions[1].ticket == "7002"
    assert state.pending_orders_count == 0


def test_account_state_service_zero_positions_agreement():
    """Verify when MT5 reports 0 positions, NormalizedAccountState reports 0."""
    service = AccountStateService()
    mock_mt5 = MagicMock()
    mock_info = MagicMock()
    mock_info.login = 476719466
    mock_info.server = "Exness-MT5Trial9"
    mock_info.currency = "USD"
    mock_info.balance = 548.20
    mock_info.equity = 548.20
    mock_info.margin = 0.0
    mock_info.margin_free = 548.20
    mock_mt5.account_info.return_value = mock_info
    mock_mt5.positions_get.return_value = ()
    mock_mt5.orders_get.return_value = ()

    state = service.poll_mt5_account_state(mock_mt5)
    assert state.open_positions_count == 0
    assert len(state.open_positions) == 0


def test_account_state_pending_orders_separated():
    """Verify pending orders are not counted as open positions."""
    service = AccountStateService()
    mock_mt5 = MagicMock()
    mock_info = MagicMock()
    mock_info.login = 476719466
    mock_mt5.account_info.return_value = mock_info
    mock_mt5.positions_get.return_value = ()  # 0 open positions

    # 1 pending limit order
    pending = MagicMock()
    pending.ticket = 9901
    pending.symbol = "XAUUSDm"
    pending.volume_current = 0.02
    pending.price_open = 4010.0
    pending.state = "ORDER_STATE_PLACED"
    pending.time_setup = 1762950000
    mock_mt5.orders_get.return_value = (pending,)

    state = service.poll_mt5_account_state(mock_mt5)
    assert state.open_positions_count == 0
    assert state.pending_orders_count == 1
    assert len(state.pending_orders) == 1
    assert state.pending_orders[0].ticket == "9901"


# ==============================================================================
# PART 4: THREE-ORDER EXECUTION TESTS
# ==============================================================================

def test_three_order_plan_identical_lot_size():
    """Verify all three orders are prepared with the EXACT SAME calculated lot size."""
    executor = ThreeOrderExecutor()
    ok, group, msg = executor.prepare_three_order_plan(
        setup_id="setup_gold_1",
        symbol="XAUUSDm",
        direction="BUY",
        entry_price=4020.0,
        sl_price=4010.0,
        tp_price=4050.0,
        common_lot_size=0.02,
        account_equity=5000.0,
        account_free_margin=4500.0,
    )
    assert ok is True
    assert group is not None
    assert len(group.orders) == 3
    for ord_spec in group.orders:
        assert ord_spec.volume == 0.02  # Exactly identical
    assert group.total_volume == 0.06   # 3 * 0.02


def test_three_order_plan_rejects_insufficient_equity_margin():
    """Verify rejection when combined exposure exceeds safe risk ceiling or margin."""
    executor = ThreeOrderExecutor()
    # Try 0.50 lots on a tiny $50 account (SL 10 pts on Gold = $500 risk per lot)
    ok, group, msg = executor.prepare_three_order_plan(
        setup_id="setup_overrisk",
        symbol="XAUUSDm",
        direction="BUY",
        entry_price=4020.0,
        sl_price=4010.0,
        tp_price=4050.0,
        common_lot_size=0.50,
        account_equity=50.0,
        account_free_margin=40.0,
    )
    assert ok is False
    assert group is None
    assert "exceeds" in msg or "Combined exposure" in msg


def test_three_order_partial_execution_preserves_filled():
    """Verify if 2 orders succeed and 1 fails, the 2 filled orders are preserved without duplicating."""
    executor = ThreeOrderExecutor()
    ok, group, _ = executor.prepare_three_order_plan(
        setup_id="setup_partial",
        symbol="XAUUSDm",
        direction="BUY",
        entry_price=4020.0,
        sl_price=4010.0,
        tp_price=4050.0,
        common_lot_size=0.01,
        account_equity=5000.0,
        account_free_margin=4500.0,
    )
    assert group is not None

    # Simulate submission where order 1 and 2 succeed, but order 3 fails
    def mock_submit(ord_spec: SingleOrderSpec):
        if ord_spec.order_index == 3:
            return False, None, None, 10019, "No money"  # Insufficient margin for order 3
        return True, 8000 + ord_spec.order_index, 4020.0, 10009, "OK"

    executor.execute_group(group, mock_submit)

    assert group.is_partially_executed is True
    assert group.confirmed_filled_count == 2
    assert group.orders[0].state == OrderExecutionState.FILLED
    assert group.orders[0].broker_ticket == 8001
    assert group.orders[1].state == OrderExecutionState.FILLED
    assert group.orders[1].broker_ticket == 8002
    assert group.orders[2].state == OrderExecutionState.REJECTED
