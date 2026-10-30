"""
Unit tests for the Six Specialized Analytical Agents and Central Coordinator (Parts 4 & 5).

Covers:
- Agent 1: The Scout (volatility regimes, session detection, swing levels)
- Agent 2: The News Analyst (macroeconomic events, blackout windows, stale data UNKNOWN rule)
- Agent 3: The Chart Analyst (quantitative Part 3 strategy execution)
- Agent 4: The Skeptic (independent challenges and VETO authority)
- Agent 5: The Risk Manager (1.0% dollar risk, 1:2 RR minimum, daily limit VETO authority)
- Agent 6: The Execution Manager (broker order translation with attached SL/TP)
- Central Coordinator (consensus orchestration, decision logging, kill switch)
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from src.agents.scout import ScoutAgent, ScoutReport
from src.agents.news_analyst import NewsAnalystAgent, NewsReport, EconomicEvent
from src.agents.chart_analyst import ChartAnalystAgent, ChartAnalysisReport
from src.agents.skeptic import SkepticAgent, SkepticReport
from src.agents.risk_manager import RiskManagerAgent, RiskManagerReport
from src.agents.execution_manager import ExecutionManagerAgent, ExecutionReport
from src.agents.coordinator import CentralCoordinator, CycleResult
from src.config.settings import AppSettings, RiskSettings, StrategySettings
from src.data.candle import Candle
from src.data.market_data_adapter import SymbolInfo
from src.execution.paper_executor import PaperExecutor
from src.state.models import DecisionLog, Order

BASE = datetime(2024, 1, 1, 4, 0, 0, tzinfo=timezone.utc)  # C0=04:00, C9=13:00 (London/NY overlap)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(h: int, o: float, h_: float, l: float, c: float) -> Candle:
    return Candle(
        time=_t(h), open=o, high=h_, low=l, close=c,
        volume=100.0, symbol="XAUUSD", timeframe="H1",
    )


@pytest.fixture
def sample_symbol_info() -> SymbolInfo:
    return SymbolInfo(
        name="XAUUSD", digits=2, point=0.01, tick_size=0.01,
        tick_value=1.0, contract_size=100.0,
        volume_min=0.01, volume_max=500.0, volume_step=0.01,
        trade_stops_level=0, spread=20, currency_profit="USD",
        currency_margin="USD",
    )


@pytest.fixture
def sample_candles() -> list[Candle]:
    prefix = [
        _c(-15 + i, 2010.0 + i, 2015.0 + i, 2005.0 + i, 2010.0 + i)
        for i in range(15)
    ]
    c0 = _c(0, 2010.0, 2015.0, 2005.0, 2008.0)
    c1 = _c(1, 2008.0, 2012.0, 2000.0, 2004.0)  # Pivot Low = 2000.0
    c2 = _c(2, 2004.0, 2010.0, 2003.0, 2008.0)
    c3 = _c(3, 2008.0, 2014.0, 2005.0, 2012.0)
    c4 = _c(4, 2010.0, 2010.0, 1996.0, 2002.0)  # Sweep low 1996
    c5 = _c(5, 2002.0, 2014.0, 2001.0, 2012.0)  # FVG C1 high 2014
    c6 = _c(6, 2012.0, 2028.0, 2012.0, 2026.0)  # FVG C2
    c7 = _c(7, 2026.0, 2035.0, 2022.0, 2032.0)  # FVG C3 low 2022
    c8 = _c(8, 2024.0, 2025.0, 2018.0, 2020.0)  # Retracement enters FVG
    c9 = _c(9, 2020.0, 2030.0, 2019.0, 2028.0)  # Breakout close 2028 > 2025
    return prefix + [c0, c1, c2, c3, c4, c5, c6, c7, c8, c9]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Agent 1: The Scout Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoutAgent:
    def test_session_detection_london_ny_overlap(self, sample_candles):
        scout = ScoutAgent(symbol="XAUUSD")
        report = scout.analyze(sample_candles, current_time=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc))
        assert report.session_name == "London/NY Overlap"
        assert report.is_core_session is True
        assert report.is_rollover_window is False

    def test_session_detection_rollover_window(self, sample_candles):
        scout = ScoutAgent(symbol="XAUUSD")
        report = scout.analyze(sample_candles, current_time=datetime(2024, 1, 1, 22, 0, tzinfo=timezone.utc))
        assert report.session_name == "Rollover/Illiquid"
        assert report.is_core_session is False
        assert report.is_rollover_window is True

    def test_volatility_classification(self, sample_candles):
        scout = ScoutAgent(symbol="XAUUSD")
        report = scout.analyze(sample_candles)
        assert report.volatility_regime in ("LOW", "NORMAL", "HIGH")
        assert report.atr > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Agent 2: The News Analyst Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestNewsAnalystAgent:
    def test_stale_calendar_returns_unknown(self):
        news = NewsAnalystAgent()
        # No calendar updated -> must report UNKNOWN with risk_score=0.5
        report = news.analyze(datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc))
        assert report.status == "UNKNOWN"
        assert report.is_data_stale is True
        assert report.risk_score == 0.5
        assert report.blackout_active is False

    def test_active_high_impact_blackout_window(self):
        news = NewsAnalystAgent(blackout_minutes_before=30, blackout_minutes_after=30)
        nfp_time = datetime(2024, 1, 1, 13, 30, tzinfo=timezone.utc)
        ev = EconomicEvent(
            event_id="ev_1", name="US Non-Farm Payrolls", currency="USD",
            event_time=nfp_time, impact="HIGH",
        )
        news.update_calendar([ev], updated_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))

        # Check 15 mins before event (13:15 UTC) -> within blackout window!
        report = news.analyze(datetime(2024, 1, 1, 13, 15, tzinfo=timezone.utc))
        assert report.status == "HIGH_RISK_WINDOW"
        assert report.blackout_active is True
        assert report.risk_score == 1.0

    def test_clear_window_when_no_nearby_events(self):
        news = NewsAnalystAgent()
        ev = EconomicEvent(
            event_id="ev_2", name="US PPI", currency="USD",
            event_time=datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc), impact="HIGH",
        )
        news.update_calendar([ev], updated_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))

        # Check at 14:00 UTC -> 4 hours before event, clear!
        report = news.analyze(datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc))
        assert report.status == "CLEAR"
        assert report.blackout_active is False
        assert report.risk_score == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Agent 3: The Chart Analyst Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestChartAnalystAgent:
    def test_chart_analyst_generates_signal(self, sample_candles):
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        report = chart.analyze(sample_candles)
        assert report.has_actionable_signal is True
        assert len(report.signals) >= 1
        sig = report.signals[0]
        assert sig.direction == "BULLISH"
        assert sig.rr >= 2.0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Agent 4: The Skeptic Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSkepticAgent:
    def test_skeptic_veto_on_active_news_blackout(self, sample_candles):
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        sig = chart.analyze(sample_candles).signals[0]

        skeptic = SkepticAgent()
        news_rep = NewsReport(
            timestamp=BASE, status="HIGH_RISK_WINDOW", blackout_active=True,
            risk_score=1.0, upcoming_events=[], active_blackout_event=None,
            data_age_hours=1.0, is_data_stale=False, reason="Active blackout",
        )

        rep = skeptic.challenge(sig, sample_candles, news_report=news_rep)
        assert rep.veto is True
        assert rep.approval_recommendation is False
        assert any("News blackout" in c for c in rep.concerns)

    def test_skeptic_veto_on_rollover_window(self, sample_candles):
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        sig = chart.analyze(sample_candles).signals[0]

        skeptic = SkepticAgent(prohibit_rollover=True)
        scout_rep = ScoutReport(
            symbol="XAUUSD", timestamp=BASE, session_name="Rollover/Illiquid",
            is_core_session=False, is_rollover_window=True, atr=5.0,
            current_range=2.0, volatility_regime="LOW", latest_swing_high=2050.0,
            latest_swing_low=2000.0, swing_highs_count=1, swing_lows_count=1,
            notes="Rollover window",
        )

        rep = skeptic.challenge(sig, sample_candles, scout_report=scout_rep)
        assert rep.veto is True
        assert any("rollover" in c.lower() for c in rep.concerns)

    def test_skeptic_approves_clean_setup(self, sample_candles):
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        sig = chart.analyze(sample_candles).signals[0]

        skeptic = SkepticAgent()
        scout_rep = ScoutReport(
            symbol="XAUUSD", timestamp=BASE, session_name="London",
            is_core_session=True, is_rollover_window=False, atr=5.0,
            current_range=4.0, volatility_regime="NORMAL", latest_swing_high=2050.0,
            latest_swing_low=2000.0, swing_highs_count=1, swing_lows_count=1,
            notes="Clean session",
        )
        news_rep = NewsReport(
            timestamp=BASE, status="CLEAR", blackout_active=False,
            risk_score=0.0, upcoming_events=[], active_blackout_event=None,
            data_age_hours=2.0, is_data_stale=False, reason="Clear",
        )

        rep = skeptic.challenge(sig, sample_candles, scout_report=scout_rep, news_report=news_rep, current_spread_pips=20.0)
        assert rep.veto is False
        assert rep.approval_recommendation is True
        assert rep.confidence_score >= 0.8


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Agent 5: The Risk Manager Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskManagerAgent:
    def test_risk_manager_approves_and_sizes_volume(self, sample_candles, sample_symbol_info, db):
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        sig = chart.analyze(sample_candles).signals[0]

        risk_settings = RiskSettings(risk_pct_per_trade=1.0, min_reward_to_risk=2.0, max_spread_pips={"XAUUSD": 50.0})
        agent = RiskManagerAgent(risk_settings=risk_settings)

        report = agent.evaluate_risk(
            signal=sig, symbol_info=sample_symbol_info, equity=10_000.0, db=db
        )
        assert report.approved is True
        assert report.lot_size >= 0.01
        assert report.risk_usd > 0
        assert report.actual_rr >= 2.0

    def test_risk_manager_veto_on_concurrent_open_trade(self, sample_candles, sample_symbol_info, db):
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        sig = chart.analyze(sample_candles).signals[0]

        risk_settings = RiskSettings(risk_pct_per_trade=1.0, min_reward_to_risk=2.0, max_spread_pips={"XAUUSD": 50.0})
        agent = RiskManagerAgent(risk_settings=risk_settings)

        # Open positions count = 1 -> should reject concurrent exposure
        report = agent.evaluate_risk(
            signal=sig, symbol_info=sample_symbol_info, equity=10_000.0,
            db=db, open_positions_count=1,
        )
        assert report.approved is False
        assert "Concurrent position limit" in report.rejection_reason


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Agent 6: The Execution Manager Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionManagerAgent:
    def test_execution_manager_paper_order(self, sample_candles):
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        sig = chart.analyze(sample_candles).signals[0]

        paper = PaperExecutor(initial_balance=10_000.0)
        exec_agent = ExecutionManagerAgent(backend=paper, mode="paper")

        report = exec_agent.execute_trade(
            signal=sig, allocated_volume=0.05, current_bid=2027.80, current_ask=2028.00
        )
        assert report.success is True
        assert report.fill_price == 2028.00  # Bullish fills at Ask
        assert report.fill_volume == 0.05
        assert report.sl_confirmed is True


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Central Coordinator Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCentralCoordinator:
    def test_full_consensus_and_execution_flow(self, sample_candles, sample_symbol_info, db):
        settings = AppSettings(execution_mode="paper")
        scout = ScoutAgent(symbol="XAUUSD")
        news = NewsAnalystAgent()
        ev = EconomicEvent("ev1", "CPI", "USD", datetime(2024, 1, 1, 20, 0, tzinfo=timezone.utc), "HIGH")
        news.update_calendar([ev], updated_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))

        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        skeptic = SkepticAgent()
        risk_settings = RiskSettings(risk_pct_per_trade=1.0, min_reward_to_risk=2.0, max_spread_pips={"XAUUSD": 50.0})
        risk = RiskManagerAgent(risk_settings=risk_settings)
        paper = PaperExecutor(initial_balance=10_000.0)
        execution = ExecutionManagerAgent(backend=paper, mode="paper")

        coord = CentralCoordinator(
            symbol="XAUUSD", scout=scout, news=news, chart=chart,
            skeptic=skeptic, risk=risk, execution=execution, settings=settings,
        )

        res: CycleResult = coord.run_cycle(
            candles=sample_candles, symbol_info=sample_symbol_info,
            equity=10_000.0, db=db, live_tick={"bid": 2027.8, "ask": 2028.0},
        )

        assert res.signals_count >= 1
        assert res.consensus_approved >= 1
        assert res.executed_orders >= 1
        assert len(res.execution_reports) >= 1
        assert res.execution_reports[0].success is True

        # Verify decision log was persisted to SQLite
        logs = db.query(DecisionLog).all()
        assert len(logs) >= 1
        assert logs[-1].final_decision == "CONSENSUS_APPROVED"

        # Verify order was persisted
        orders = db.query(Order).all()
        assert len(orders) >= 1
        assert orders[-1].status == "FILLED"

    def test_kill_switch_blocks_cycle(self, sample_candles, sample_symbol_info, db):
        settings = AppSettings(execution_mode="paper")
        scout = ScoutAgent(symbol="XAUUSD")
        news = NewsAnalystAgent()
        chart = ChartAnalystAgent(symbol="XAUUSD", timeframe="H1")
        skeptic = SkepticAgent()
        risk_settings = RiskSettings(risk_pct_per_trade=1.0, min_reward_to_risk=2.0, max_spread_pips={"XAUUSD": 50.0})
        risk = RiskManagerAgent(risk_settings=risk_settings)
        paper = PaperExecutor(initial_balance=10_000.0)
        execution = ExecutionManagerAgent(backend=paper, mode="paper")

        coord = CentralCoordinator(
            symbol="XAUUSD", scout=scout, news=news, chart=chart,
            skeptic=skeptic, risk=risk, execution=execution, settings=settings,
        )

        coord.activate_kill_switch("Emergency test halt")
        assert coord.is_kill_switch_active is True

        res = coord.run_cycle(candles=sample_candles, symbol_info=sample_symbol_info, equity=10_000.0, db=db)
        assert res.executed_orders == 0
        assert res.consensus_approved == 0
        assert "Kill Switch" in res.rejection_reasons[0]
