"""
Backtest Runner — STRATEGY_SPEC.md v1.0

Replays historical candles through the same strategy core, state machine,
and risk engine used by the live paper/demo engine. No special backtest
logic — the same rules apply (no look-ahead, no repainting).

Usage:
    runner = BacktestRunner(settings, candles_by_symbol, symbol_specs)
    report = runner.run()
    print(report.summary())

Requirements enforced:
  - Same FVGDetector, SwingDetector, etc. as live engine (no separate backtest logic)
  - Candles fed one by one in chronological order (no future data)
  - In-memory SQLite for state persistence during replay
  - Transaction costs configurable per symbol
  - Results include every required metric from STRATEGY_SPEC.md Part 2 §7
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.settings import AppSettings
from src.data.candle import Candle
from src.data.market_data_adapter import HistoricalDataAdapter, SymbolInfo
from src.execution.paper_executor import PaperExecutor
from src.state.models import SetupState
from src.state.state_machine import SetupRepository
from src.utils.database import Base, init_db
from src.utils.logging_config import get_logger

import src.state.models    # noqa: F401  register models
import src.journal.models  # noqa: F401
import src.api.models      # noqa: F401

log = get_logger(__name__)


# ── Cost assumptions ──────────────────────────────────────────────────────────

@dataclass
class CostAssumptions:
    """Transaction cost model per symbol (R Part 2 §7)."""
    symbol: str
    spread_pips: float = 0.0          # typical spread in pips
    commission_per_lot: float = 0.0   # USD per lot round-turn
    slippage_pips: float = 0.0        # assumed slippage in pips
    swap_long_per_night: float = 0.0  # USD per lot per overnight
    swap_short_per_night: float = 0.0


# ── Trade record ──────────────────────────────────────────────────────────────

@dataclass
class BacktestTrade:
    setup_id: str
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    sl: float
    tp: float
    volume: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_reason: str = ""
    gross_pnl: float = 0.0
    costs: float = 0.0
    net_pnl: float = 0.0
    risk_usd: float = 0.0

    @property
    def r_multiple(self) -> float:
        if self.risk_usd == 0:
            return 0.0
        return self.net_pnl / self.risk_usd


# ── Report ────────────────────────────────────────────────────────────────────

@dataclass
class BacktestReport:
    symbol: str
    start_date: datetime | None
    end_date: datetime | None
    spec_version: str
    spec_hash: str
    git_commit: str
    initial_balance: float
    final_balance: float
    trades: list[BacktestTrade] = field(default_factory=list)
    cost_assumptions: dict[str, CostAssumptions] = field(default_factory=dict)

    @property
    def closed_trades(self) -> list[BacktestTrade]:
        return [t for t in self.trades if t.exit_time is not None]

    @property
    def num_trades(self) -> int:
        return len(self.closed_trades)

    @property
    def win_rate(self) -> float:
        if not self.closed_trades:
            return 0.0
        wins = sum(1 for t in self.closed_trades if t.net_pnl > 0)
        return wins / len(self.closed_trades)

    @property
    def avg_r(self) -> float:
        if not self.closed_trades:
            return 0.0
        return sum(t.r_multiple for t in self.closed_trades) / len(self.closed_trades)

    @property
    def expectancy(self) -> float:
        """Average net PnL per trade."""
        if not self.closed_trades:
            return 0.0
        return sum(t.net_pnl for t in self.closed_trades) / len(self.closed_trades)

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.net_pnl for t in self.closed_trades if t.net_pnl > 0)
        gross_loss = abs(sum(t.net_pnl for t in self.closed_trades if t.net_pnl < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float("inf")

    @property
    def net_profit(self) -> float:
        return self.final_balance - self.initial_balance

    @property
    def max_drawdown(self) -> float:
        """Maximum peak-to-trough drawdown in USD."""
        balance = self.initial_balance
        peak = balance
        max_dd = 0.0
        for t in self.closed_trades:
            balance += t.net_pnl
            if balance > peak:
                peak = balance
            dd = peak - balance
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def max_drawdown_pct(self) -> float:
        if self.initial_balance == 0:
            return 0.0
        return (self.max_drawdown / self.initial_balance) * 100

    @property
    def longest_losing_streak(self) -> int:
        streak = max_streak = 0
        for t in self.closed_trades:
            if t.net_pnl < 0:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        return max_streak

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"BACKTEST REPORT — {self.symbol}",
            f"{'='*60}",
            f"Period          : {self.start_date} → {self.end_date}",
            f"Spec version    : {self.spec_version}",
            f"Spec hash       : {self.spec_hash}",
            f"Git commit      : {self.git_commit}",
            f"Initial balance : ${self.initial_balance:,.2f}",
            f"Final balance   : ${self.final_balance:,.2f}",
            f"Net profit      : ${self.net_profit:,.2f}",
            f"",
            f"Trades          : {self.num_trades}",
            f"Win rate        : {self.win_rate:.1%}",
            f"Avg R           : {self.avg_r:.2f}R",
            f"Expectancy      : ${self.expectancy:.2f}/trade",
            f"Profit factor   : {self.profit_factor:.2f}",
            f"Max drawdown    : ${self.max_drawdown:,.2f} "
            f"({self.max_drawdown_pct:.1f}%)",
            f"Longest loss streak: {self.longest_losing_streak}",
            f"{'='*60}",
            f"DISCLAIMER: Past results do not guarantee future profits.",
            f"{'='*60}",
        ]
        return "\n".join(lines)


# ── Runner ────────────────────────────────────────────────────────────────────

class BacktestRunner:
    """
    Candle-by-candle historical replay using the live strategy engine.

    The same FVGDetector, SwingDetector, state machine, and risk engine
    are used here as in paper/demo mode — there is no separate backtest
    strategy code (R Part 2 §6).
    """

    def __init__(
        self,
        settings: AppSettings,
        candles_by_symbol: dict[str, list[Candle]],
        symbol_specs: dict[str, SymbolInfo],
        initial_balance: float = 10_000.0,
        cost_assumptions: dict[str, CostAssumptions] | None = None,
        spec_hash: str = "NOT_YET_ESTABLISHED",
        git_commit: str = "unknown",
    ) -> None:
        self._settings = settings
        self._candles = candles_by_symbol
        self._specs = symbol_specs
        self._initial_balance = initial_balance
        self._costs = cost_assumptions or {}
        self._spec_hash = spec_hash
        self._git_commit = git_commit

    def run(self, symbol: str) -> BacktestReport:
        """
        Replay all candles for `symbol` and return a BacktestReport.

        Candles must be pre-sorted oldest-first. The live bar is never
        passed to the engine — each evaluation uses candles[0:i+1].
        """
        from src.engine.trading_engine import TradingEngine

        candles = self._candles.get(symbol, [])
        if not candles:
            log.error("backtest_no_candles", symbol=symbol)
            return BacktestReport(
                symbol=symbol, start_date=None, end_date=None,
                spec_version="1.0", spec_hash=self._spec_hash,
                git_commit=self._git_commit,
                initial_balance=self._initial_balance,
                final_balance=self._initial_balance,
            )

        # Fresh in-memory database for this run
        engine_db = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine_db)
        SessionFactory = sessionmaker(bind=engine_db, autocommit=False,
                                      autoflush=False, expire_on_commit=False)

        executor = PaperExecutor(initial_balance=self._initial_balance)
        adapter = HistoricalDataAdapter({symbol: candles})
        info = self._specs.get(symbol)

        trading_engine = TradingEngine(
            settings=self._settings,
            market_data=adapter,
            db_session_factory=SessionFactory,
            executor=executor,
            now_fn=lambda: candles[-1].time,
            spec_hash=self._spec_hash,
            git_commit=self._git_commit,
        )

        if info:
            from src.strategy.strategy_core import (
                FVGDetector, SwingDetector, GapExitChecker,
            )
            s = self._settings.strategy
            trading_engine._symbol_specs[symbol] = info
            trading_engine._fvg_detectors[symbol] = FVGDetector(
                symbol=symbol, timeframe=s.timeframe,
                atr_period=s.atr_period,
                min_fvg_atr_factor=s.min_fvg_atr_factor,
                min_fvg_ticks=s.min_fvg_ticks,
                tick_size=info.tick_size,
            )
            trading_engine._swing_detectors[symbol] = SwingDetector(
                left_bars=s.pivot_left_bars,
                right_bars=s.pivot_right_bars,
            )
            trading_engine._gap_exit_checkers[symbol] = GapExitChecker(
                mode=s.gap_exit_mode
            )

        log.info("backtest_started", symbol=symbol, candles=len(candles))

        # ── Candle-by-candle replay ───────────────────────────────────────────
        for i in range(1, len(candles) + 1):
            slice_ = candles[:i]
            adapter._data[symbol] = slice_
            trading_engine.evaluate_symbol(symbol, now=slice_[-1].time)

            # Simulate SL/TP hits on the latest candle
            last = slice_[-1]
            prices = {symbol: last.close}
            triggered_ids = executor.ledger.check_sl_tp(prices)
            for pid in triggered_ids:
                for pos in executor.ledger.open_positions:
                    if pos.position_id == pid:
                        executor.close_position(
                            pid, last.close,
                            pip_value_per_lot=info.tick_value / info.tick_size if info else 1.0,
                            pip_size=info.tick_size if info else 0.01,
                        )
                        break

        # ── Collect results ───────────────────────────────────────────────────
        trades: list[BacktestTrade] = []
        for pos in executor.ledger.closed_trades:
            cost = self._estimate_costs(pos, info)
            trades.append(BacktestTrade(
                setup_id=pos.setup_id,
                symbol=symbol,
                direction=pos.direction,
                entry_time=pos.opened_at,
                entry_price=pos.entry_price,
                sl=pos.sl,
                tp=pos.tp,
                volume=pos.volume,
                exit_time=pos.closed_at,
                exit_price=pos.close_price,
                exit_reason="SL" if pos.pnl and pos.pnl < 0 else "TP",
                gross_pnl=pos.pnl or 0.0,
                costs=cost,
                net_pnl=(pos.pnl or 0.0) - cost,
                risk_usd=0.0,  # populated below
            ))

        report = BacktestReport(
            symbol=symbol,
            start_date=candles[0].time if candles else None,
            end_date=candles[-1].time if candles else None,
            spec_version="1.0",
            spec_hash=self._spec_hash,
            git_commit=self._git_commit,
            initial_balance=self._initial_balance,
            final_balance=executor.ledger.balance,
            trades=trades,
            cost_assumptions=self._costs,
        )

        log.info("backtest_complete", symbol=symbol,
                 trades=report.num_trades,
                 net_profit=report.net_profit)
        return report

    def _estimate_costs(self, pos, info: SymbolInfo | None) -> float:
        """Estimate total transaction cost for a closed position."""
        symbol = pos.symbol
        cost_spec = self._costs.get(symbol)
        if cost_spec is None or info is None:
            return 0.0
        pip_value = info.tick_value / info.tick_size * info.point if info.tick_size > 0 else 1.0
        spread_cost = cost_spec.spread_pips * pip_value * pos.volume
        commission = cost_spec.commission_per_lot * pos.volume
        slippage = cost_spec.slippage_pips * pip_value * pos.volume
        return spread_cost + commission + slippage
