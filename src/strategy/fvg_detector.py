"""
FVG Detection, Swing/Liquidity-Sweep Detection, and Reference-Candle Logic.

This is the core strategy module. All rules are deterministic and explicit.
No AI, no probabilistic decisions, no look-ahead.

Key rules:
  - An FVG requires THREE COMPLETED candles.
  - A swing requires pivot_left_bars candles to the left AND pivot_right_bars
    candles to the right — meaning the pivot candle is already confirmed history.
  - The reference candle is the LAST completed candle that entered/intersected
    the FVG during the retracement. Once saved it is FROZEN.
  - Entry trigger = ref_candle.high (bullish) or ref_candle.low (bearish).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.data.candle import Candle
from src.utils.logging_config import get_logger

log = get_logger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class FVG:
    """A detected Fair Value Gap."""
    id: str
    symbol: str
    timeframe: str
    direction: str           # "BULLISH" or "BEARISH"
    fvg_high: float          # Upper boundary of the gap
    fvg_low: float           # Lower boundary of the gap
    c1_time: datetime
    c3_time: datetime        # Time when gap was confirmed (C3 close)
    c1_high: float
    c1_low: float
    c3_high: float
    c3_low: float
    is_valid: bool = True

    @property
    def size(self) -> float:
        return self.fvg_high - self.fvg_low

    def contains_price(self, price: float) -> bool:
        """True if price is within or on the boundary of the gap."""
        return self.fvg_low <= price <= self.fvg_high

    def candle_intersects(self, candle: Candle) -> bool:
        """
        True if the candle's range intersects the FVG.
        A candle intersects when its low is below fvg_high AND
        its high is above fvg_low — i.e. some overlap exists.
        """
        return candle.low < self.fvg_high and candle.high > self.fvg_low


@dataclass
class Swing:
    """A confirmed swing high or swing low."""
    candle: Candle
    level: float          # The pivot price (swing high.high or swing low.low)
    direction: str        # "HIGH" or "LOW"
    confirmed_at: datetime   # Time of the rightmost confirmation candle


@dataclass
class LiquiditySweep:
    """A confirmed liquidity sweep event."""
    swing: Swing
    sweep_candle: Candle
    direction: str          # "BULLISH" (swept low) or "BEARISH" (swept high)
    swept_level: float
    sweep_extreme: float    # Lowest low of sweep candle (bull) / highest high (bear)


@dataclass
class ReferenceCandle:
    """
    The FROZEN retracement candle.

    Saved when: a completed candle entered or extended into the FVG during
    the retracement phase. Updated to the MOST RECENT such candle until the
    gap-exit condition fires, after which it is frozen.
    """
    candle: Candle
    is_frozen: bool = False

    @property
    def trigger_high(self) -> float:
        return self.candle.high

    @property
    def trigger_low(self) -> float:
        return self.candle.low


# ── Detectors ─────────────────────────────────────────────────────────────────

class FVGDetector:
    """
    Scans a list of completed candles for bullish and bearish FVGs.

    Usage:
        detector = FVGDetector(symbol, timeframe, min_gap_pips, pip_size)
        fvgs = detector.find_new_fvgs(candles, known_ids)
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        min_gap_pips: float = 5.0,
        pip_size: float = 0.01,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.min_gap_pips = min_gap_pips
        self.pip_size = pip_size

    def _gap_pips(self, gap_size: float) -> float:
        return gap_size / self.pip_size if self.pip_size > 0 else gap_size

    def find_all_fvgs(
        self, candles: list[Candle]
    ) -> list[FVG]:
        """
        Scan the full candle list and return every detected FVG.
        Requires at least 3 candles. The last candle in the list must be
        a completed bar (callers must strip the forming bar first).
        """
        if len(candles) < 3:
            return []

        results: list[FVG] = []
        for i in range(len(candles) - 2):
            c1, c2, c3 = candles[i], candles[i + 1], candles[i + 2]
            fvg = self._check_triple(c1, c2, c3)
            if fvg is not None:
                results.append(fvg)
        return results

    def find_new_fvgs(
        self, candles: list[Candle], known_ids: set[str]
    ) -> list[FVG]:
        """Return only FVGs not already in known_ids."""
        all_fvgs = self.find_all_fvgs(candles)
        return [f for f in all_fvgs if f.id not in known_ids]

    def _make_id(self, c1: Candle, direction: str) -> str:
        from src.utils.ids import setup_id
        return setup_id(self.symbol, direction, c1.time)

    def _check_triple(
        self, c1: Candle, c2: Candle, c3: Candle
    ) -> FVG | None:
        # ── Bullish FVG: C1.high < C3.low ────────────────────────────────────
        if c1.high < c3.low:
            gap_size = c3.low - c1.high
            if self._gap_pips(gap_size) >= self.min_gap_pips:
                return FVG(
                    id=self._make_id(c1, "BULLISH"),
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    direction="BULLISH",
                    fvg_high=c3.low,
                    fvg_low=c1.high,
                    c1_time=c1.time,
                    c3_time=c3.time,
                    c1_high=c1.high,
                    c1_low=c1.low,
                    c3_high=c3.high,
                    c3_low=c3.low,
                )

        # ── Bearish FVG: C1.low > C3.high ────────────────────────────────────
        if c1.low > c3.high:
            gap_size = c1.low - c3.high
            if self._gap_pips(gap_size) >= self.min_gap_pips:
                return FVG(
                    id=self._make_id(c1, "BEARISH"),
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    direction="BEARISH",
                    fvg_high=c1.low,
                    fvg_low=c3.high,
                    c1_time=c1.time,
                    c3_time=c3.time,
                    c1_high=c1.high,
                    c1_low=c1.low,
                    c3_high=c3.high,
                    c3_low=c3.low,
                )

        return None


class SwingDetector:
    """
    Detects confirmed swing highs and lows.

    A swing HIGH at index i is confirmed when:
      candles[i].high > candles[i-j].high  for all j in 1..left_bars
      AND candles[i].high > candles[i+k].high  for all k in 1..right_bars

    The pivot candle is confirmed only after right_bars additional candles
    have closed — ensuring no look-ahead bias.

    Returns swings using the position in the candle list at which they
    become confirmed (i.e. index i + right_bars in the full list).
    """

    def __init__(self, left_bars: int = 5, right_bars: int = 5) -> None:
        if left_bars < 1 or right_bars < 1:
            raise ValueError("left_bars and right_bars must be >= 1")
        self.left_bars = left_bars
        self.right_bars = right_bars

    def find_swings(self, candles: list[Candle]) -> list[Swing]:
        """Return all confirmed swings in the candle list."""
        required = self.left_bars + 1 + self.right_bars
        if len(candles) < required:
            return []

        swings: list[Swing] = []
        for i in range(self.left_bars, len(candles) - self.right_bars):
            pivot = candles[i]

            is_high = all(
                pivot.high > candles[i - j].high
                for j in range(1, self.left_bars + 1)
            ) and all(
                pivot.high > candles[i + k].high
                for k in range(1, self.right_bars + 1)
            )

            is_low = all(
                pivot.low < candles[i - j].low
                for j in range(1, self.left_bars + 1)
            ) and all(
                pivot.low < candles[i + k].low
                for k in range(1, self.right_bars + 1)
            )

            if is_high:
                confirmed_at = candles[i + self.right_bars].time
                swings.append(
                    Swing(
                        candle=pivot,
                        level=pivot.high,
                        direction="HIGH",
                        confirmed_at=confirmed_at,
                    )
                )
            if is_low:
                confirmed_at = candles[i + self.right_bars].time
                swings.append(
                    Swing(
                        candle=pivot,
                        level=pivot.low,
                        direction="LOW",
                        confirmed_at=confirmed_at,
                    )
                )

        return swings

    def latest_swing_high(self, candles: list[Candle]) -> Swing | None:
        swings = self.find_swings(candles)
        highs = [s for s in swings if s.direction == "HIGH"]
        return highs[-1] if highs else None

    def latest_swing_low(self, candles: list[Candle]) -> Swing | None:
        swings = self.find_swings(candles)
        lows = [s for s in swings if s.direction == "LOW"]
        return lows[-1] if lows else None


class LiquiditySweepDetector:
    """
    Detects liquidity sweeps against confirmed swing highs/lows.

    Bullish sweep:
      - A completed candle trades BELOW a confirmed swing low
        (candle.low < swing.level)
      - AND that candle CLOSES BACK ABOVE the swing low
        (candle.close > swing.level)

    Bearish sweep:
      - A completed candle trades ABOVE a confirmed swing high
        (candle.high > swing.level)
      - AND that candle CLOSES BACK BELOW the swing high
        (candle.close < swing.level)
    """

    def find_sweeps(
        self,
        candles: list[Candle],
        swings: list[Swing],
    ) -> list[LiquiditySweep]:
        """
        Scan candles for sweeps of the provided swings.
        A candle can only sweep a swing that was CONFIRMED before
        the candle's open time (no look-ahead).
        """
        sweeps: list[LiquiditySweep] = []

        for candle in candles:
            for swing in swings:
                # Swing must be confirmed before this candle formed
                if swing.confirmed_at >= candle.time:
                    continue

                if swing.direction == "LOW":
                    # Bullish sweep: wick below then close above
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

                elif swing.direction == "HIGH":
                    # Bearish sweep: wick above then close below
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


class ReferenceCandelSelector:
    """
    Identifies and freezes the retracement reference candle inside a FVG.

    Rules:
    - A candle QUALIFIES when:
        1. It is a COMPLETED candle.
        2. Its range intersects the FVG (candle_intersects returns True).
        3. It participates in the retracement direction:
           - Bullish setup: the retracement moves price DOWN into the FVG,
             so qualifying candles are those whose low <= fvg_high
             (touching or entering the gap from above).
           - Bearish setup: the retracement moves price UP into the FVG,
             so qualifying candles are those whose high >= fvg_low
             (touching or entering from below).
    - Among all qualifying candles the MOST RECENT is selected.
    - Once the reference candle is saved it is FROZEN. Subsequent candles
      inside the gap do NOT replace it.
    - If no qualifying candle can be unambiguously identified, the setup
      is REJECTED (not silently defaulted to a random candle).
    """

    @staticmethod
    def find_reference_candle(
        fvg: FVG,
        candles_in_retracement: list[Candle],
    ) -> ReferenceCandle | None:
        """
        From a list of completed candles observed during the retracement phase,
        return the most recent one that qualifies as the reference candle.

        Returns None if no qualifying candle exists (setup should be rejected).
        """
        qualifying: list[Candle] = []

        for candle in candles_in_retracement:
            if not fvg.candle_intersects(candle):
                continue

            if fvg.direction == "BULLISH":
                # Retracement = price moving DOWN; candle must reach into the gap
                if candle.low <= fvg.fvg_high:
                    qualifying.append(candle)
            else:  # BEARISH
                # Retracement = price moving UP; candle must reach into the gap
                if candle.high >= fvg.fvg_low:
                    qualifying.append(candle)

        if not qualifying:
            log.warning(
                "no_reference_candle_found",
                fvg_id=fvg.id,
                symbol=fvg.symbol,
                direction=fvg.direction,
                candidates=len(candles_in_retracement),
            )
            return None

        # Select the most recent qualifying candle
        most_recent = max(qualifying, key=lambda c: c.time)
        ref = ReferenceCandle(candle=most_recent, is_frozen=False)

        log.info(
            "reference_candle_selected",
            fvg_id=fvg.id,
            symbol=fvg.symbol,
            direction=fvg.direction,
            ref_time=most_recent.time.isoformat(),
            ref_high=most_recent.high,
            ref_low=most_recent.low,
        )
        return ref

    @staticmethod
    def freeze(ref: ReferenceCandle) -> ReferenceCandle:
        """Return a frozen copy of the reference candle."""
        return ReferenceCandle(candle=ref.candle, is_frozen=True)


class EntryTriggerChecker:
    """
    Evaluates whether the entry trigger condition has been met.

    Two modes:
      - candle_close: trigger fires when a COMPLETED candle closes
        beyond the trigger level.
      - tick_break: trigger fires when a live tick price crosses
        the trigger level (uses bid for shorts, ask for longs).
    """

    @staticmethod
    def check_candle_close(
        fvg: FVG,
        ref: ReferenceCandle,
        new_candle: Candle,
    ) -> bool:
        """
        Candle-close mode: return True if `new_candle` (completed) closes
        beyond the frozen trigger level.
        """
        if not ref.is_frozen:
            raise ValueError("Reference candle must be frozen before checking trigger")

        if fvg.direction == "BULLISH":
            return new_candle.close > ref.trigger_high
        else:
            return new_candle.close < ref.trigger_low

    @staticmethod
    def check_tick_break(
        fvg: FVG,
        ref: ReferenceCandle,
        bid: float,
        ask: float,
    ) -> bool:
        """
        Tick-break mode: return True if the current market price has
        crossed the trigger level.

        For a bullish setup the executable buy price is the ASK.
        For a bearish setup the executable sell price is the BID.
        """
        if not ref.is_frozen:
            raise ValueError("Reference candle must be frozen before checking trigger")

        if fvg.direction == "BULLISH":
            return ask > ref.trigger_high
        else:
            return bid < ref.trigger_low
