"""
Unit tests for Exness Demo Forward Verifier (Milestone 6):
- MT5 IPC connectivity check
- Exness symbol resolution (XAUUSD -> XAUUSDm, BTCUSD -> BTCUSDm)
- Live quote streaming & latency calculation
- Pre-flight order_check validation
- Demo order dispatch with mandatory attached SL/TP
- Emergency liquidation
- Graceful offline / terminal disconnected handling
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.execution.demo_verifier import DemoVerifier, DemoVerificationReport
from src.execution.mt5_executor import MT5Executor, MT5Position
from src.data.candle import Candle


class TestDemoVerifier:
    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        ex = MagicMock(spec=MT5Executor)
        ex.connect.return_value = True
        ex.is_connected.return_value = True
        ex.get_account_info.return_value = {
            "login": 12345678,
            "server": "Exness-MT5Trial12",
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "margin_free": 10000.0,
            "leverage": 200,
            "currency": "USD",
            "trade_mode": 0,
        }
        ex.resolve_symbol.side_effect = lambda s: f"{s}m"
        ex.get_symbol_tick.side_effect = lambda s: {
            "symbol": s,
            "bid": 2650.10 if "XAU" in s else 96100.0,
            "ask": 2650.35 if "XAU" in s else 96150.0,
            "last": 2650.20 if "XAU" in s else 96120.0,
            "volume": 10.0,
            "time": datetime.now(timezone.utc),
        }
        ex._determine_filling_type.return_value = 2  # IOC
        return ex

    @pytest.fixture
    def mock_data_adapter(self) -> MagicMock:
        da = MagicMock()
        da.get_candles.return_value = [
            Candle(
                time=datetime(2025, 1, 1, h, tzinfo=timezone.utc),
                open=2650.0, high=2655.0, low=2645.0, close=2652.0,
                volume=100.0, symbol="XAUUSDm", timeframe="H1"
            )
            for h in range(20)
        ]
        return da

    def test_verify_connectivity_success(self, mock_executor, mock_data_adapter):
        verifier = DemoVerifier(executor=mock_executor, data_adapter=mock_data_adapter)
        ok, info = verifier.verify_connectivity()
        assert ok is True
        assert info["login"] == 12345678
        assert "Exness" in info["server"]
        assert info["balance"] == 10000.0

    def test_verify_symbol_resolution(self, mock_executor, mock_data_adapter):
        verifier = DemoVerifier(executor=mock_executor, data_adapter=mock_data_adapter, symbols=["XAUUSD", "BTCUSD"])
        sym_map = verifier.verify_symbol_resolution()
        assert sym_map["XAUUSD"] == "XAUUSDm"
        assert sym_map["BTCUSD"] == "BTCUSDm"

    def test_verify_quote_streaming(self, mock_executor, mock_data_adapter):
        verifier = DemoVerifier(executor=mock_executor, data_adapter=mock_data_adapter, symbols=["XAUUSD", "BTCUSD"])
        sym_map = {"XAUUSD": "XAUUSDm", "BTCUSD": "BTCUSDm"}
        quotes = verifier.verify_quote_streaming(sym_map)

        assert "XAUUSD" in quotes
        assert "BTCUSD" in quotes
        assert quotes["XAUUSD"]["bid"] == 2650.10
        assert quotes["XAUUSD"]["ask"] == 2650.35
        assert quotes["XAUUSD"]["spread"] == 0.25
        assert quotes["XAUUSD"]["h1_candles_count"] == 20
        assert quotes["XAUUSD"]["latency_ms"] >= 0.0

    @patch("MetaTrader5.order_check")
    def test_verify_preflight_order_check(self, mock_mt5_check, mock_executor, mock_data_adapter):
        mock_res = MagicMock()
        mock_res.retcode = 0
        mock_res.comment = "Done"
        mock_res.margin = 50.0
        mock_res.margin_free = 9950.0
        mock_mt5_check.return_value = mock_res

        verifier = DemoVerifier(executor=mock_executor, data_adapter=mock_data_adapter)
        res = verifier.verify_preflight_order_check(symbol="XAUUSD", volume=0.01)

        assert res["retcode"] == 0
        assert res["margin_required"] == 50.0
        assert res["symbol"] == "XAUUSDm"

    def test_verify_demo_order_dispatch_and_liquidation(self, mock_executor, mock_data_adapter):
        mock_pos = MT5Position(
            ticket=987654,
            symbol="XAUUSDm",
            direction="BULLISH",
            volume=0.01,
            entry_price=2650.35,
            current_price=2650.35,
            sl=2645.35,
            tp=2660.35,
            pnl=0.0,
            swap=0.0,
            magic=101001,
            comment="AGY_VERIFY",
            opened_at=datetime.now(timezone.utc),
        )
        mock_executor.submit_order.return_value = (True, "Filled", mock_pos)
        mock_executor.close_position.return_value = (True, "Closed @ 2650.35")
        mock_executor.get_positions.return_value = []

        verifier = DemoVerifier(executor=mock_executor, data_adapter=mock_data_adapter)
        trade_res, liq_res = verifier.verify_demo_order_dispatch(symbol="XAUUSD", volume=0.01)

        assert trade_res["filled"] is True
        assert trade_res["ticket"] == 987654
        assert trade_res["sl_verified"] is True
        assert trade_res["sl"] == 2645.35

        assert liq_res["closed"] is True
        assert liq_res["remaining_positions"] == 0

    def test_run_full_verification_when_connected(self, mock_executor, mock_data_adapter):
        with patch("MetaTrader5.order_check") as mock_check:
            mock_res = MagicMock()
            mock_res.retcode = 0
            mock_res.comment = "Done"
            mock_res.margin = 50.0
            mock_res.margin_free = 9950.0
            mock_check.return_value = mock_res

            verifier = DemoVerifier(executor=mock_executor, data_adapter=mock_data_adapter)
            report = verifier.run_full_verification(execute_live_demo_trade=False)

            assert report.terminal_connected is True
            assert report.passed is True
            assert "XAUUSD" in report.symbol_resolution
            assert "BTCUSD" in report.symbol_resolution
            assert "ALL CHECKS PASSED" in report.summary()

    def test_run_full_verification_when_offline(self, mock_data_adapter):
        offline_executor = MagicMock(spec=MT5Executor)
        offline_executor.connect.return_value = False

        verifier = DemoVerifier(executor=offline_executor, data_adapter=mock_data_adapter)
        report = verifier.run_full_verification()

        assert report.terminal_connected is False
        assert report.passed is False
        assert "TERMINAL OFFLINE" in report.summary() or "OFFLINE" in report.summary()
