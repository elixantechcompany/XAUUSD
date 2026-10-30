"""
Unit tests for Profit Guardian — dynamic trailing stops & aggressive retracement protection.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.execution.profit_guardian import ProfitGuardian


def test_profit_guardian_bullish_breakeven():
    """At 1.0R, SL moves to entry + buffer (breakeven)."""
    mock_executor = MagicMock()
    guardian = ProfitGuardian(master_executor=mock_executor, breakeven_r=1.0)

    # Long trade: entry 2650.00, SL 2640.00 (Risk = 10.00 USD), TP 2670.00 (2.0R)
    guardian.register_position(
        ticket=1001,
        symbol="XAUUSD",
        direction="BULLISH",
        entry_price=2650.00,
        sl=2640.00,
        tp=2670.00,
    )

    # Price moves to 2655 (0.5R) -> No change
    mod, new_sl, reason = guardian.update_price(1001, 2655.00)
    assert not mod

    # Price hits 2660.00 (1.0R) -> Breakeven triggered
    mod, new_sl, reason = guardian.update_price(1001, 2660.00)
    assert mod is True
    assert new_sl > 2650.00
    assert "BREAKEVEN" in reason


def test_profit_guardian_bullish_profit_lock():
    """At 1.5R, SL locks at +0.5R profit; at 2.0R locks at +1.0R."""
    mock_executor = MagicMock()
    guardian = ProfitGuardian(master_executor=mock_executor)

    guardian.register_position(
        ticket=1002,
        symbol="XAUUSD",
        direction="BULLISH",
        entry_price=2650.00,
        sl=2640.00,
        tp=2675.00,
    )

    # Price hits 2665.00 (1.5R) -> SL locks at entry + 0.5R (2655.00)
    mod, new_sl, reason = guardian.update_price(1002, 2665.00)
    assert mod is True
    assert new_sl == pytest.approx(2655.00, 0.01)
    assert "PROFIT_LOCK_1.5R" in reason

    # Price hits 2670.00 (2.0R) -> SL locks at entry + 1.0R (2660.00)
    mod, new_sl, reason = guardian.update_price(1002, 2670.00)
    assert mod is True
    assert new_sl == pytest.approx(2660.00, 0.01)
    assert "PROFIT_LOCK_2R" in reason


def test_profit_guardian_aggressive_retracement_lock():
    """If market spikes to 1.8R profit and then sharply retraces >40%, SL shifts tightly to protect banked gains."""
    mock_executor = MagicMock()
    guardian = ProfitGuardian(master_executor=mock_executor, retrace_lock_pct=0.40)

    guardian.register_position(
        ticket=1003,
        symbol="XAUUSD",
        direction="BULLISH",
        entry_price=2650.00,
        sl=2640.00,
        tp=2680.00,
    )

    # 1. Price runs up to 2668.00 (Peak = +18.00 USD, 1.8R)
    guardian.update_price(1003, 2668.00)

    # 2. Market suddenly experiences an aggressive pullback: drops from 2668 to 2658 (drops 10 USD out of 18 USD = 55% retrace)
    mod, new_sl, reason = guardian.update_price(1003, 2658.00)
    assert mod is True
    assert "AGGRESSIVE_RETRACE_GUARDIAN" in reason
    # SL is shifted to protect at least 60% of peak gain (2650 + 18 * 0.60 = 2660.80)
    assert new_sl > 2655.00


def test_profit_guardian_bearish_positions():
    """Bearish short trade breakeven and retracement protection."""
    mock_executor = MagicMock()
    guardian = ProfitGuardian(master_executor=mock_executor)

    # Short trade: Entry 2650.00, SL 2660.00 (Risk = 10 USD), TP 2630.00
    guardian.register_position(
        ticket=2001,
        symbol="XAUUSD",
        direction="BEARISH",
        entry_price=2650.00,
        sl=2660.00,
        tp=2630.00,
    )

    # Price drops to 2640.00 (1.0R gain for short) -> Breakeven moves SL below 2650
    mod, new_sl, reason = guardian.update_price(2001, 2640.00)
    assert mod is True
    assert new_sl < 2650.00
    assert "BREAKEVEN" in reason
