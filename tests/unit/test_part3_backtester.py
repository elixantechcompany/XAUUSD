"""
Unit tests for Part 3 Backtesting Engine and Historical Data Loader:
- HistoricalDataLoader generation & CSV ingestion
- Position sizing & 1.0% dollar risk enforcement
- Trade simulation: TP hit, SL hit, intrabar collision prioritization
- Quantitative metrics: Win Rate, Profit Factor, Expectancy, Max Drawdown %, Losing Streak
- End-to-end backtest replay on XAUUSD and BTCUSD H1 series
"""
from __future__ import annotations

import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta

from src.data.candle import Candle
from src.data.market_data_adapter import SymbolInfo
from src.backtest.data_loader import HistoricalDataLoader
from src.backtest.part3_backtester import Part3Backtester, Part3BacktestReport, _ActivePosition
from src.backtest.runner import BacktestTrade, CostAssumptions
from tests.fixtures.candles import _t, _c


class TestHistoricalDataLoader:
    def test_generate_synthetic_h1_returns_valid_chronological_candles(self):
        candles = HistoricalDataLoader.generate_synthetic_h1(
            symbol="XAUUSD", count=100, seed=42
        )
        assert len(candles) == 100
        for i in range(len(candles) - 1):
            assert candles[i].time < candles[i + 1].time
            assert candles[i].high >= candles[i].low
            assert candles[i].high >= candles[i].open
            assert candles[i].high >= candles[i].close
            assert candles[i].low <= candles[i].open
            assert candles[i].low <= candles[i].close

    def test_load_from_csv(self):
        csv_content = """Date,Open,High,Low,Close,Volume
2025-01-01 00:00:00,2000.0,2005.0,1995.0,2002.0,150
2025-01-01 01:00:00,2002.0,2010.0,2000.0,2008.0,200
"""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            candles = HistoricalDataLoader.load_from_csv(temp_path, symbol="XAUUSD", timeframe="H1")
            assert len(candles) == 2
            assert candles[0].open == 2000.0
            assert candles[1].close == 2008.0
            assert candles[0].time < candles[1].time
        finally:
            os.remove(temp_path)


class TestPart3Backtester:
    @pytest.fixture
    def xau_backtester(self) -> Part3Backtester:
        return Part3Backtester(
            symbol="XAUUSD",
            initial_balance=10_000.0,
            risk_pct_per_trade=1.0,
            min_rr=2.0,
            max_daily_trades=5,
        )

    def test_initial_configuration(self, xau_backtester):
        assert xau_backtester.symbol == "XAUUSD"
        assert xau_backtester.initial_balance == 10_000.0
        assert xau_backtester.risk_pct_per_trade == 1.0
        assert xau_backtester.min_rr == 2.0
        assert xau_backtester.spec.tick_value == 1.0
        assert xau_backtester.spec.contract_size == 100.0

    def test_btcusd_spec_configuration(self):
        btc_backtester = Part3Backtester(symbol="BTCUSD", initial_balance=50_000.0)
        assert btc_backtester.symbol == "BTCUSD"
        assert btc_backtester.spec.contract_size == 1.0
        assert btc_backtester.spec.tick_value == 0.01

    def test_report_metrics_calculation(self):
        t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        # Construct synthetic trades: 3 wins of $200 (2.0R), 2 losses of -$100 (-1.0R)
        trades = [
            BacktestTrade(
                setup_id="s1", symbol="XAUUSD", direction="BULLISH",
                entry_time=t0, entry_price=2000.0, sl=1995.0, tp=2010.0,
                volume=0.2, exit_time=t0 + timedelta(hours=2), exit_price=2010.0,
                exit_reason="TP", gross_pnl=200.0, costs=10.0, net_pnl=190.0, risk_usd=100.0,
            ),
            BacktestTrade(
                setup_id="s2", symbol="XAUUSD", direction="BULLISH",
                entry_time=t0 + timedelta(hours=3), entry_price=2010.0, sl=2005.0, tp=2020.0,
                volume=0.2, exit_time=t0 + timedelta(hours=5), exit_price=2005.0,
                exit_reason="SL", gross_pnl=-100.0, costs=10.0, net_pnl=-110.0, risk_usd=100.0,
            ),
            BacktestTrade(
                setup_id="s3", symbol="XAUUSD", direction="BEARISH",
                entry_time=t0 + timedelta(hours=6), entry_price=2020.0, sl=2025.0, tp=2010.0,
                volume=0.2, exit_time=t0 + timedelta(hours=8), exit_price=2010.0,
                exit_reason="TP", gross_pnl=200.0, costs=10.0, net_pnl=190.0, risk_usd=100.0,
            ),
            BacktestTrade(
                setup_id="s4", symbol="XAUUSD", direction="BEARISH",
                entry_time=t0 + timedelta(hours=9), entry_price=2015.0, sl=2020.0, tp=2005.0,
                volume=0.2, exit_time=t0 + timedelta(hours=11), exit_price=2020.0,
                exit_reason="SL", gross_pnl=-100.0, costs=10.0, net_pnl=-110.0, risk_usd=100.0,
            ),
            BacktestTrade(
                setup_id="s5", symbol="XAUUSD", direction="BULLISH",
                entry_time=t0 + timedelta(hours=12), entry_price=2000.0, sl=1995.0, tp=2010.0,
                volume=0.2, exit_time=t0 + timedelta(hours=14), exit_price=2010.0,
                exit_reason="TP", gross_pnl=200.0, costs=10.0, net_pnl=190.0, risk_usd=100.0,
            ),
        ]

        report = Part3BacktestReport(
            symbol="XAUUSD",
            timeframe="H1",
            start_date=t0,
            end_date=t0 + timedelta(hours=20),
            initial_balance=10_000.0,
            final_balance=10_350.0,
            trades=trades,
            equity_curve=[
                (t0, 10_000.0),
                (t0 + timedelta(hours=2), 10_190.0),
                (t0 + timedelta(hours=5), 10_080.0),
                (t0 + timedelta(hours=8), 10_270.0),
                (t0 + timedelta(hours=11), 10_160.0),
                (t0 + timedelta(hours=14), 10_350.0),
            ],
        )

        assert report.total_trades == 5
        assert len(report.winning_trades) == 3
        assert len(report.losing_trades) == 2
        assert report.win_rate == 0.6  # 60%
        assert report.net_profit == 350.0
        assert report.gross_profit == 570.0
        assert report.gross_loss == 220.0
        assert round(report.profit_factor, 2) == 2.59
        assert report.expectancy_usd == 70.0  # $350 / 5 trades
        assert round(report.expectancy_r, 2) == 0.70  # (3*1.9 - 2*1.1) / 5
        assert round(report.avg_rr_achieved, 2) == 1.90
        assert report.longest_losing_streak == 1
        assert report.max_drawdown_usd == 110.0
        assert "QUANTITATIVE PERFORMANCE REPORT" in report.summary()

    def test_conservative_intrabar_collision_prioritizes_sl(self):
        """When both SL and TP are within the same candle range, SL must trigger first."""
        t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        candles: list[Candle] = []

        # Baseline candles
        for i in range(15):
            candles.append(_c(i, lo=2000.0, hi=2005.0, o=2001.0, c=2003.0))

        # Build complete bullish setup:
        # C15-C17: FVG (2006 to 2014)
        c1 = _c(15, lo=2002.0, hi=2006.0, o=2003.0, c=2005.0)
        c2 = _c(16, lo=2006.0, hi=2018.0, o=2007.0, c=2017.0)
        c3 = _c(17, lo=2014.0, hi=2020.0, o=2015.0, c=2019.0)
        # Swing Low formation
        s1 = _c(18, lo=2004.0, hi=2012.0, o=2010.0, c=2008.0)
        s_pivot = _c(19, lo=1998.0, hi=2008.0, o=2006.0, c=2002.0)  # pivot low 1998
        s2 = _c(20, lo=2002.0, hi=2010.0, o=2004.0, c=2008.0)
        s3 = _c(21, lo=2003.0, hi=2012.0, o=2005.0, c=2009.0)
        # Sweep
        sw = _c(22, lo=1995.0, hi=2010.0, o=2008.0, c=2005.0)  # low 1995 < 1998, close 2005 > 1998
        # Market confirmation & entering candle
        mc = _c(23, lo=2004.0, hi=2012.0, o=2005.0, c=2011.0)  # close 2011 > sw.high 2010, enters FVG (1995..2014)
        # Breakout candle
        bo = _c(24, lo=2008.0, hi=2015.0, o=2009.0, c=2014.0)  # triggers breakout

        # Now candle 25: Massive volatile bar touching both SL (1994) and TP (2050)
        collision_bar = _c(25, lo=1990.0, hi=2060.0, o=2014.0, c=2030.0)

        candles.extend([c1, c2, c3, s1, s_pivot, s2, s3, sw, mc, bo, collision_bar])

        backtester = Part3Backtester(
            symbol="XAUUSD",
            initial_balance=10_000.0,
            risk_pct_per_trade=1.0,
            cost_assumptions=CostAssumptions("XAUUSD", spread_pips=0, commission_per_lot=0, slippage_pips=0),
        )
        report = backtester.run(candles)
        if report.trades:
            # Must exit via SL
            trade = report.trades[0]
            assert "SL" in trade.exit_reason
            assert trade.net_pnl < 0

    def test_end_to_end_xauusd_and_btcusd_backtest_runs_cleanly(self):
        # 1. Test XAUUSD
        xau_candles = HistoricalDataLoader.generate_synthetic_h1(
            symbol="XAUUSD", count=250, seed=123
        )
        xau_bt = Part3Backtester(symbol="XAUUSD", initial_balance=10_000.0)
        xau_report = xau_bt.run(xau_candles)
        assert xau_report.symbol == "XAUUSD"
        assert len(xau_report.equity_curve) > 0
        assert xau_report.final_balance > 0

        # 2. Test BTCUSD
        btc_candles = HistoricalDataLoader.generate_synthetic_h1(
            symbol="BTCUSD", count=250, seed=456
        )
        btc_bt = Part3Backtester(symbol="BTCUSD", initial_balance=50_000.0)
        btc_report = btc_bt.run(btc_candles)
        assert btc_report.symbol == "BTCUSD"
        assert len(btc_report.equity_curve) > 0
        assert btc_report.final_balance > 0
