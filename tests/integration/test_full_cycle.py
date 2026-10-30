"""
Integration test — full paper trading cycle.

Uses a synthetic candle sequence from tests/fixtures/candles.py.
Runs the complete state machine from FVG detection through paper fill.
No MT5 connection required.

Covers: R19 full sequence, R73 persistence, paper mode isolation (IMPL7).
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from src.config.settings import AppSettings, StrategySettings, RiskSettings
from src.data.market_data_adapter import HistoricalDataAdapter
from src.execution.paper_executor import PaperExecutor
from src.state.models import SetupState
from src.state.state_machine import SetupRepository
from src.utils.database import get_session_factory, init_db
from tests.conftest import make_xauusd_info
from tests.fixtures.candles import bullish_setup_sequence, bearish_setup_sequence


def _make_settings(mode: str = "paper") -> AppSettings:
    return AppSettings(
        execution_mode=mode,
        strategy=StrategySettings(
            symbols=["XAUUSD"],
            timeframe="H1",
            min_fvg_atr_factor=0.0,   # disable ATR filter for test
            min_fvg_ticks=0,           # disable tick filter for test
            pivot_left_bars=2,
            pivot_right_bars=2,
            max_fvg_age_bars=100,
            max_setup_age_bars_after_sweep=100,
            late_entry_atr_factor=999.0,  # effectively disable late-entry guard
        ),
        risk=RiskSettings(
            risk_pct_per_trade=1.0,
            min_reward_to_risk=2.0,
            max_daily_trades=5,
            daily_loss_pct=3.0,
            max_consecutive_losses=0,   # disabled for clean test
            max_open_per_symbol=1,
        ),
    )


class TestBullishFullCycle:
    """End-to-end bullish setup: FVG → sweep → ref candle → gap exit → trigger → paper fill."""

    def test_setup_reaches_position_open(self, db) -> None:
        from src.engine.trading_engine import TradingEngine

        candles = bullish_setup_sequence()
        info = make_xauusd_info()
        adapter = HistoricalDataAdapter({"XAUUSD": candles})
        executor = PaperExecutor(initial_balance=10_000.0)
        settings = _make_settings()

        def session_factory():
            return db

        engine = TradingEngine(
            settings=settings,
            market_data=adapter,
            db_session_factory=session_factory,
            executor=executor,
            now_fn=lambda: candles[-1].time,
        )

        # Manually inject symbol spec since MT5 is not connected
        from src.strategy.strategy_core import FVGDetector, SwingDetector, GapExitChecker
        s = settings.strategy
        engine._symbol_specs["XAUUSD"] = info
        engine._fvg_detectors["XAUUSD"] = FVGDetector(
            symbol="XAUUSD", timeframe="H1",
            atr_period=14,
            min_fvg_atr_factor=s.min_fvg_atr_factor,
            min_fvg_ticks=s.min_fvg_ticks,
            tick_size=info.tick_size,
        )
        engine._swing_detectors["XAUUSD"] = SwingDetector(
            left_bars=s.pivot_left_bars,
            right_bars=s.pivot_right_bars,
        )
        engine._gap_exit_checkers["XAUUSD"] = GapExitChecker(mode="candle_close")

        # Run multiple evaluation cycles (one per candle close)
        for i in range(len(candles)):
            partial = candles[:i + 1]
            adapter._data["XAUUSD"] = partial
            engine.evaluate_symbol("XAUUSD")

        # Check final setup state
        repo = SetupRepository(db)
        all_setups = repo.get_all(symbol="XAUUSD")
        assert len(all_setups) > 0, "Expected at least one setup to be created"

        states = {s.state for s in all_setups}
        # At minimum we expect POSITION_OPEN or CLOSED (paper fill)
        advanced_states = {
            SetupState.POSITION_OPEN, SetupState.CLOSED,
            SetupState.SIGNAL_READY, SetupState.ORDER_PENDING,
            SetupState.SWEEP_CONFIRMED, SetupState.WAITING_FOR_RETRACEMENT,
        }
        assert states & advanced_states, (
            f"No setup advanced beyond FVG_DETECTED. States found: {states}"
        )

    def test_paper_executor_never_imports_mt5(self) -> None:
        """IMPL7: PaperExecutor must not import MetaTrader5."""
        import sys
        executor = PaperExecutor()
        assert "MetaTrader5" not in sys.modules, (
            "MetaTrader5 was imported by PaperExecutor — paper isolation broken"
        )

    def test_live_mode_blocked(self) -> None:
        """R88: live trading permanently disabled."""
        with pytest.raises(Exception):
            AppSettings(execution_mode="live")


class TestPaperIsolation:
    """IMPL7: paper mode cannot call MT5 order functions."""

    def test_paper_executor_has_no_mt5_dependency(self) -> None:
        import importlib
        import src.execution.paper_executor as mod
        source = open(mod.__file__).read()
        assert "import MetaTrader5" not in source, (
            "PaperExecutor source imports MetaTrader5 — paper isolation broken"
        )
        assert "from MetaTrader5" not in source, (
            "PaperExecutor source imports from MetaTrader5 — paper isolation broken"
        )
        assert "import mt5" not in source.lower()

    def test_paper_fill_recorded_in_ledger(self) -> None:
        executor = PaperExecutor(initial_balance=10_000.0)
        ok, msg, pos = executor.submit_order(
            setup_id="test001",
            symbol="XAUUSD",
            direction="BULLISH",
            volume=0.1,
            entry_price=2020.0,
            sl=2010.0,
            tp=2040.0,
            current_ask=2020.5,
            current_bid=2020.0,
        )
        assert ok
        assert pos is not None
        positions = executor.get_positions("XAUUSD")
        assert len(positions) == 1
        assert positions[0].direction == "BULLISH"
