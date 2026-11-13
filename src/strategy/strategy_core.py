"""
New Strategy Core — STRATEGY_SPEC.md v1.0

This module implements every detection and evaluation rule from the approved
specification. It is the SOLE source of strategy logic for the new engine.

The legacy fvg_detector.py is preserved but MUST NOT be imported here or
influence any decision in this module.

All functions are deterministic:
  - same candle list + same config → same output every time
  - no clock reads, no MT5 calls, no randomness

Rule IDs are referenced in every function that enforces them.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.data.candle import Candle
from src.data.indicators import atr as compute_atr
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
SPEC_VERSION = "1.2"
SPEC_HASH_PLACEHOLDER = "NOT_YET_ESTABLISHED"


# ═══════════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FVG:
    """
    A detected and confirmed Fair Value Gap (R5, R6, R7, R10).

    Boundaries:
      Bullish: fvg_low = C1.high,  fvg_high = C3.low
      Bearish: fvg_low = C3.high,  fvg_high = C1.low
    """
    id: str                    # deterministic SHA-256 ID (R10)
    symbol: str
    timeframe: str             # always "H1" (R2)
    direction: str             # "BULLISH" or "BEARISH"
    fvg_low: float
    fvg_high: float
    c1_time: datetime          # UTC
    c3_time: datetime          # UTC — confirmation time
    c1_high: float
    c1_low: float
    c3_high: float
    c3_low: float
    atr_at_detection: float    # ATR(14) used for size filter (R8)
    created_at: datetime       # system UTC time when stored (R10)

    @property
    def size(self) -> float:
        return self.fvg_high - self.fvg_low

    def contains_price(self, price: float) -> bool:
        """True if price is within the gap boundaries (inclusive)."""
        return self.fvg_low <= price <= self.fvg_high

    def candle_intersects(self, candle: Candle) -> bool:
        """True when the candle's range has any overlap with the gap."""
        return candle.low < self.fvg_high and candle.high > self.fvg_low

    def is_fully_traversed_by(self, candle: Candle) -> bool:
        """
        R11: Bullish FVG invalidated when a completed candle closes below fvg_low.
             Bearish FVG invalidated when a completed candle closes above fvg_high.
        """
        if self.direction == "BULLISH":
            return candle.close < self.fvg_low
        else:
            return candle.close > self.fvg_high


@dataclass(frozen=True)
class Swing:
    """A confirmed swing high or low (R12, R13, R14)."""
    candle: Candle
    level: float               # pivot price (high.high or low.low)
    direction: str             # "HIGH" or "LOW"
    confirmed_at: datetime     # open time of the (pivot_index + right_bars)th candle


@dataclass(frozen=True)
class LiquiditySweep:
    """
    A confirmed liquidity sweep (R15, R16, R17, R18).

    Bullish sweep: sweep_candle.low < swing.level AND sweep_candle.close > swing.level
    Bearish sweep: sweep_candle.high > swing.level AND sweep_candle.close < swing.level
    """
    swing: Swing
    sweep_candle: Candle
    direction: str             # "BULLISH" or "BEARISH" (matches FVG direction)
    swept_level: float         # the swing level that was swept
    sweep_extreme: float       # lowest low (bull) or highest high (bear) of sweep candle


@dataclass
class ReferenceCandle:
    """
    The retracement reference candle (R21–R25).

    Mutable until frozen (R24). After freeze, trigger_level is immutable.
    """
    candle: Candle
    frozen: bool = False

    @property
    def trigger_high(self) -> float:
        """Trigger level for bullish entries (R27)."""
        return self.candle.high

    @property
    def trigger_low(self) -> float:
        """Trigger level for bearish entries (R28)."""
        return self.candle.low

    def freeze(self) -> "ReferenceCandle":
        """Return a frozen copy. After this, trigger levels are immutable (R24)."""
        return ReferenceCandle(candle=self.candle, frozen=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: deterministic ID
# ═══════════════════════════════════════════════════════════════════════════════

def _fvg_id(symbol: str, direction: str, c1_time: datetime) -> str:
    """Deterministic SHA-256 ID. Same inputs always produce same ID (R10)."""
    raw = f"{symbol}|{direction}|{c1_time.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════════════
# FVG Detector (R5, R6, R7, R8, R9, R10, R11)
# ═══════════════════════════════════════════════════════════════════════════════

class FVGDetector:
    """
    Detects Fair Value Gaps from completed H1 candle lists.

    Rules enforced:
      R2  — H1 timeframe only
      R3  — completed candles only (callers must strip live bar)
      R5  — bullish FVG definition
      R6  — bearish FVG definition
      R7  — confirmed after C3 closes
      R8  — minimum size filter (ATR-based + tick-based)
      R10 — stored fields
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        atr_period: int = 14,
        min_fvg_atr_factor: float = 0.1,
        min_fvg_ticks: int = 2,
        tick_size: float = 0.01,
    ) -> None:
        if timeframe != "H1":
            raise ValueError(
                f"FVGDetector requires timeframe='H1', got '{timeframe}' (R2)"
            )
        self.symbol = symbol
        self.timeframe = timeframe
        self.atr_period = atr_period
        self.min_fvg_atr_factor = min_fvg_atr_factor
        self.min_fvg_ticks = min_fvg_ticks
        self.tick_size = tick_size

    def _min_size(self, candles: list[Candle], up_to_index: int) -> tuple[float, float] | None:
        """
        R8: minimum gap size = max(atr_factor × ATR(14), min_ticks × tick_size).
        Returns (min_size, atr_val) tuple, or None if ATR cannot be computed.

        Enforces a hard floor of 1 tick even when both factors are zero,
        so zero-size gaps are never accepted.
        """
        window = candles[: up_to_index + 1]
        atr_val = compute_atr(window, self.atr_period)
        if atr_val is None:
            return None
        tick_min = max(self.min_fvg_ticks, 1) * self.tick_size  # B2: floor of 1 tick
        atr_min = self.min_fvg_atr_factor * atr_val
        return max(atr_min, tick_min), atr_val

    def find_all_fvgs(
        self,
        candles: list[Candle],
        now: datetime | None = None,
    ) -> list[FVG]:
        """
        Scan the complete candle list for FVGs.

        Args:
            candles: Completed H1 candles, oldest first.
                     Caller MUST have stripped the forming bar (R3).
            now:     Current UTC time for `created_at` field. If None, uses
                     the time of C3 (safe for replay/backtest).

        Returns:
            List of FVG objects passing all filters.
        """
        if len(candles) < 3:
            return []

        results: list[FVG] = []
        for i in range(len(candles) - 2):
            c1, c2, c3 = candles[i], candles[i + 1], candles[i + 2]  # noqa: F841

            direction: str | None = None
            fvg_low = fvg_high = 0.0

            # R5 — bullish
            if c1.high < c3.low:
                direction = "BULLISH"
                fvg_low = c1.high
                fvg_high = c3.low

            # R6 — bearish
            elif c1.low > c3.high:
                direction = "BEARISH"
                fvg_low = c3.high
                fvg_high = c1.low

            if direction is None:
                continue

            gap_size = fvg_high - fvg_low

            # R8 — minimum size filter
            size_result = self._min_size(candles, i + 2)
            if size_result is None:
                log.debug(
                    "fvg_rejected_atr_unavailable",
                    symbol=self.symbol,
                    c1_time=c1.time.isoformat(),
                    candles_available=len(candles[: i + 3]),
                    atr_period=self.atr_period,
                )
                continue

            min_size, atr_val = size_result
            if gap_size < min_size:
                log.debug(
                    "fvg_rejected_too_small",
                    symbol=self.symbol,
                    direction=direction,
                    c1_time=c1.time.isoformat(),
                    gap_size=gap_size,
                    min_size=min_size,
                    atr=atr_val,
                )
                continue

            fvg_id = _fvg_id(self.symbol, direction, c1.time)
            created = now if now is not None else c3.time

            results.append(
                FVG(
                    id=fvg_id,
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    direction=direction,
                    fvg_low=fvg_low,
                    fvg_high=fvg_high,
                    c1_time=c1.time,
                    c3_time=c3.time,
                    c1_high=c1.high,
                    c1_low=c1.low,
                    c3_high=c3.high,
                    c3_low=c3.low,
                    atr_at_detection=atr_val,
                    created_at=created,
                )
            )

        return results

    def find_new_fvgs(
        self,
        candles: list[Candle],
        known_ids: set[str],
        now: datetime | None = None,
    ) -> list[FVG]:
        """Return only FVGs whose IDs are not in known_ids."""
        return [f for f in self.find_all_fvgs(candles, now) if f.id not in known_ids]

    def is_age_expired(self, fvg: FVG, candles: list[Candle], max_age_bars: int) -> bool:
        """
        R9: Returns True if the FVG is older than max_age_bars completed bars.
        Counts completed candles whose open time is strictly greater than fvg.c3_time.
        """
        bars_after_c3 = sum(1 for c in candles if c.time > fvg.c3_time)
        return bars_after_c3 >= max_age_bars


# ═══════════════════════════════════════════════════════════════════════════════
# Swing Detector (R12, R13, R14)
# ═══════════════════════════════════════════════════════════════════════════════

class SwingDetector:
    """
    Detects confirmed swing highs and lows using a pivot method (R12).

    Rules enforced:
      R12 — 2-left / 2-right pivot (configurable)
      R13 — strict inequality (ties do not produce a pivot)
      R14 — pivot usable only after right_bars candles have closed
    """

    def __init__(self, left_bars: int = 2, right_bars: int = 2) -> None:
        if left_bars < 1 or right_bars < 1:
            raise ValueError(
                f"left_bars and right_bars must be >= 1, "
                f"got left={left_bars} right={right_bars}"
            )
        self.left_bars = left_bars
        self.right_bars = right_bars

    def find_swings(self, candles: list[Candle]) -> list[Swing]:
        """
        Return all confirmed swings in the candle list.

        A pivot at index i is only included if candles[i + right_bars] exists
        (i.e. right_bars candles have closed after it). — R14
        """
        required = self.left_bars + 1 + self.right_bars
        if len(candles) < required:
            return []

        swings: list[Swing] = []
        for i in range(self.left_bars, len(candles) - self.right_bars):
            pivot = candles[i]

            # R12 — strict greater-than for high pivot (R13 — no ties)
            is_high = all(
                pivot.high > candles[i - j].high
                for j in range(1, self.left_bars + 1)
            ) and all(
                pivot.high > candles[i + k].high
                for k in range(1, self.right_bars + 1)
            )

            # R12 — strict less-than for low pivot (R13 — no ties)
            is_low = all(
                pivot.low < candles[i - j].low
                for j in range(1, self.left_bars + 1)
            ) and all(
                pivot.low < candles[i + k].low
                for k in range(1, self.right_bars + 1)
            )

            # R14 — confirmed_at is the open time of the last right-bar candle
            confirmed_at = candles[i + self.right_bars].time

            if is_high:
                swings.append(
                    Swing(
                        candle=pivot,
                        level=pivot.high,
                        direction="HIGH",
                        confirmed_at=confirmed_at,
                    )
                )
            if is_low:
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
        highs = [s for s in self.find_swings(candles) if s.direction == "HIGH"]
        return highs[-1] if highs else None

    def latest_swing_low(self, candles: list[Candle]) -> Swing | None:
        lows = [s for s in self.find_swings(candles) if s.direction == "LOW"]
        return lows[-1] if lows else None


# ═══════════════════════════════════════════════════════════════════════════════
# Liquidity Sweep Detector (R15, R16, R17, R18)
# ═══════════════════════════════════════════════════════════════════════════════

class LiquiditySweepDetector:
    """
    Detects liquidity sweeps against confirmed swings (R15, R16, R17, R18).

    Rules enforced:
      R15 — bullish sweep: wick below swing low + close back above
      R16 — bearish sweep: wick above swing high + close back below
      R13 — strict inequalities (no ties)
      R17 — sweep candle must open after FVG C3 close time
    """

    def find_sweeps_for_fvg(
        self,
        fvg: FVG,
        candles: list[Candle],
        swings: list[Swing],
    ) -> list[LiquiditySweep]:
        """
        Find sweeps associated with a specific FVG.

        R17: sweep candle open time must be > fvg.c3_time.
        R14: swing must be confirmed before the sweep candle opened.

        For a bullish FVG, we look for sweeps of swing LOWS (bullish sweep).
        For a bearish FVG, we look for sweeps of swing HIGHS (bearish sweep).
        """
        target_swing_direction = "LOW" if fvg.direction == "BULLISH" else "HIGH"
        relevant_swings = [s for s in swings if s.direction == target_swing_direction]

        sweeps: list[LiquiditySweep] = []
        for candle in candles:
            # R17: sweep must occur after FVG confirmation
            if candle.time <= fvg.c3_time:
                continue

            for swing in relevant_swings:
                # R14: swing must be confirmed before this candle's open time
                if swing.confirmed_at >= candle.time:
                    continue

                if swing.direction == "LOW":
                    # R15: bullish sweep — wick below AND close back above (strict)
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
                    # R16: bearish sweep — wick above AND close back below (strict)
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


# ═══════════════════════════════════════════════════════════════════════════════
# Reference Candle Selector (R21–R25)
# ═══════════════════════════════════════════════════════════════════════════════

class ReferenceCandleSelector:
    """
    Identifies and manages the retracement reference candle (R21–R25).

    Rules enforced:
      R21 — bullish: most recent candle intersecting FVG during downward retracement
      R22 — bearish: most recent candle intersecting FVG during upward retracement
      R23 — reference candle updated until freeze
      R24 — frozen at gap exit
      R25 — setup rejected if no qualifying candle found
    """

    @staticmethod
    def find_reference_candle(
        fvg: FVG,
        retracement_candles: list[Candle],
    ) -> ReferenceCandle | None:
        """
        Find the most recent qualifying retracement candle (R21, R22).

        Args:
            fvg: The confirmed FVG for this setup.
            retracement_candles: Completed candles observed during the
                                 retracement phase (sweep candle excluded).

        Returns:
            ReferenceCandle (unfrozen) or None if no qualifying candle (R25).
        """
        qualifying: list[Candle] = []

        for candle in retracement_candles:
            if not fvg.candle_intersects(candle):
                continue

            if fvg.direction == "BULLISH":
                # R21: downward retracement — candle low must reach into or below fvg_high
                if candle.low <= fvg.fvg_high:
                    qualifying.append(candle)
            else:
                # R22: upward retracement — candle high must reach into or above fvg_low
                if candle.high >= fvg.fvg_low:
                    qualifying.append(candle)

        if not qualifying:
            log.warning(
                "no_reference_candle_found",   # R25
                fvg_id=fvg.id,
                symbol=fvg.symbol,
                direction=fvg.direction,
                candidates=len(retracement_candles),
            )
            return None

        most_recent = max(qualifying, key=lambda c: c.time)
        log.info(
            "reference_candle_selected",
            fvg_id=fvg.id,
            symbol=fvg.symbol,
            direction=fvg.direction,
            ref_time=most_recent.time.isoformat(),
            ref_high=most_recent.high,
            ref_low=most_recent.low,
        )
        return ReferenceCandle(candle=most_recent, frozen=False)


# ═══════════════════════════════════════════════════════════════════════════════
# Market Confirmation Checker (Part 3.D)
# ═══════════════════════════════════════════════════════════════════════════════

class MarketConfirmationChecker:
    """
    Evaluates Market Confirmation by checking break of preceding candle (Part 3.D).

    Rules enforced:
      Bullish: Completed candle closes strictly above immediately preceding candle's HIGH.
               candle.close > preceding_candle.high
      Bearish: Completed candle closes strictly below immediately preceding candle's LOW.
               candle.close < preceding_candle.low
    """

    @staticmethod
    def check_market_confirmation(
        direction: str,
        current_candle: Candle,
        preceding_candle: Candle,
    ) -> bool:
        """
        Check if current_candle confirms market direction relative to preceding_candle.
        Strict inequality is required.
        """
        if direction == "BULLISH":
            return current_candle.close > preceding_candle.high
        elif direction == "BEARISH":
            return current_candle.close < preceding_candle.low
        return False

    @staticmethod
    def find_market_confirmation(
        direction: str,
        candles: list[Candle],
        after_time: datetime | None = None,
    ) -> tuple[Candle, Candle] | None:
        """
        Find the earliest candle in candles (after after_time, if given)
        that closes beyond its immediately preceding candle.

        Returns (confirming_candle, preceding_candle) or None.
        """
        if len(candles) < 2:
            return None

        for i in range(1, len(candles)):
            prev_c = candles[i - 1]
            curr_c = candles[i]
            if after_time is not None and curr_c.time <= after_time:
                continue
            if MarketConfirmationChecker.check_market_confirmation(direction, curr_c, prev_c):
                return curr_c, prev_c

        return None


# ═══════════════════════════════════════════════════════════════════════════════
# FVG Entry Candle Manager (Part 3.E)
# ═══════════════════════════════════════════════════════════════════════════════

class FVGEntryCandleManager:
    """
    Identifies, locks, and freezes the first candle entering the FVG (Part 3.E).

    Rules enforced:
      1. Detects the first completed candle that enters/intersects the FVG zone.
      2. Once captured, freezes its OHLC and timestamp permanently.
      3. Prohibits any subsequent modification or replacement.
      4. Defines breakout levels:
         Bullish: breakout_high = frozen_candle.high
         Bearish: breakout_low = frozen_candle.low
    """

    @staticmethod
    def find_first_entering_candle(
        fvg: FVG,
        retracement_candles: list[Candle],
    ) -> ReferenceCandle | None:
        """
        Find the FIRST completed candle entering the FVG zone (Part 3.E).
        Candles are evaluated in strict chronological order (oldest first).

        Returns a FROZEN ReferenceCandle, or None if no candle has entered yet.
        """
        # Ensure chronological ordering
        sorted_candles = sorted(retracement_candles, key=lambda c: c.time)

        for candle in sorted_candles:
            if not fvg.candle_intersects(candle):
                continue

            if fvg.direction == "BULLISH":
                # Downward retracement reaches into or below fvg_high
                if candle.low <= fvg.fvg_high:
                    log.info(
                        "first_entering_candle_locked",
                        fvg_id=fvg.id,
                        direction="BULLISH",
                        time=candle.time.isoformat(),
                        trigger_high=candle.high,
                    )
                    return ReferenceCandle(candle=candle, frozen=True)
            else:
                # Upward retracement reaches into or above fvg_low
                if candle.high >= fvg.fvg_low:
                    log.info(
                        "first_entering_candle_locked",
                        fvg_id=fvg.id,
                        direction="BEARISH",
                        time=candle.time.isoformat(),
                        trigger_low=candle.low,
                    )
                    return ReferenceCandle(candle=candle, frozen=True)

        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Breakout Trigger Checker (Part 3.E)
# ═══════════════════════════════════════════════════════════════════════════════

class BreakoutTriggerChecker:
    """
    Evaluates breakout of the frozen entering candle's High/Low (Part 3.E).

    Rules enforced:
      Bullish: Breakout occurs when price crosses above the frozen entering candle's HIGH.
      Bearish: Breakout occurs when price crosses below the frozen entering candle's LOW.
    """

    @staticmethod
    def check_candle_breakout(
        direction: str,
        entry_ref: ReferenceCandle,
        candle: Candle,
    ) -> bool:
        """
        Candle-close breakout confirmation:
          Bullish: completed candle.close > entry_ref.trigger_high
          Bearish: completed candle.close < entry_ref.trigger_low
        """
        if not entry_ref.frozen:
            raise ValueError("Entry candle must be frozen before checking breakout (Part 3.E)")

        if direction == "BULLISH":
            return candle.close > entry_ref.trigger_high
        else:
            return candle.close < entry_ref.trigger_low

    @staticmethod
    def check_tick_breakout(
        direction: str,
        entry_ref: ReferenceCandle,
        bid: float,
        ask: float,
    ) -> bool:
        """
        Live tick breakout:
          Bullish: ask > entry_ref.trigger_high
          Bearish: bid < entry_ref.trigger_low
        """
        if not entry_ref.frozen:
            raise ValueError("Entry candle must be frozen before checking breakout (Part 3.E)")

        if direction == "BULLISH":
            return ask > entry_ref.trigger_high
        else:
            return bid < entry_ref.trigger_low


# ═══════════════════════════════════════════════════════════════════════════════
# Gap Exit Checker (R26)
# ═══════════════════════════════════════════════════════════════════════════════

class GapExitChecker:
    """
    Evaluates the gap-exit condition (R26 — PROPOSED DEFAULT: candle_close mode).

    The condition is configurable. Only 'candle_close' is implemented in v1.0.
    """

    def __init__(self, mode: str = "candle_close") -> None:
        if mode != "candle_close":
            raise NotImplementedError(
                f"Gap exit mode '{mode}' is not implemented in spec v1.0. "
                "Only 'candle_close' is supported."
            )
        self.mode = mode

    def is_gap_exited(self, fvg: FVG, candle: Candle) -> bool:
        """
        R26: Returns True when the completed candle's close confirms gap exit.

        Bullish: candle.close > fvg.fvg_high  (strict)
        Bearish: candle.close < fvg.fvg_low   (strict)
        """
        if fvg.direction == "BULLISH":
            return candle.close > fvg.fvg_high
        else:
            return candle.close < fvg.fvg_low


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Trigger Checker (R27–R31)
# ═══════════════════════════════════════════════════════════════════════════════

class EntryTriggerChecker:
    """
    Evaluates whether the entry trigger has fired (R27–R31).

    Modes:
      CANDLE_CLOSE — trigger on completed candle close beyond trigger level (R29)
      TICK_BREAK   — trigger on live executable quote crossing trigger level (R30)
    """

    @staticmethod
    def check_candle_close(
        fvg: FVG,
        ref: ReferenceCandle,
        candle: Candle,
    ) -> bool:
        """
        R29: CANDLE_CLOSE mode.

        Raises ValueError if reference candle is not frozen (R24 enforcement).
        """
        if not ref.frozen:
            raise ValueError(
                "Reference candle must be frozen before checking entry trigger (R24)"
            )
        if fvg.direction == "BULLISH":
            # R27: candle.close strictly above trigger_high
            return candle.close > ref.trigger_high
        else:
            # R28: candle.close strictly below trigger_low
            return candle.close < ref.trigger_low

    @staticmethod
    def check_tick_break(
        fvg: FVG,
        ref: ReferenceCandle,
        bid: float,
        ask: float,
        tick_time: datetime,
        max_tick_age_seconds: int = 5,
        now: datetime | None = None,
    ) -> tuple[bool, str]:
        """
        R30: TICK_BREAK mode.

        Returns (triggered: bool, rejection_reason: str).
        rejection_reason is empty string when triggered=True.

        R31: validates tick freshness, positive bid/ask, ask > bid.
        """
        if not ref.frozen:
            raise ValueError(
                "Reference candle must be frozen before checking entry trigger (R24)"
            )

        # R31: tick validity checks
        if now is None:
            now = datetime.now(tz=timezone.utc)

        age = (now - tick_time).total_seconds()
        if age > max_tick_age_seconds:
            return False, f"Tick stale: age={age:.1f}s > max={max_tick_age_seconds}s (R31)"

        if bid <= 0 or ask <= 0:
            return False, f"Invalid tick prices: bid={bid} ask={ask} (R31)"

        if ask <= bid:
            return False, f"Inverted spread: ask={ask} <= bid={bid} (R31)"

        # R30: bullish uses ask (executable buy price)
        if fvg.direction == "BULLISH":
            if ask > ref.trigger_high:
                return True, ""
            return False, f"Ask {ask} has not crossed trigger {ref.trigger_high} (R27)"
        else:
            # R30: bearish uses bid (executable sell price)
            if bid < ref.trigger_low:
                return True, ""
            return False, f"Bid {bid} has not crossed trigger {ref.trigger_low} (R28)"


# ═══════════════════════════════════════════════════════════════════════════════
# Stop-Loss Calculator (R35, R36, R37)
# ═══════════════════════════════════════════════════════════════════════════════

class StopLossCalculator:
    """
    Calculates the protective stop-loss price (R35, R36, R37).

    Rules enforced:
      R35 — structural reference: sweep candle extreme
      R36 — buffer: max(min_ticks × tick_size, sl_buffer_atr_factor × ATR(14))
      R37 — broker stop-distance and tick-increment constraints
      R38 — widening after entry is permanently prohibited
    """

    def __init__(
        self,
        atr_period: int = 14,
        sl_buffer_atr_factor: float = 0.05,
        sl_buffer_min_ticks: int = 2,
        tick_size: float = 0.01,
        trade_stops_level: int = 0,
        point: float = 0.01,
    ) -> None:
        self.atr_period = atr_period
        self.sl_buffer_atr_factor = sl_buffer_atr_factor
        self.sl_buffer_min_ticks = sl_buffer_min_ticks
        self.tick_size = tick_size
        self.trade_stops_level = trade_stops_level
        self.point = point

    def calculate(
        self,
        fvg: FVG,
        sweep: LiquiditySweep,
        entry_price: float,
        candles: list[Candle],
    ) -> tuple[float | None, str]:
        """
        Calculate the stop-loss price.

        Returns (sl_price, rejection_reason).
        sl_price is None if the trade must be rejected.
        """
        # R36: buffer = max(min_ticks × tick_size, atr_factor × ATR)
        atr_val = compute_atr(candles, self.atr_period)
        if atr_val is None:
            return None, "Cannot compute SL buffer: ATR unavailable (R36)"

        tick_buffer = self.sl_buffer_min_ticks * self.tick_size
        atr_buffer = self.sl_buffer_atr_factor * atr_val
        buffer = max(tick_buffer, atr_buffer)

        # R35: structural reference = sweep extreme ± buffer
        if fvg.direction == "BULLISH":
            raw_sl = sweep.sweep_extreme - buffer
        else:
            raw_sl = sweep.sweep_extreme + buffer

        # Round to nearest tick increment
        if self.tick_size > 0:
            import math
            if fvg.direction == "BULLISH":
                # Round down (away from entry) for bullish SL
                raw_sl = math.floor(raw_sl / self.tick_size) * self.tick_size
            else:
                # Round up (away from entry) for bearish SL
                raw_sl = math.ceil(raw_sl / self.tick_size) * self.tick_size
        raw_sl = round(raw_sl, 8)

        # R37: broker minimum stop distance
        sl_distance = abs(entry_price - raw_sl)
        min_distance = self.trade_stops_level * self.point
        if sl_distance < min_distance:
            return None, (
                f"SL distance {sl_distance:.5f} < broker minimum "
                f"{min_distance:.5f} (R37)"
            )

        return raw_sl, ""


# ═══════════════════════════════════════════════════════════════════════════════
# Take-Profit Calculator (R40, R41, R42)
# ═══════════════════════════════════════════════════════════════════════════════

class TakeProfitCalculator:
    """
    Calculates take-profit price (R40, R41, R42).

    Rules enforced:
      R40 — minimum 1:2 R:R
      R41 — TP = entry ± 2 × (entry − SL)
      R42 — conservative rounding toward entry; re-check R:R
      R43 — no trailing stops, partial TPs, break-even, or reversals
    """

    def __init__(
        self,
        min_rr: float = 2.0,
        tick_size: float = 0.01,
    ) -> None:
        if min_rr < 2.0:
            raise ValueError(
                f"min_rr={min_rr} violates the 2.0 minimum (STRATEGY_SPEC.md R40)"
            )
        self.min_rr = min_rr
        self.tick_size = tick_size

    def calculate(
        self,
        fvg: FVG,
        entry_price: float,
        sl_price: float,
    ) -> tuple[float | None, float, str]:
        """
        Calculate TP price.

        Returns (tp_price, actual_rr, rejection_reason).
        tp_price is None if minimum R:R cannot be satisfied.
        """
        import math

        sl_distance = abs(entry_price - sl_price)
        if sl_distance <= 0:
            return None, 0.0, "SL distance is zero or negative (R41)"

        # R41: raw TP = entry ± min_rr × sl_distance
        if fvg.direction == "BULLISH":
            raw_tp = entry_price + self.min_rr * sl_distance
        else:
            raw_tp = entry_price - self.min_rr * sl_distance

        # R42: conservative rounding toward entry
        if self.tick_size > 0:
            if fvg.direction == "BULLISH":
                # Round DOWN (toward entry) for bullish TP
                tp = math.floor(round(raw_tp / self.tick_size, 8)) * self.tick_size
            else:
                # Round UP (toward entry) for bearish TP
                tp = math.ceil(round(raw_tp / self.tick_size, 8)) * self.tick_size
        else:
            tp = raw_tp
        tp = round(tp, 8)

        # R42: re-check R:R after rounding
        tp_distance = abs(tp - entry_price)
        if tp_distance <= 0:
            return None, 0.0, "TP distance is zero after rounding (R42)"

        actual_rr = round(tp_distance / sl_distance, 6)
        if actual_rr < self.min_rr:
            return None, actual_rr, (
                f"R:R {actual_rr:.3f} below minimum {self.min_rr:.1f} after rounding (R40)"
            )

        return tp, actual_rr, ""


# ═══════════════════════════════════════════════════════════════════════════════
# Setup Expiry and Invalidation Checker (R9, R11, R64–R69)
# ═══════════════════════════════════════════════════════════════════════════════

class SetupExpiryChecker:
    """
    Evaluates whether a setup should be expired or invalidated (R64–R69).

    Rules enforced:
      R64 — expire after max_setup_age_bars_after_sweep post-sweep bars
      R65 — expire when FVG exceeds max_fvg_age_bars
      R66 — invalidation conditions
      R67 — bullish: close below sweep low
      R68 — bearish: close above sweep high
      R69 — no resurrection after terminal state
    """

    def __init__(
        self,
        max_fvg_age_bars: int = 24,
        max_setup_age_bars_after_sweep: int = 12,
    ) -> None:
        self.max_fvg_age_bars = max_fvg_age_bars
        self.max_setup_age_bars_after_sweep = max_setup_age_bars_after_sweep

    def check_expiry(
        self,
        fvg: FVG,
        sweep: LiquiditySweep | None,
        candles: list[Candle],
    ) -> tuple[bool, str]:
        """
        R64, R65: Returns (should_expire, reason).

        Whichever condition triggers first wins.
        """
        # R65: FVG age
        bars_since_c3 = sum(1 for c in candles if c.time > fvg.c3_time)
        if bars_since_c3 >= self.max_fvg_age_bars:
            return True, (
                f"FVG exceeded max age: {bars_since_c3} bars >= "
                f"{self.max_fvg_age_bars} (R65)"
            )

        # R64: post-sweep age
        if sweep is not None:
            bars_since_sweep = sum(
                1 for c in candles if c.time > sweep.sweep_candle.time
            )
            if bars_since_sweep >= self.max_setup_age_bars_after_sweep:
                return True, (
                    f"Setup not triggered within {bars_since_sweep} bars "
                    f"after sweep (max {self.max_setup_age_bars_after_sweep}) (R64)"
                )

        return False, ""

    def check_invalidation(
        self,
        fvg: FVG,
        sweep: LiquiditySweep | None,
        candle: Candle,
    ) -> tuple[bool, str]:
        """
        R66–R68: Check if a single completed candle invalidates the setup.

        Returns (should_invalidate, reason).
        """
        # R11: FVG fully traversed
        if fvg.is_fully_traversed_by(candle):
            return True, (
                f"FVG fully traversed (invalidated): close {candle.close:.5f} "
                f"{'<' if fvg.direction == 'BULLISH' else '>'} "
                f"fvg_{'low' if fvg.direction == 'BULLISH' else 'high'} "
                f"{fvg.fvg_low if fvg.direction == 'BULLISH' else fvg.fvg_high:.5f} (R11)"
            )

        # R67: bullish — close below sweep extreme
        if sweep is not None and fvg.direction == "BULLISH":
            if candle.close < sweep.sweep_extreme:
                return True, (
                    f"Bullish setup invalidated: close {candle.close:.5f} "
                    f"< sweep low {sweep.sweep_extreme:.5f} (R67)"
                )

        # R68: bearish — close above sweep extreme
        if sweep is not None and fvg.direction == "BEARISH":
            if candle.close > sweep.sweep_extreme:
                return True, (
                    f"Bearish setup invalidated: close {candle.close:.5f} "
                    f"> sweep high {sweep.sweep_extreme:.5f} (R68)"
                )

        return False, ""


# ═══════════════════════════════════════════════════════════════════════════════
# Break-Even and ATR Trailing Stop Manager (R89–R96, spec v1.1)
# ═══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass as _dataclass_be  # noqa: F401 (duplicate — use top-level dataclass)


@dataclass
class StopUpdateResult:
    """
    Output of a break-even / trailing stop evaluation.

    new_sl is None when no update is needed.
    reason explains exactly why the decision was made (for decision log).
    """
    should_update: bool
    new_sl: float | None
    reason: str
    is_breakeven: bool = False    # True only when this is the initial BE move
    is_trailing: bool = False     # True when this is a trailing move


class BreakEvenTrailingManager:
    """
    Manages break-even and ATR trailing stop for an open position.

    Rules enforced:
      R89  — break-even triggers at breakeven_trigger_pct of distance to TP
      R90  — break-even moves SL to exact entry price
      R91  — broker verification required (handled by caller)
      R92  — trailing activates after break-even confirmed
      R93  — trail = best_close - trailing_atr_factor × ATR(14)
      R94  — evaluated on candle close only
      R95  — broker verification required (handled by caller)
      R96  — SL never moves against the position; TP unchanged
    """

    def __init__(
        self,
        breakeven_trigger_pct: float = 0.50,
        trailing_atr_factor: float = 1.0,
        atr_period: int = 14,
        tick_size: float = 0.01,
        trade_stops_level: int = 0,
        point: float = 0.01,
    ) -> None:
        if not (0.01 <= breakeven_trigger_pct <= 0.99):
            raise ValueError(
                f"breakeven_trigger_pct must be between 0.01 and 0.99, "
                f"got {breakeven_trigger_pct}"
            )
        if trailing_atr_factor <= 0:
            raise ValueError(
                f"trailing_atr_factor must be > 0, got {trailing_atr_factor}"
            )
        self.breakeven_trigger_pct = breakeven_trigger_pct
        self.trailing_atr_factor   = trailing_atr_factor
        self.atr_period            = atr_period
        self.tick_size             = tick_size
        self.trade_stops_level     = trade_stops_level
        self.point                 = point

    # ── Public API ─────────────────────────────────────────────────────────────

    def evaluate(
        self,
        direction: str,
        entry_price: float,
        original_sl: float,
        tp_price: float,
        current_sl: float,
        breakeven_fired: bool,
        best_close_since_entry: float | None,
        candles: list,          # list[Candle] — completed H1 candles
        close_price: float,     # latest completed H1 candle close (R94)
    ) -> StopUpdateResult:
        """
        Evaluate whether the stop should be updated on this candle close.

        Call once per completed H1 candle while the position is open.
        The caller is responsible for broker submission and verification (R91, R95).

        Args:
            direction:              "BULLISH" or "BEARISH"
            entry_price:            actual fill price
            original_sl:            SL at the time of entry (never changes)
            tp_price:               take-profit price (never changes)
            current_sl:             current active SL (may have been updated)
            breakeven_fired:        True if break-even has already been confirmed
            best_close_since_entry: best candle close seen since entry
                                    (highest for bull, lowest for bear); None if first candle
            candles:                completed H1 candles for ATR calculation
            close_price:            close of the most recently completed H1 candle

        Returns:
            StopUpdateResult — new_sl is None when no update needed
        """
        # ── Update best close (R93) ─────────────────────────────────────────
        if best_close_since_entry is None:
            best_close_since_entry = close_price
        else:
            if direction == "BULLISH":
                best_close_since_entry = max(best_close_since_entry, close_price)
            else:
                best_close_since_entry = min(best_close_since_entry, close_price)

        # ── Phase 1: check break-even trigger (R89) ─────────────────────────
        if not breakeven_fired:
            return self._check_breakeven(
                direction, entry_price, tp_price,
                current_sl, close_price, best_close_since_entry,
            )

        # ── Phase 2: trailing stop (R92, R93) ───────────────────────────────
        return self._check_trailing(
            direction, entry_price, current_sl,
            best_close_since_entry, candles,
        )

    # ── Internal ───────────────────────────────────────────────────────────────

    def _check_breakeven(
        self,
        direction: str,
        entry_price: float,
        tp_price: float,
        current_sl: float,
        close_price: float,
        best_close: float,
    ) -> StopUpdateResult:
        """R89: check whether price has reached the break-even trigger level."""
        if direction == "BULLISH":
            tp_distance = tp_price - entry_price
            if tp_distance <= 0:
                return StopUpdateResult(
                    False, None, "TP distance is zero or negative — skipping BE check"
                )
            progress = (best_close - entry_price) / tp_distance
            already_at_be = current_sl >= entry_price
        else:
            tp_distance = entry_price - tp_price
            if tp_distance <= 0:
                return StopUpdateResult(
                    False, None, "TP distance is zero or negative — skipping BE check"
                )
            progress = (entry_price - best_close) / tp_distance
            already_at_be = current_sl <= entry_price

        # R89: skip if SL already at or better than break-even
        if already_at_be:
            return StopUpdateResult(
                False, None,
                f"SL already at/beyond entry ({current_sl:.5f}) — "
                "break-even not needed (R89)"
            )

        if progress < self.breakeven_trigger_pct:
            return StopUpdateResult(
                False, None,
                f"Progress {progress:.3f} < trigger {self.breakeven_trigger_pct:.2f} "
                f"(R89) — no break-even yet"
            )

        # R90: move SL to exact entry price, rounded conservatively
        new_sl = self._round_to_tick(entry_price, direction, mode="breakeven")

        # R90: check broker minimum stop distance from current price
        if not self._passes_min_stop(new_sl, close_price, direction):
            return StopUpdateResult(
                False, None,
                f"Break-even triggered (progress={progress:.3f}) but "
                f"broker min stop distance not yet satisfied — deferring (R90)"
            )

        return StopUpdateResult(
            should_update=True,
            new_sl=new_sl,
            reason=(
                f"Break-even triggered: progress={progress:.3f} >= "
                f"{self.breakeven_trigger_pct:.2f}. "
                f"SL {current_sl:.5f} -> entry {new_sl:.5f} (R89/R90)"
            ),
            is_breakeven=True,
            is_trailing=False,
        )

    def _check_trailing(
        self,
        direction: str,
        entry_price: float,
        current_sl: float,
        best_close: float,
        candles: list,
    ) -> StopUpdateResult:
        """R93: compute ATR trailing stop and check if it improves the current SL."""
        atr_val = compute_atr(candles, self.atr_period)
        if atr_val is None:
            return StopUpdateResult(
                False, None,
                "ATR unavailable — trailing stop skipped this candle (R93)"
            )

        trail_distance = self.trailing_atr_factor * atr_val

        if direction == "BULLISH":
            candidate_sl = best_close - trail_distance
            # R96: never move SL backward (must be >= current_sl)
            if candidate_sl <= current_sl:
                return StopUpdateResult(
                    False, None,
                    f"Trailing SL candidate {candidate_sl:.5f} <= "
                    f"current SL {current_sl:.5f} — no move needed (R96)"
                )
        else:
            candidate_sl = best_close + trail_distance
            # R96: never move SL backward (must be <= current_sl)
            if candidate_sl >= current_sl:
                return StopUpdateResult(
                    False, None,
                    f"Trailing SL candidate {candidate_sl:.5f} >= "
                    f"current SL {current_sl:.5f} — no move needed (R96)"
                )

        # Round to valid tick increment
        new_sl = self._round_to_tick(candidate_sl, direction, mode="trailing")

        # Sanity: never move against position after break-even (R96)
        if direction == "BULLISH" and new_sl < entry_price:
            return StopUpdateResult(
                False, None,
                f"Trailing SL {new_sl:.5f} would be below entry {entry_price:.5f} "
                "— not allowed after break-even (R96)"
            )
        if direction == "BEARISH" and new_sl > entry_price:
            return StopUpdateResult(
                False, None,
                f"Trailing SL {new_sl:.5f} would be above entry {entry_price:.5f} "
                "— not allowed after break-even (R96)"
            )

        return StopUpdateResult(
            should_update=True,
            new_sl=new_sl,
            reason=(
                f"Trailing stop: best_close={best_close:.5f} "
                f"ATR={atr_val:.5f} factor={self.trailing_atr_factor} "
                f"trail_dist={trail_distance:.5f} "
                f"SL {current_sl:.5f} -> {new_sl:.5f} (R93/R94)"
            ),
            is_breakeven=False,
            is_trailing=True,
        )

    def _round_to_tick(
        self, price: float, direction: str, mode: str
    ) -> float:
        """Round price to nearest valid tick, conservatively (toward entry)."""
        import math as _math
        if self.tick_size <= 0:
            return round(price, 8)
        if mode == "breakeven":
            # For break-even the caller already passes the exact entry price;
            # just snap to the nearest tick
            steps = round(price / self.tick_size)
        elif direction == "BULLISH":
            # Trailing bull: floor (stop stays further from current price = safer)
            steps = _math.floor(price / self.tick_size)
        else:
            # Trailing bear: ceil
            steps = _math.ceil(price / self.tick_size)
        return round(steps * self.tick_size, 8)

    def _passes_min_stop(
        self, sl: float, current_price: float, direction: str
    ) -> bool:
        """R90: check broker minimum stop distance constraint."""
        min_dist = self.trade_stops_level * self.point
        if min_dist <= 0:
            return True
        dist = abs(current_price - sl)
        return dist >= min_dist

    # ── Utility: update best_close given a new candle ─────────────────────────

    @staticmethod
    def update_best_close(
        direction: str,
        previous_best: float | None,
        new_close: float,
    ) -> float:
        """Return the updated best-close value after a new H1 candle closes."""
        if previous_best is None:
            return new_close
        if direction == "BULLISH":
            return max(previous_best, new_close)
        return min(previous_best, new_close)
