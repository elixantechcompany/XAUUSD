"""
Part 3 Backtesting Engine — Master Specification Part 12 Implementation.

Replays completed H1 candles chronologically using Part3StrategyEngine with:
- Zero lookahead bias (strict window slicing candles[:i+1])
- Exact Part 3 entry trigger on breakout of first entering candle
- Structural Stop Loss (at sweep extreme) and Take Profit (minimum 1:2 R:R)
- Sizing aligned with Risk Manager Agent (1.0% dollar risk, max 5 trades/day)
- Conservative intrabar collision handling (SL prioritized if both SL and TP hit in same bar)
- Full metrics calculation: Win Rate, Profit Factor, Expectancy, Max Drawdown %,
  Average R:R achieved, and Longest losing streak.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from typing import Optional, Sequence

from src.data.candle import Candle
from src.data.market_data_adapter import SymbolInfo
from src.strategy.part3_strategy import Part3StrategyEngine, Part3TradeSignal
from src.backtest.runner import CostAssumptions, BacktestTrade
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class Part3BacktestReport:
    """Quantitative performance report meeting all Part 12 requirements."""
    symbol: str
    timeframe: str
    start_date: datetime | None
    end_date: datetime | None
    initial_balance: float
    final_balance: float
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def winning_trades(self) -> list[BacktestTrade]:
        return [t for t in self.trades if t.net_pnl > 0]

    @property
    def losing_trades(self) -> list[BacktestTrade]:
        return [t for t in self.trades if t.net_pnl < 0]

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return len(self.winning_trades) / len(self.trades)

    @property
    def gross_profit(self) -> float:
        return sum(t.net_pnl for t in self.winning_trades)

    @property
    def gross_loss(self) -> float:
        return abs(sum(t.net_pnl for t in self.losing_trades))

    @property
    def net_profit(self) -> float:
        return self.final_balance - self.initial_balance

    @property
    def return_pct(self) -> float:
        if self.initial_balance == 0:
            return 0.0
        return (self.net_profit / self.initial_balance) * 100.0

    @property
    def profit_factor(self) -> float:
        if self.gross_loss == 0.0:
            return float("inf") if self.gross_profit > 0 else 0.0
        return self.gross_profit / self.gross_loss

    @property
    def expectancy_usd(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.net_pnl for t in self.trades) / len(self.trades)

    @property
    def expectancy_r(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.r_multiple for t in self.trades) / len(self.trades)

    @property
    def avg_rr_achieved(self) -> float:
        if not self.winning_trades:
            return 0.0
        return sum(t.r_multiple for t in self.winning_trades) / len(self.winning_trades)

    @property
    def max_drawdown_usd(self) -> float:
        peak = self.initial_balance
        max_dd = 0.0
        for _, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @property
    def max_drawdown_pct(self) -> float:
        peak = self.initial_balance
        max_dd_pct = 0.0
        for _, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            if peak > 0:
                dd_pct = ((peak - equity) / peak) * 100.0
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
        return max_dd_pct

    @property
    def longest_losing_streak(self) -> int:
        max_streak = 0
        curr_streak = 0
        for t in self.trades:
            if t.net_pnl < 0:
                curr_streak += 1
                if curr_streak > max_streak:
                    max_streak = curr_streak
            else:
                curr_streak = 0
        return max_streak

    def summary(self) -> str:
        border = "=" * 68
        lines = [
            border,
            f"  QUANTITATIVE PERFORMANCE REPORT — {self.symbol} ({self.timeframe})",
            f"  Strategy: Master Spec Part 3 Pure Sequence Engine",
            border,
            f"  Backtest Period      : {self.start_date} -> {self.end_date}",
            f"  Initial Capital      : ${self.initial_balance:,.2f}",
            f"  Final Equity         : ${self.final_balance:,.2f}",
            f"  Net Profit           : ${self.net_profit:,.2f} ({self.return_pct:+.2f}%)",
            f"  Gross Profit         : ${self.gross_profit:,.2f}",
            f"  Gross Loss           : ${self.gross_loss:,.2f}",
            "-" * 68,
            f"  Total Trades         : {self.total_trades}",
            f"  Winning Trades       : {len(self.winning_trades)}",
            f"  Losing Trades        : {len(self.losing_trades)}",
            f"  Win Rate             : {self.win_rate * 100.0:.1f}%",
            f"  Profit Factor        : {self.profit_factor:.2f}" if self.profit_factor != float("inf") else "  Profit Factor        : INF",
            f"  Expectancy ($/trade) : ${self.expectancy_usd:,.2f}",
            f"  Expectancy (R/trade) : {self.expectancy_r:+.2f}R",
            f"  Avg Winner R:R       : {self.avg_rr_achieved:.2f}R (Min Spec: 2.00R)",
            f"  Max Drawdown ($)     : ${self.max_drawdown_usd:,.2f}",
            f"  Max Drawdown (%)     : {self.max_drawdown_pct:.2f}%",
            f"  Longest Loss Streak  : {self.longest_losing_streak}",
            border,
        ]
        return "\n".join(lines)


@dataclass
class _ActivePosition:
    setup_id: str
    symbol: str
    direction: str              # "BULLISH" or "BEARISH"
    entry_time: datetime
    entry_price: float
    sl: float
    tp: float
    volume: float
    risk_usd: float


class Part3Backtester:
    """
    Simulates chronological bar-by-bar execution using Part3StrategyEngine.
    """

    def __init__(
        self,
        symbol: str,
        initial_balance: float = 10_000.0,
        risk_pct_per_trade: float = 1.0,
        min_rr: float = 2.0,
        max_daily_trades: int = 5,
        symbol_spec: SymbolInfo | None = None,
        cost_assumptions: CostAssumptions | None = None,
    ) -> None:
        self.symbol = symbol.upper()
        self.initial_balance = initial_balance
        self.risk_pct_per_trade = risk_pct_per_trade
        self.min_rr = min_rr
        self.max_daily_trades = max_daily_trades

        # Configure default specs if not supplied
        if symbol_spec is None:
            if "XAU" in self.symbol:
                self.spec = SymbolInfo(
                    name=self.symbol, digits=2, point=0.01, tick_size=0.01,
                    tick_value=1.0, contract_size=100.0, volume_min=0.01,
                    volume_max=500.0, volume_step=0.01, trade_stops_level=0,
                    spread=20, currency_profit="USD", currency_margin="USD",
                )
            else:
                self.spec = SymbolInfo(
                    name=self.symbol, digits=2, point=0.01, tick_size=0.01,
                    tick_value=0.01, contract_size=1.0, volume_min=0.01,
                    volume_max=10.0, volume_step=0.01, trade_stops_level=0,
                    spread=5000, currency_profit="USD", currency_margin="USD",
                )
        else:
            self.spec = symbol_spec

        self.costs = cost_assumptions or CostAssumptions(
            symbol=self.symbol,
            spread_pips=self.spec.spread * self.spec.point,
            commission_per_lot=2.0,
            slippage_pips=self.spec.point * 2,
        )

        self.strategy = Part3StrategyEngine(
            symbol=self.symbol,
            timeframe="H1",
            tick_size=self.spec.tick_size,
            point=self.spec.point,
            min_rr=self.min_rr,
        )

    def run(self, candles: Sequence[Candle]) -> Part3BacktestReport:
        """
        Replay candles bar-by-bar without lookahead.
        """
        if len(candles) < 15:
            return Part3BacktestReport(
                symbol=self.symbol,
                timeframe="H1",
                start_date=None,
                end_date=None,
                initial_balance=self.initial_balance,
                final_balance=self.initial_balance,
            )

        balance = self.initial_balance
        active_position: _ActivePosition | None = None
        closed_trades: list[BacktestTrade] = []
        equity_curve: list[tuple[datetime, float]] = [(candles[0].time, balance)]

        traded_setups: set[str] = set()
        daily_trades_count: dict[date, int] = {}

        for i in range(15, len(candles)):
            curr_candle = candles[i]
            window = candles[: i + 1]

            # 1. Manage Active Position (Intrabar SL/TP Check)
            if active_position is not None:
                pos = active_position
                is_closed = False
                exit_price = 0.0
                exit_reason = ""

                if pos.direction == "BULLISH":
                    hit_sl = curr_candle.low <= pos.sl
                    hit_tp = curr_candle.high >= pos.tp

                    if hit_sl and hit_tp:
                        # Conservative assumption: SL hit first
                        exit_price = pos.sl - (self.costs.slippage_pips * self.spec.point)
                        exit_reason = "SL (Collision)"
                        is_closed = True
                    elif hit_sl:
                        exit_price = pos.sl - (self.costs.slippage_pips * self.spec.point)
                        exit_reason = "SL"
                        is_closed = True
                    elif hit_tp:
                        exit_price = pos.tp
                        exit_reason = "TP"
                        is_closed = True

                else:  # BEARISH
                    hit_sl = curr_candle.high >= pos.sl
                    hit_tp = curr_candle.low <= pos.tp

                    if hit_sl and hit_tp:
                        exit_price = pos.sl + (self.costs.slippage_pips * self.spec.point)
                        exit_reason = "SL (Collision)"
                        is_closed = True
                    elif hit_sl:
                        exit_price = pos.sl + (self.costs.slippage_pips * self.spec.point)
                        exit_reason = "SL"
                        is_closed = True
                    elif hit_tp:
                        exit_price = pos.tp
                        exit_reason = "TP"
                        is_closed = True

                if is_closed:
                    # Calculate PnL & Transaction Costs
                    if pos.direction == "BULLISH":
                        price_diff = exit_price - pos.entry_price
                    else:
                        price_diff = pos.entry_price - exit_price

                    gross_pnl = (price_diff / self.spec.tick_size) * self.spec.tick_value * pos.volume
                    spread_cost = self.costs.spread_pips * (self.spec.tick_value / self.spec.tick_size) * pos.volume
                    comm_cost = self.costs.commission_per_lot * pos.volume
                    slip_cost = self.costs.slippage_pips * (self.spec.tick_value / self.spec.tick_size) * pos.volume
                    total_costs = spread_cost + comm_cost + slip_cost

                    net_pnl = gross_pnl - total_costs
                    balance += net_pnl

                    closed_trades.append(
                        BacktestTrade(
                            setup_id=pos.setup_id,
                            symbol=pos.symbol,
                            direction=pos.direction,
                            entry_time=pos.entry_time,
                            entry_price=pos.entry_price,
                            sl=pos.sl,
                            tp=pos.tp,
                            volume=pos.volume,
                            exit_time=curr_candle.time,
                            exit_price=exit_price,
                            exit_reason=exit_reason,
                            gross_pnl=gross_pnl,
                            costs=total_costs,
                            net_pnl=net_pnl,
                            risk_usd=pos.risk_usd,
                        )
                    )
                    active_position = None

            # Record equity point
            equity_curve.append((curr_candle.time, balance))

            # 2. Check for New Entry if flat
            if active_position is None:
                trade_date = curr_candle.time.date()
                if daily_trades_count.get(trade_date, 0) >= self.max_daily_trades:
                    continue

                signals = self.strategy.evaluate(window)
                if not signals:
                    continue

                # Take the latest unhandled signal
                sig = signals[-1]
                if sig.setup_id in traded_setups:
                    continue

                # Position sizing based on 1.0% dollar risk
                risk_usd = balance * (self.risk_pct_per_trade / 100.0)
                sl_distance = abs(sig.entry_price - sig.sl_price)
                if sl_distance <= 0:
                    continue

                risk_ticks = sl_distance / self.spec.tick_size
                risk_per_lot = risk_ticks * self.spec.tick_value
                if risk_per_lot <= 0:
                    continue

                raw_vol = risk_usd / risk_per_lot
                steps = math.floor(raw_vol / self.spec.volume_step)
                volume = round(steps * self.spec.volume_step, 2)
                volume = max(self.spec.volume_min, min(self.spec.volume_max, volume))

                active_position = _ActivePosition(
                    setup_id=sig.setup_id,
                    symbol=self.symbol,
                    direction=sig.direction,
                    entry_time=curr_candle.time,
                    entry_price=sig.entry_price,
                    sl=sig.sl_price,
                    tp=sig.tp_price,
                    volume=volume,
                    risk_usd=risk_usd,
                )
                traded_setups.add(sig.setup_id)
                daily_trades_count[trade_date] = daily_trades_count.get(trade_date, 0) + 1

        return Part3BacktestReport(
            symbol=self.symbol,
            timeframe="H1",
            start_date=candles[0].time,
            end_date=candles[-1].time,
            initial_balance=self.initial_balance,
            final_balance=balance,
            trades=closed_trades,
            equity_curve=equity_curve,
        )
