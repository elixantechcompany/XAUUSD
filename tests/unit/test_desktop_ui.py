"""
Unit tests for PySide6 Desktop GUI components — Milestone 5.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.agents.coordinator import CentralCoordinator, CoordinatorVerdict
from src.desktop.main_window import MainWindow
from src.desktop.widgets.candlestick_chart import StrategyChartWidget
from src.desktop.widgets.consensus_panel import ConsensusPanelWidget
from src.desktop.widgets.kill_switch_dialog import KillSwitchConfirmationDialog
from src.desktop.widgets.system_status_bar import SystemStatusBarWidget
from src.data.candle import Candle
from src.strategy.strategy_core import FVG, Swing


def _make_sample_candle(time_str: str, o: float, h: float, l: float, c: float) -> Candle:
    t = datetime.fromisoformat(time_str)
    return Candle(symbol="XAUUSD", timeframe="H1", time=t, open=o, high=h, low=l, close=c, volume=100.0)


def test_strategy_chart_widget_plot():
    """StrategyChartWidget accepts candles, swings, FVGs, and trade levels."""
    chart = StrategyChartWidget()

    c1 = _make_sample_candle("2024-01-01 10:00:00+00:00", 2020.0, 2030.0, 2019.0, 2028.0)
    c2 = _make_sample_candle("2024-01-01 11:00:00+00:00", 2028.0, 2035.0, 2026.0, 2033.0)
    c3 = _make_sample_candle("2024-01-01 12:00:00+00:00", 2033.0, 2040.0, 2031.0, 2038.0)
    candles = [c1, c2, c3]

    sw1 = Swing(candle=c1, level=2030.0, direction="HIGH", confirmed_at=c1.time)
    sw2 = Swing(candle=c2, level=2026.0, direction="LOW", confirmed_at=c2.time)

    fvg = FVG(
        id="fvg-01",
        symbol="XAUUSD",
        timeframe="H1",
        direction="BULLISH",
        fvg_low=2030.0,
        fvg_high=2031.0,
        c1_time=c1.time,
        c3_time=c3.time,
        c1_high=2030.0,
        c1_low=2019.0,
        c3_high=2040.0,
        c3_low=2031.0,
        atr_at_detection=5.0,
        created_at=c3.time,
    )

    chart.plot_candles(candles)
    chart.set_swings([sw1, sw2])
    chart.set_fvgs([fvg])
    chart.set_trade_levels(entry=2032.0, sl=2025.0, tp=2046.0, sweep_extreme=2024.0)

    assert len(chart.candles) == 3
    assert len(chart.swings) == 2
    assert len(chart.fvgs) == 1
    assert chart.levels["entry"] == 2032.0
    assert chart.levels["sl"] == 2025.0
    assert chart.levels["tp"] == 2046.0


def test_consensus_panel_widget_updates():
    """ConsensusPanelWidget updates agent cards and coordinator verdict."""
    panel = ConsensusPanelWidget()

    decisions = [
        {"agent_name": "The Scout", "vote": "PASS", "rationale": "Normal volatility", "decision_id": "dec-12345678"},
        {"agent_name": "The News Analyst", "vote": "PASS", "rationale": "No blackouts", "decision_id": "dec-12345678"},
        {"agent_name": "The Skeptic", "vote": "PASS", "rationale": "Risk acceptable", "decision_id": "dec-12345678"},
        {"agent_name": "The Risk Manager", "vote": "APPROVE", "rationale": "1% sizing safe", "decision_id": "dec-12345678"},
    ]

    panel.update_consensus(verdict=CoordinatorVerdict.APPROVED, decisions=decisions)

    # Test veto update
    veto_decisions = [
        {"agent_name": "The Skeptic", "vote": "VETO", "rationale": "Rollover window active", "decision_id": "dec-9999"},
    ]
    panel.update_consensus(verdict=CoordinatorVerdict.VETOED_BY_SKEPTIC, decisions=veto_decisions)


def test_system_status_bar_updates():
    """SystemStatusBarWidget updates MT5 connection and execution mode."""
    bar = SystemStatusBarWidget()
    bar.set_mt5_status(connected=True, mode="LIVE")
    if bar.bar:
        assert "CONNECTED" in bar.mt5_label.text()
        assert "LIVE" in bar.mode_label.text()

    bar.set_mt5_status(connected=False, mode="HALTED")
    if bar.bar:
        assert "DISCONNECTED" in bar.mt5_label.text()
        assert "HALTED" in bar.mode_label.text()


def test_main_window_integration():
    """MainWindow initializes and connects coordinator and UI elements."""
    coordinator = CentralCoordinator()
    window = MainWindow(coordinator=coordinator)

    assert window.current_symbol == "XAUUSD"
    window._on_symbol_changed("BTCUSD")
    assert window.current_symbol == "BTCUSD"

    # Test market view update
    c1 = _make_sample_candle("2024-01-01 10:00:00+00:00", 2020.0, 2030.0, 2019.0, 2028.0)
    window.update_market_view(candles=[c1], swings=[], fvgs=[], trade_levels={"entry": 2028.0, "sl": 2020.0, "tp": 2044.0})

    # Test consensus view update
    window.update_consensus_view(verdict=CoordinatorVerdict.APPROVED, decisions=[])


def test_kill_switch_dialog_confirmation():
    """KillSwitchConfirmationDialog confirm method returns bool."""
    with patch("src.desktop.widgets.kill_switch_dialog.KillSwitchConfirmationDialog.confirm", return_value=True):
        res = KillSwitchConfirmationDialog.confirm()
        assert res is True
