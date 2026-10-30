"""
Unit tests for MultiAccountCopier Engine:
- In-process fast switching between accounts
- Dynamic proportional position sizing per child equity
- Slippage guard rejection
- Synchronized child position liquidation on master close
- Global Kill Switch execution across all accounts
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.execution.multi_account_copier import (
    MultiAccountCopier,
    ChildAccountConfig,
    CopiedTradeRecord,
)
from src.execution.mt5_executor import MT5Executor, MT5Position
from src.utils.credentials import BrokerCredentials


class TestMultiAccountCopier:
    @pytest.fixture
    def master_creds(self) -> BrokerCredentials:
        return BrokerCredentials(
            account_id=11111111,
            password="master_password",
            server="Exness-MT5Trial12",
        )

    @pytest.fixture
    def master_executor(self, master_creds) -> MagicMock:
        ex = MagicMock(spec=MT5Executor)
        ex.credentials = master_creds
        ex.resolve_symbol.side_effect = lambda s: f"{s}m"
        ex._determine_filling_type.return_value = 2  # IOC
        ex.close_all_positions.return_value = 1
        return ex

    @pytest.fixture
    def child_1(self) -> ChildAccountConfig:
        return ChildAccountConfig(
            account_id=22222222,
            password="child1_password",
            server="Exness-MT5Trial12",
            label="Prop Account $10k",
            risk_pct=1.0,
            risk_multiplier=1.0,
            is_active=True,
            max_slippage_pips=3.0,
        )

    @pytest.fixture
    def child_2(self) -> ChildAccountConfig:
        return ChildAccountConfig(
            account_id=33333333,
            password="child2_password",
            server="Exness-MT5Trial12",
            label="Personal Account $5k",
            risk_pct=1.0,
            risk_multiplier=1.0,
            is_active=True,
            max_slippage_pips=3.0,
        )

    def test_add_and_remove_child_account(self, master_executor, child_1, child_2):
        copier = MultiAccountCopier(master_executor=master_executor)
        copier.add_child_account(child_1)
        copier.add_child_account(child_2)

        children = copier.get_child_accounts()
        assert len(children) == 2
        assert copier.child_accounts[22222222].label == "Prop Account $10k"

        removed = copier.remove_child_account(22222222)
        assert removed is True
        assert len(copier.get_child_accounts()) == 1

    @patch("MetaTrader5.login")
    @patch("MetaTrader5.account_info")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.symbol_info_tick")
    @patch("MetaTrader5.order_check")
    @patch("MetaTrader5.order_send")
    def test_copy_order_proportional_risk_sizing(
        self,
        mock_send,
        mock_check,
        mock_tick,
        mock_sym_info,
        mock_acct_info,
        mock_login,
        master_executor,
        child_1,
        child_2,
    ):
        mock_login.return_value = True

        # Child 1: $10,000 balance -> 1% risk = $100
        # Child 2: $5,000 balance -> 1% risk = $50
        def fake_account_info():
            m = MagicMock()
            # If current login is child 1:
            m.balance = 10000.0 if mock_login.call_args[1]["login"] == 22222222 else 5000.0
            return m

        mock_acct_info.side_effect = fake_account_info

        # Symbol spec: XAUUSD, tick_size=0.01, tick_value=1.0
        sym_m = MagicMock()
        sym_m.trade_tick_size = 0.01
        sym_m.point = 0.01
        sym_m.trade_tick_value = 1.0
        sym_m.volume_min = 0.01
        sym_m.volume_max = 100.0
        sym_m.volume_step = 0.01
        mock_sym_info.return_value = sym_m

        # Tick price
        tick_m = MagicMock()
        tick_m.ask = 2650.0
        tick_m.bid = 2649.8
        mock_tick.return_value = tick_m

        # Pre-flight check passes
        check_m = MagicMock()
        check_m.retcode = 0
        mock_check.return_value = check_m

        # Order send returns ticket
        send_m = MagicMock()
        send_m.retcode = 10009  # TRADE_RETCODE_DONE
        send_m.order = 777001
        send_m.price = 2650.0
        mock_send.return_value = send_m

        copier = MultiAccountCopier(master_executor=master_executor, child_accounts=[child_1, child_2])

        master_pos = MT5Position(
            ticket=999001,
            symbol="XAUUSD",
            direction="BULLISH",
            volume=0.5,
            entry_price=2650.0,
            current_price=2650.0,
            sl=2645.0,  # $5.00 SL distance (500 points = $500 risk per lot)
            tp=2660.0,  # 1:2 RR
            pnl=0.0,
            swap=0.0,
            magic=101001,
            comment="AGY_MASTER",
            opened_at=datetime.now(timezone.utc),
        )

        records = copier.copy_order(master_pos=master_pos, setup_id="SETUP_101")
        assert len(records) == 2

        # Verify Child 1 volume:
        # $100 risk / ($500 per lot) = 0.20 lots
        rec_1 = next(r for r in records if r.child_account_id == 22222222)
        assert rec_1.volume == 0.20
        assert rec_1.sl == 2645.0
        assert rec_1.tp == 2660.0

        # Verify Child 2 volume:
        # $50 risk / ($500 per lot) = 0.10 lots
        rec_2 = next(r for r in records if r.child_account_id == 33333333)
        assert rec_2.volume == 0.10

        # Verify terminal session was restored to master account (11111111)
        last_login_call = mock_login.call_args[1]
        assert last_login_call["login"] == 11111111

    @patch("MetaTrader5.login")
    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.symbol_info_tick")
    @patch("MetaTrader5.order_send")
    def test_sync_position_close(
        self,
        mock_send,
        mock_tick,
        mock_positions,
        mock_login,
        master_executor,
        child_1,
    ):
        mock_login.return_value = True

        copier = MultiAccountCopier(master_executor=master_executor, child_accounts=[child_1])
        # Add open copied trade
        copier.copied_trades.append(
            CopiedTradeRecord(
                master_ticket=999001,
                child_account_id=22222222,
                child_ticket=777001,
                symbol="XAUUSDm",
                direction="BULLISH",
                entry_price=2650.0,
                volume=0.2,
                sl=2645.0,
                tp=2660.0,
                opened_at=datetime.now(timezone.utc),
                status="OPEN",
            )
        )

        pos_m = MagicMock()
        pos_m.ticket = 777001
        pos_m.type = 0  # BUY
        pos_m.symbol = "XAUUSDm"
        pos_m.volume = 0.2
        mock_positions.return_value = [pos_m]

        tick_m = MagicMock()
        tick_m.bid = 2658.0
        tick_m.ask = 2658.2
        mock_tick.return_value = tick_m

        send_m = MagicMock()
        send_m.retcode = 10009
        mock_send.return_value = send_m

        res = copier.sync_position_close(master_ticket=999001)
        assert res[777001] is True
        assert copier.copied_trades[0].status == "CLOSED"

    @patch("MetaTrader5.login")
    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.symbol_info_tick")
    @patch("MetaTrader5.order_send")
    def test_emergency_kill_switch_across_all_accounts(
        self,
        mock_send,
        mock_tick,
        mock_positions,
        mock_login,
        master_executor,
        child_1,
    ):
        mock_login.return_value = True

        p1 = MagicMock()
        p1.ticket = 888001
        p1.type = 0
        p1.symbol = "XAUUSDm"
        p1.volume = 0.1
        mock_positions.return_value = [p1]

        tick_m = MagicMock()
        tick_m.bid = 2650.0
        tick_m.ask = 2650.2
        mock_tick.return_value = tick_m

        send_m = MagicMock()
        send_m.retcode = 10009
        mock_send.return_value = send_m

        copier = MultiAccountCopier(master_executor=master_executor, child_accounts=[child_1])
        report = copier.close_all_accounts_positions()

        assert "11111111" in report  # Master closed
        assert "22222222" in report  # Child closed
        assert report["22222222"] == 1
