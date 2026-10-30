"""
Central Coordinator — Multi-Agent Consensus Controller and Pipeline Sequencer

Role:
- Orchestrates the six specialized analytical agents in strict sequence:
    1. The Scout (Market structure, volatility, session timing)
    2. The News Analyst (Macroeconomic calendar, event blackout windows)
    3. The Chart Analyst (Part 3 quantitative strategy execution)
    4. The Skeptic (Adversarial counter-argument analysis with VETO authority)
    5. The Risk Manager (1.0% dollar risk sizing and daily limit enforcement with VETO authority)
    6. The Execution Manager (Broker order dispatch with pre-attached SL/TP)
- Enforces consensus: trade dispatch requires unanimous approval from both Veto agents.
- Writes immutable decision logs and state transitions to SQLite WAL database before execution.
- Provides emergency Kill Switch functionality.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from src.agents.chart_analyst import ChartAnalystAgent, ChartAnalysisReport
from src.agents.execution_manager import ExecutionManagerAgent, ExecutionReport
from src.agents.news_analyst import NewsAnalystAgent, NewsReport
from src.agents.risk_manager import RiskManagerAgent, RiskManagerReport
from src.agents.scout import ScoutAgent, ScoutReport
from src.agents.skeptic import SkepticAgent, SkepticReport
from src.config.settings import AppSettings, get_settings
from src.data.candle import Candle
from src.data.market_data_adapter import SymbolInfo
from src.journal.models import JournalEntry
from src.state.models import DecisionLog, Order, Setup, SetupState, SetupTransition, SetupDirection
from src.state.state_machine import SetupStateMachine, SetupRepository
from src.strategy.part3_strategy import Part3TradeSignal
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class CoordinatorVerdict(str, Enum):
    APPROVED = "APPROVED"
    VETOED_BY_SKEPTIC = "VETOED_BY_SKEPTIC"
    VETOED_BY_RISK = "VETOED_BY_RISK"
    PENDING = "PENDING"
    KILL_SWITCH_ACTIVE = "KILL_SWITCH_ACTIVE"


@dataclass
class CycleResult:
    """Summary of one multi-agent coordination cycle."""
    symbol: str
    timestamp: datetime
    candles_evaluated: int
    scout_report: ScoutReport
    news_report: NewsReport
    chart_report: ChartAnalysisReport
    signals_count: int
    consensus_approved: int
    vetoed_by_skeptic: int
    vetoed_by_risk: int
    executed_orders: int
    execution_reports: list[ExecutionReport] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)


class CentralCoordinator:
    """
    Central Coordinator.
    Runs the multi-agent pipeline and enforces pipeline consensus.
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        scout: ScoutAgent | None = None,
        news: NewsAnalystAgent | None = None,
        chart: ChartAnalystAgent | None = None,
        skeptic: SkepticAgent | None = None,
        risk: RiskManagerAgent | None = None,
        execution: ExecutionManagerAgent | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.symbol = symbol
        self.scout = scout or ScoutAgent(symbol=symbol)
        self.news = news or NewsAnalystAgent()
        self.chart = chart or ChartAnalystAgent(symbol=symbol)
        self.skeptic = skeptic or SkepticAgent()
        self.risk = risk or RiskManagerAgent(self.settings.risk)
        self.execution = execution or ExecutionManagerAgent(self.settings)
        self._kill_switch_active = False
        self._kill_switch_reason: str | None = None
        self._last_verdict: CoordinatorVerdict = CoordinatorVerdict.PENDING

    @property
    def is_kill_switch_active(self) -> bool:
        return self._kill_switch_active

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch_active

    @kill_switch_active.setter
    def kill_switch_active(self, value: bool) -> None:
        self._kill_switch_active = value

    @property
    def kill_switch_reason(self) -> str | None:
        return self._kill_switch_reason

    @kill_switch_reason.setter
    def kill_switch_reason(self, value: str | None) -> None:
        self._kill_switch_reason = value

    @property
    def last_verdict(self) -> CoordinatorVerdict:
        return self._last_verdict

    def activate_kill_switch(self, reason: str = "Manual emergency halt") -> None:
        """Emergency Kill Switch — immediately halts all new trading operations."""
        self._kill_switch_active = True
        self._kill_switch_reason = reason
        self._last_verdict = CoordinatorVerdict.KILL_SWITCH_ACTIVE
        log.critical("kill_switch_activated", reason=reason)

    def trigger_kill_switch(self, reason: str = "Manual emergency halt", db: Session | None = None) -> None:
        """Alias for activate_kill_switch for API and Desktop GUI callers."""
        self.activate_kill_switch(reason=reason)

    def deactivate_kill_switch(self) -> None:
        """Deactivate Kill Switch."""
        self._kill_switch_active = False
        self._kill_switch_reason = None
        self._last_verdict = CoordinatorVerdict.PENDING
        log.info("kill_switch_deactivated")

    def run_cycle(
        self,
        candles: list[Candle],
        symbol_info: SymbolInfo,
        equity: float,
        live_tick: dict | None = None,
        db: Session | None = None,
        open_positions_count: int = 0,
        now: datetime | None = None,
    ) -> CycleResult:
        """
        Execute one full multi-agent cycle.
        """
        ts = now or (candles[-1].time if candles else datetime.now(tz=timezone.utc))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Emergency Kill Switch Check
        if self._kill_switch_active:
            log.warning("cycle_aborted_kill_switch_active", symbol=self.symbol)
            empty_scout = self.scout.analyze(candles, current_time=ts)
            empty_news = self.news.analyze(current_time=ts)
            empty_chart = ChartAnalysisReport(
                symbol=self.symbol, timestamp=ts, signals=[], candidate_setups_count=0,
                has_actionable_signal=False, summary="Kill switch active; cycle aborted.",
            )
            return CycleResult(
                symbol=self.symbol, timestamp=ts, candles_evaluated=len(candles),
                scout_report=empty_scout, news_report=empty_news, chart_report=empty_chart,
                signals_count=0, consensus_approved=0, vetoed_by_skeptic=0, vetoed_by_risk=0,
                executed_orders=0, rejection_reasons=["Emergency Kill Switch is active."],
            )

        # 1. Step 1: Agent 1 (The Scout) — Market Structure & Context
        scout_rep = self.scout.analyze(candles, current_time=ts)

        # 2. Step 2: Agent 2 (The News Analyst) — Economic Event Risk
        news_rep = self.news.analyze(current_time=ts)

        # 3. Step 3: Agent 3 (The Chart Analyst) — Part 3 Strategy Evaluation
        chart_rep = self.chart.analyze(candles, live_tick=live_tick, current_time=ts)

        result = CycleResult(
            symbol=self.symbol,
            timestamp=ts,
            candles_evaluated=len(candles),
            scout_report=scout_rep,
            news_report=news_rep,
            chart_report=chart_rep,
            signals_count=len(chart_rep.signals),
            consensus_approved=0,
            vetoed_by_skeptic=0,
            vetoed_by_risk=0,
            executed_orders=0,
        )

        if not chart_rep.signals:
            return result

        # 4. For each candidate signal, enforce consensus among analytical agents
        current_spread_pips = symbol_info.spread_pips

        for sig in chart_rep.signals:
            # 4.A Agent 4: The Skeptic (Adversarial Check with VETO Authority)
            skeptic_rep = self.skeptic.challenge(
                signal=sig,
                candles=candles,
                scout_report=scout_rep,
                news_report=news_rep,
                current_spread_pips=current_spread_pips,
            )

            if skeptic_rep.veto:
                result.vetoed_by_skeptic += 1
                reason = f"The Skeptic exercised VETO: {'; '.join(skeptic_rep.concerns)}"
                result.rejection_reasons.append(reason)
                self._record_decision_log(
                    db=db, signal=sig, decision="VETO_SKEPTIC", reason=reason,
                    spread=current_spread_pips, equity=equity, ts=ts,
                )
                continue

            # 4.B Agent 5: The Risk Manager (Position Sizing & Limits with VETO Authority)
            risk_rep = self.risk.evaluate_risk(
                signal=sig,
                symbol_info=symbol_info,
                equity=equity,
                db=db,
                open_positions_count=open_positions_count,
                trade_date=ts.date(),
            )

            if not risk_rep.approved:
                result.vetoed_by_risk += 1
                reason = f"The Risk Manager exercised VETO: {risk_rep.rejection_reason}"
                result.rejection_reasons.append(reason)
                self._record_decision_log(
                    db=db, signal=sig, decision="VETO_RISK", reason=reason,
                    spread=current_spread_pips, equity=equity, ts=ts,
                )
                continue

            # Consensus Achieved!
            result.consensus_approved += 1
            self._record_decision_log(
                db=db, signal=sig, decision="CONSENSUS_APPROVED",
                reason=f"Approved by Scout, Chart Analyst, Skeptic (conf={skeptic_rep.confidence_score:.2f}), and Risk Manager (vol={risk_rep.lot_size}).",
                spread=current_spread_pips, equity=equity, ts=ts,
            )

            # 4.C Agent 6: The Execution Manager (Order Dispatch with attached SL/TP)
            current_bid = live_tick.get("bid", sig.entry_price) if live_tick else sig.entry_price
            current_ask = live_tick.get("ask", sig.entry_price) if live_tick else sig.entry_price

            exec_rep = self.execution.execute_trade(
                signal=sig,
                allocated_volume=risk_rep.lot_size,
                current_bid=current_bid,
                current_ask=current_ask,
                symbol_info=symbol_info,
            )
            result.execution_reports.append(exec_rep)

            if exec_rep.success:
                result.executed_orders += 1
                self._persist_order(db=db, signal=sig, exec_rep=exec_rep, ts=ts)
            else:
                result.rejection_reasons.append(f"Execution failed: {exec_rep.message}")

        return result

    def _record_decision_log(
        self,
        db: Session | None,
        signal: Part3TradeSignal,
        decision: str,
        reason: str,
        spread: float,
        equity: float,
        ts: datetime,
    ) -> None:
        """Write immutable decision log before order placement."""
        if db is None:
            return
        try:
            entry = DecisionLog(
                created_at=ts,
                spec_version="1.0",
                spec_hash="MASTER_SPEC_PART_4_5",
                git_commit=None,
                symbol=signal.symbol,
                timeframe=signal.timeframe,
                setup_id=signal.setup_id,
                prev_state="ANALYZED",
                new_state=decision,
                rules_evaluated=json.dumps(["SCOUT", "NEWS", "CHART", "SKEPTIC", "RISK"]),
                rule_results=json.dumps({"decision": decision}),
                final_decision=decision,
                decision_reason=reason,
                spread_at_decision=spread,
                quote_timestamp=ts,
                equity_at_decision=equity,
            )
            db.add(entry)
            db.commit()
        except Exception as exc:
            db.rollback()
            log.error("decision_log_failed", error=str(exc))

    def _persist_order(
        self,
        db: Session | None,
        signal: Part3TradeSignal,
        exec_rep: ExecutionReport,
        ts: datetime,
    ) -> None:
        """Persist setup row, order row and journal entry."""
        if db is None:
            return
        try:
            # Ensure parent Setup row exists to satisfy foreign key constraint
            setup_row = db.get(Setup, signal.setup_id)
            if setup_row is None:
                setup_row = Setup(
                    id=signal.setup_id,
                    symbol=signal.symbol,
                    timeframe=signal.timeframe,
                    direction=SetupDirection(signal.direction),
                    state=SetupState.ENTRY_CONFIRMED,
                    created_at=ts,
                    updated_at=ts,
                    fvg_high=signal.fvg.fvg_high,
                    fvg_low=signal.fvg.fvg_low,
                    fvg_open_time=signal.fvg.c1_time,
                    fvg_c1_time=signal.fvg.c1_time,
                    fvg_c3_time=signal.fvg.c3_time,
                    fvg_atr_at_detection=signal.fvg.atr_at_detection,
                    fvg_c1_high=signal.fvg.c1_high,
                    fvg_c1_low=signal.fvg.c1_low,
                    fvg_c3_high=signal.fvg.c3_high,
                    fvg_c3_low=signal.fvg.c3_low,
                    sweep_level=signal.sweep.swept_level,
                    sweep_candle_time=signal.sweep.sweep_candle.time,
                    sweep_extreme=signal.sweep.sweep_extreme,
                    ref_candle_time=signal.entering_candle.candle.time,
                    ref_candle_open=signal.entering_candle.candle.open,
                    ref_candle_high=signal.entering_candle.candle.high,
                    ref_candle_low=signal.entering_candle.candle.low,
                    ref_candle_close=signal.entering_candle.candle.close,
                    ref_candle_frozen=True,
                    trigger_level=signal.entering_candle_high if signal.direction == "BULLISH" else signal.entering_candle_low,
                    trigger_fired_at=ts,
                    proposed_entry=signal.entry_price,
                    proposed_sl=signal.sl_price,
                    proposed_tp=signal.tp_price,
                    proposed_volume=exec_rep.fill_volume,
                    spec_version="1.0",
                )
                db.add(setup_row)
                db.flush()

            if exec_rep.success:
                setup_row.state = SetupState.POSITION_OPEN
                setup_row.updated_at = ts

            order_row = Order(
                id=exec_rep.order_id,
                setup_id=signal.setup_id,
                symbol=signal.symbol,
                direction=signal.direction,
                execution_mode=exec_rep.mode,
                requested_at=ts,
                requested_volume=exec_rep.fill_volume or 0.0,
                requested_entry=signal.entry_price,
                requested_sl=signal.sl_price,
                requested_tp=signal.tp_price,
                filled_at=ts,
                filled_price=exec_rep.fill_price,
                filled_volume=exec_rep.fill_volume,
                broker_ticket=int(exec_rep.broker_ticket) if isinstance(exec_rep.broker_ticket, int) else None,
                is_paper=(exec_rep.mode == "PAPER"),
                sl_confirmed_by_broker=exec_rep.sl_confirmed,
                status="FILLED" if exec_rep.success else "REJECTED",
                spec_version="1.0",
            )
            db.add(order_row)
            db.commit()
            log.info("order_persisted_to_db", order_id=exec_rep.order_id, ticket=exec_rep.broker_ticket)
        except Exception as exc:
            db.rollback()
            log.error("order_persistence_failed", error=str(exc))
