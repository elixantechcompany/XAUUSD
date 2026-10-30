"""
Part 3 Pure Strategy Engine — Master Specification Implementation

Implements the strict quantitative sequence defined in Master Specification Part 3:
1. Confirmed Liquidity Sweep
2. Market Confirmation (preceding-candle close break)
3. Three-Candle Fair Value Gap (FVG)
4. FVG Retracement
5. Save Candle Entering FVG (lock & freeze immediately)
6. High/Low Breakout Execution
7. Structural Stop Loss & 1:2 Take Profit

Completely deterministic, zero lookahead bias, H1 completed candles only.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.data.candle import Candle
from src.strategy.strategy_core import (
    FVG, Swing, LiquiditySweep, ReferenceCandle,
    FVGDetector, SwingDetector, LiquiditySweepDetector,
    MarketConfirmationChecker, FVGEntryCandleManager, BreakoutTriggerChecker,
    StopLossCalculator, TakeProfitCalculator, SetupExpiryChecker,
)
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Part3TradeSignal:
    """A fully confirmed trade signal ready for risk management and execution."""
    symbol: str
    timeframe: str
    direction: str              # "BULLISH" or "BEARISH"
    signal_time: datetime
    entry_price: float
    sl_price: float
    tp_price: float
    rr: float
    sweep_extreme: float
    entering_candle_high: float
    entering_candle_low: float
    setup_id: str
    fvg: FVG
    sweep: LiquiditySweep
    entering_candle: ReferenceCandle


class Part3StrategyEngine:
    """
    Executes the exact Part 3 technical strategy.

    Orchestrates the sequence:
      Liquidity Sweep -> Market Confirmation -> 3-Candle FVG ->
      Retracement -> Freeze Entering Candle -> High/Low Breakout -> Signal
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str = "H1",
        left_bars: int = 2,
        right_bars: int = 2,
        atr_period: int = 14,
        min_fvg_atr_factor: float = 0.1,
        min_fvg_ticks: int = 2,
        tick_size: float = 0.01,
        sl_buffer_atr_factor: float = 0.05,
        sl_buffer_min_ticks: int = 2,
        trade_stops_level: int = 0,
        point: float = 0.01,
        min_rr: float = 2.0,
        max_fvg_age_bars: int = 24,
        max_setup_age_bars_after_sweep: int = 12,
    ) -> None:
        if timeframe != "H1":
            raise ValueError(f"Part3StrategyEngine strictly requires timeframe='H1', got '{timeframe}'")

        self.symbol = symbol
        self.timeframe = timeframe
        self.tick_size = tick_size

        self.swing_detector = SwingDetector(left_bars=left_bars, right_bars=right_bars)
        self.fvg_detector = FVGDetector(
            symbol=symbol,
            timeframe=timeframe,
            atr_period=atr_period,
            min_fvg_atr_factor=min_fvg_atr_factor,
            min_fvg_ticks=min_fvg_ticks,
            tick_size=tick_size,
        )
        self.sweep_detector = LiquiditySweepDetector()
        self.market_confirmation_checker = MarketConfirmationChecker()
        self.entry_candle_manager = FVGEntryCandleManager()
        self.breakout_checker = BreakoutTriggerChecker()
        self.sl_calc = StopLossCalculator(
            atr_period=atr_period,
            sl_buffer_atr_factor=sl_buffer_atr_factor,
            sl_buffer_min_ticks=sl_buffer_min_ticks,
            tick_size=tick_size,
            trade_stops_level=trade_stops_level,
            point=point,
        )
        self.tp_calc = TakeProfitCalculator(min_rr=min_rr, tick_size=tick_size)
        self.expiry_checker = SetupExpiryChecker(
            max_fvg_age_bars=max_fvg_age_bars,
            max_setup_age_bars_after_sweep=max_setup_age_bars_after_sweep,
        )

    def evaluate(
        self,
        candles: list[Candle],
        live_tick: dict | None = None,
        now: datetime | None = None,
    ) -> list[Part3TradeSignal]:
        """
        Evaluate candle series against the full Part 3 sequence.
        Candles must be closed/completed bars in chronological order.
        """
        if len(candles) < 10:
            return []

        if now is None:
            now = candles[-1].time

        signals: list[Part3TradeSignal] = []

        # 1. Detect all confirmed swings
        swings = self.swing_detector.find_swings(candles)
        if not swings:
            return []

        # 2. Detect all valid 3-candle FVGs
        all_fvgs = self.fvg_detector.find_all_fvgs(candles, now=now)
        if not all_fvgs:
            return []

        # 3. For each candidate FVG, trace the sequence
        for fvg in all_fvgs:
            # Check FVG age expiry
            if self.fvg_detector.is_age_expired(fvg, candles, self.expiry_checker.max_fvg_age_bars):
                continue

            # Check FVG invalidation (closed across opposite boundary)
            invalidated = False
            for c in candles:
                if c.time > fvg.c3_time and fvg.is_fully_traversed_by(c):
                    invalidated = True
                    break
            if invalidated:
                continue

            # Find sweeps matching direction
            # For BULLISH FVG: we look for sweeps of swing LOWS (Bullish sweep)
            # For BEARISH FVG: we look for sweeps of swing HIGHS (Bearish sweep)
            target_direction = fvg.direction
            sweeps = self._find_sweeps_for_direction(target_direction, candles, swings, fvg)
            if not sweeps:
                continue

            # Iterate over qualifying sweeps (typically latest)
            for sweep in sweeps:
                # Post-sweep candles
                post_sweep_candles = [c for c in candles if c.time > sweep.sweep_candle.time]
                if not post_sweep_candles:
                    continue

                # Expiry check post sweep
                if len(post_sweep_candles) > self.expiry_checker.max_setup_age_bars_after_sweep:
                    continue

                # Invalidation check: completed candle closes beyond sweep extreme
                sweep_invalidated = False
                for c in post_sweep_candles:
                    if target_direction == "BULLISH" and c.close < sweep.sweep_extreme:
                        sweep_invalidated = True
                        break
                    elif target_direction == "BEARISH" and c.close > sweep.sweep_extreme:
                        sweep_invalidated = True
                        break
                if sweep_invalidated:
                    continue

                # 4. Step 2: Market Confirmation (preceding candle close break)
                # Must occur on sweep candle or in candles following sweep
                market_confirmed = False
                # First check sweep candle relative to candle before sweep
                sweep_idx = next((i for i, c in enumerate(candles) if c.time == sweep.sweep_candle.time), None)
                if sweep_idx is not None and sweep_idx > 0:
                    prev_c = candles[sweep_idx - 1]
                    if self.market_confirmation_checker.check_market_confirmation(
                        target_direction, sweep.sweep_candle, prev_c
                    ):
                        market_confirmed = True

                if not market_confirmed:
                    # Check post-sweep candles
                    for i, curr_c in enumerate(post_sweep_candles):
                        prev_c = post_sweep_candles[i - 1] if i > 0 else sweep.sweep_candle
                        if self.market_confirmation_checker.check_market_confirmation(
                            target_direction, curr_c, prev_c
                        ):
                            market_confirmed = True
                            break

                if not market_confirmed:
                    continue

                # 5. Step 4 & 5: FVG Retracement & Save FIRST Entering Candle
                # Look for candles entering the FVG zone after FVG formation
                candidate_retrace = [
                    c for c in candles
                    if c.time > fvg.c3_time and c.time >= sweep.sweep_candle.time
                ]
                entering_ref = self.entry_candle_manager.find_first_entering_candle(fvg, candidate_retrace)
                if entering_ref is None or not entering_ref.frozen:
                    continue

                # 6. Step 6: Breakout Execution
                # Must monitor candles after the entering candle has closed
                post_entry_candles = [
                    c for c in candles if c.time > entering_ref.candle.time
                ]
                if not post_entry_candles:
                    # Check live tick if provided
                    if live_tick:
                        triggered = self.breakout_checker.check_tick_breakout(
                            target_direction, entering_ref, live_tick.get("bid", 0.0), live_tick.get("ask", 0.0)
                        )
                        if triggered:
                            entry_price = live_tick["ask"] if target_direction == "BULLISH" else live_tick["bid"]
                            sig = self._build_signal(fvg, sweep, entering_ref, entry_price, candles, now)
                            if sig:
                                signals.append(sig)
                    continue

                # Check completed candles for breakout
                breakout_candle = None
                for c in post_entry_candles:
                    if self.breakout_checker.check_candle_breakout(target_direction, entering_ref, c):
                        breakout_candle = c
                        break

                if breakout_candle is None:
                    continue

                # Signal confirmed on the breakout candle!
                entry_price = breakout_candle.close
                sig = self._build_signal(fvg, sweep, entering_ref, entry_price, candles, breakout_candle.time)
                if sig:
                    signals.append(sig)

        return signals

    def _find_sweeps_for_direction(
        self,
        direction: str,
        candles: list[Candle],
        swings: list[Swing],
        fvg: FVG,
    ) -> list[LiquiditySweep]:
        """Find sweeps of swing pivots matching direction."""
        target_swing_type = "LOW" if direction == "BULLISH" else "HIGH"
        relevant_swings = [s for s in swings if s.direction == target_swing_type]

        sweeps: list[LiquiditySweep] = []
        for candle in candles:
            # Sweep must not be older than FVG window (e.g. within lookback)
            for swing in relevant_swings:
                if swing.confirmed_at >= candle.time:
                    continue
                if swing.direction == "LOW" and direction == "BULLISH":
                    if candle.low < swing.level and candle.close > swing.level:
                        sweeps.append(
                            LiquiditySweep(
                                swing=swing,
                                sweep_candle=candle,
                                direction="BULLISH",
                                swept_level=swing.level,
                                sweep_extreme=candle.low,
                            )
                        )
                elif swing.direction == "HIGH" and direction == "BEARISH":
                    if candle.high > swing.level and candle.close < swing.level:
                        sweeps.append(
                            LiquiditySweep(
                                swing=swing,
                                sweep_candle=candle,
                                direction="BEARISH",
                                swept_level=swing.level,
                                sweep_extreme=candle.high,
                            )
                        )
        return sweeps

    def _build_signal(
        self,
        fvg: FVG,
        sweep: LiquiditySweep,
        entering_ref: ReferenceCandle,
        entry_price: float,
        candles: list[Candle],
        signal_time: datetime,
    ) -> Part3TradeSignal | None:
        """Calculate Stop Loss, Take Profit, and R:R."""
        # Stop loss calculation
        sl_price, sl_err = self.sl_calc.calculate(fvg, sweep, entry_price, candles)
        if sl_price is None or sl_err:
            log.warning("sl_calc_failed", reason=sl_err)
            return None

        # Take profit calculation
        tp_price, actual_rr, tp_err = self.tp_calc.calculate(fvg, entry_price, sl_price)
        if tp_price is None or tp_err:
            log.warning("tp_calc_failed", reason=tp_err)
            return None

        setup_id = hashlib.sha256(
            f"{self.symbol}|{fvg.direction}|{sweep.sweep_candle.time.isoformat()}|{fvg.c1_time.isoformat()}".encode()
        ).hexdigest()[:16]

        return Part3TradeSignal(
            symbol=self.symbol,
            timeframe=self.timeframe,
            direction=fvg.direction,
            signal_time=signal_time,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            rr=actual_rr,
            sweep_extreme=sweep.sweep_extreme,
            entering_candle_high=entering_ref.trigger_high,
            entering_candle_low=entering_ref.trigger_low,
            setup_id=setup_id,
            fvg=fvg,
            sweep=sweep,
            entering_candle=entering_ref,
        )
