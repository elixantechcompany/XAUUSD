"""
Unit tests for MT5Executor.
Tests Exness symbol resolution, SL/TP enforcement, pre-flight checks, and emergency close.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

from src.execution.mt5_executor import MT5Executor, MT5Position
from src.utils.credentials import BrokerCredentials


@pytest.fixture
def dummy_creds() -> BrokerCredentials:
    return BrokerCredentials(
        account_id=12345678,
        password="TestPassword!",
        server="Exness-MT5Trial12",
        path=None,
    )


class TestMT5Executor:
    def test_live_mode_blocked_without_arm_switch(self, dummy_creds):
        with pytest.raises(PermissionError, match="LIVE execution mode blocked"):
            MT5Executor(credentials=dummy_creds, mode="LIVE", live_armed=False)

    def test_live_mode_allowed_with_arm_switch(self, dummy_creds):
        executor = MT5Executor(credentials=dummy_creds, mode="LIVE", live_armed=True)
        assert executor.mode == "LIVE"

    def test_symbol_resolution_exness_standard_suffix(self, dummy_creds):
        executor = MT5Executor(credentials=dummy_creds, mode="DEMO")

        mock_symbols = [
            SimpleNamespace(name="EURUSD"),
            SimpleNamespace(name="XAUUSDm"),   # Exness Standard symbol
            SimpleNamespace(name="BTCUSDm"),
        ]

        with patch("MetaTrader5.symbols_get", return_value=mock_symbols), \
             patch("MetaTrader5.symbol_select", return_value=True):

            resolved_gold = executor.resolve_symbol("XAUUSD")
            assert resolved_gold == "XAUUSDm"

            resolved_btc = executor.resolve_symbol("BTCUSD")
            assert resolved_btc == "BTCUSDm"

    def test_submit_order_attaches_sl_and_tp(self, dummy_creds):
        executor = MT5Executor(credentials=dummy_creds, mode="DEMO")
        executor._connected = True

        mock_check = SimpleNamespace(retcode=0, comment="Done")
        mock_send_res = SimpleNamespace(
            retcode=10009,  # TRADE_RETCODE_DONE
            order=99887766,
            price=2028.00,
            volume=0.05,
            comment="Done",
        )
        mock_position = SimpleNamespace(
            ticket=99887766,
            symbol="XAUUSDm",
            type=0,  # POSITION_TYPE_BUY
            volume=0.05,
            price_open=2028.00,
            price_current=2028.10,
            sl=2015.00,
            tp=2054.00,
            profit=5.00,
            swap=0.0,
            magic=101001,
            comment="AGY_12345678",
            time=int(datetime.now(tz=timezone.utc).timestamp()),
        )
        mock_symbol_info = SimpleNamespace(name="XAUUSDm", filling_mode=2)
        mock_terminal = SimpleNamespace(connected=True, trade_allowed=True)

        with patch("MetaTrader5.terminal_info", return_value=mock_terminal), \
             patch("MetaTrader5.symbols_get", return_value=[SimpleNamespace(name="XAUUSDm")]), \
             patch("MetaTrader5.symbol_select", return_value=True), \
             patch("MetaTrader5.symbol_info", return_value=mock_symbol_info), \
             patch("MetaTrader5.order_check", return_value=mock_check), \
             patch("MetaTrader5.order_send", return_value=mock_send_res), \
             patch("MetaTrader5.positions_get", return_value=[mock_position]):

            ok, msg, pos = executor.submit_order(
                setup_id="test_setup_1",
                symbol="XAUUSD",
                direction="BULLISH",
                volume=0.05,
                entry_price=2028.00,
                sl=2015.00,
                tp=2054.00,
                current_ask=2028.00,
                current_bid=2027.80,
            )

            assert ok is True
            assert pos is not None
            assert pos.ticket == 99887766
            assert pos.sl == 2015.00
            assert pos.tp == 2054.00
            assert pos.entry_price == 2028.00

    def test_preflight_order_check_rejection(self, dummy_creds):
        executor = MT5Executor(credentials=dummy_creds, mode="DEMO")
        executor._connected = True

        mock_check = SimpleNamespace(retcode=10019, comment="No money")  # Margin check failed
        mock_symbol_info = SimpleNamespace(name="XAUUSDm", filling_mode=2)
        mock_terminal = SimpleNamespace(connected=True, trade_allowed=True)

        with patch("MetaTrader5.terminal_info", return_value=mock_terminal), \
             patch("MetaTrader5.symbols_get", return_value=[SimpleNamespace(name="XAUUSDm")]), \
             patch("MetaTrader5.symbol_select", return_value=True), \
             patch("MetaTrader5.symbol_info", return_value=mock_symbol_info), \
             patch("MetaTrader5.order_check", return_value=mock_check):

            ok, msg, pos = executor.submit_order(
                setup_id="test_setup_2",
                symbol="XAUUSD",
                direction="BULLISH",
                volume=50.0,  # Excessive volume
                entry_price=2028.00,
                sl=2015.00,
                tp=2054.00,
                current_ask=2028.00,
                current_bid=2027.80,
            )

            assert ok is False
            assert "No money" in msg
            assert pos is None

    def test_close_all_positions_emergency_liquidation(self, dummy_creds):
        executor = MT5Executor(credentials=dummy_creds, mode="DEMO")
        executor._connected = True

        mock_pos1 = SimpleNamespace(
            ticket=101, symbol="XAUUSDm", type=0, volume=0.05,
            price_open=2000.0, price_current=2010.0, sl=1990.0, tp=2030.0,
            profit=50.0, swap=0.0, magic=101001, comment="", time=1700000000,
        )
        mock_pos2 = SimpleNamespace(
            ticket=102, symbol="BTCUSDm", type=1, volume=0.01,
            price_open=60000.0, price_current=59000.0, sl=61000.0, tp=58000.0,
            profit=10.0, swap=0.0, magic=101002, comment="", time=1700000000,
        )
        mock_terminal = SimpleNamespace(connected=True, trade_allowed=True)

        with patch("MetaTrader5.terminal_info", return_value=mock_terminal), \
             patch("MetaTrader5.positions_get", side_effect=[[mock_pos1, mock_pos2], [mock_pos1], [mock_pos2]]), \
             patch("MetaTrader5.symbol_info_tick", return_value=SimpleNamespace(bid=2010.0, ask=2010.2)), \
             patch("MetaTrader5.symbol_info", return_value=SimpleNamespace(filling_mode=2)), \
             patch("MetaTrader5.order_send", return_value=SimpleNamespace(retcode=10009)):

            closed_count = executor.close_all_positions()
            assert closed_count == 2
