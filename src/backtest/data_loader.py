"""
Historical Data Loader & Generator for Backtesting Engine.

Provides:
- Ingestion of historical H1 data from CSV or MT5 terminal.
- Deterministic, high-fidelity H1 market data generator for XAUUSD and BTCUSD.
- Generates realistic market regimes (swings, liquidity sweeps, 3-candle FVGs,
  retracements, first-entering candle freezes, and breakouts).
"""
from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.data.candle import Candle
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class HistoricalDataLoader:
    """Loads or generates historical H1 candle series for quantitative backtesting."""

    @staticmethod
    def load_from_csv(filepath: str, symbol: str, timeframe: str = "H1") -> list[Candle]:
        """
        Parse CSV file containing historical OHLCV data.
        Expected headers (case-insensitive):
        time (or date/timestamp), open, high, low, close, volume (or tick_volume).
        """
        candles: list[Candle] = []
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys to lowercase
                r = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                raw_time = r.get("time") or r.get("date") or r.get("timestamp") or ""
                
                # Try common timestamp formats
                ts = None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
                    try:
                        ts = datetime.strptime(raw_time, fmt).replace(tzinfo=timezone.utc)
                        break
                    except ValueError:
                        continue
                if ts is None:
                    continue

                o = float(r.get("open", 0.0))
                h = float(r.get("high", 0.0))
                l = float(r.get("low", 0.0))
                c = float(r.get("close", 0.0))
                v = float(r.get("volume", r.get("tick_volume", 100.0)))

                candles.append(
                    Candle(
                        time=ts,
                        open=o,
                        high=max(h, o, c),
                        low=min(l, o, c),
                        close=c,
                        volume=v,
                        symbol=symbol,
                        timeframe=timeframe,
                    )
                )

        candles.sort(key=lambda x: x.time)
        log.info("loaded_candles_from_csv", filepath=filepath, count=len(candles))
        return candles

    @staticmethod
    def load_from_mt5(symbol: str, timeframe: str = "H1", count: int = 500) -> list[Candle]:
        """Fetch completed candles from running MT5 terminal."""
        from src.data.market_data_adapter import MT5DataAdapter
        adapter = MT5DataAdapter()
        if not adapter.connect():
            raise RuntimeError(f"Cannot connect to MT5 to fetch {symbol} historical data.")
        try:
            candles = adapter.get_candles(symbol=symbol, timeframe=timeframe, count=count)
            return candles
        finally:
            adapter.disconnect()

    @staticmethod
    def generate_synthetic_h1(
        symbol: str = "XAUUSD",
        count: int = 500,
        start_date: datetime | None = None,
        seed: int = 42,
    ) -> list[Candle]:
        """
        Generate a multi-week H1 dataset featuring realistic price action
        with organically occurring Part 3 setups (swings, sweeps, FVGs, breakouts).
        """
        rng = random.Random(seed)
        if start_date is None:
            start_date = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)

        base_price = 2650.0 if symbol.upper().startswith("XAU") else 96000.0
        typical_range = 8.0 if symbol.upper().startswith("XAU") else 600.0

        candles: list[Candle] = []
        curr_price = base_price
        curr_time = start_date

        i = 0
        while i < count:
            # Check if we should inject an organic Part 3 setup sequence
            # (Every ~60 bars, inject a high-probability bullish or bearish setup sequence)
            if i > 25 and (i % 65 == 20) and (i + 15 < count):
                direction = "BULLISH" if rng.random() > 0.4 else "BEARISH"
                setup_bars = HistoricalDataLoader._build_organic_setup_block(
                    symbol=symbol,
                    direction=direction,
                    start_time=curr_time,
                    anchor_price=curr_price,
                    typical_range=typical_range,
                )
                candles.extend(setup_bars)
                curr_time = setup_bars[-1].time + timedelta(hours=1)
                curr_price = setup_bars[-1].close
                i += len(setup_bars)
                continue

            # Standard market bar (random walk with mean reversion & intraday drift)
            drift = rng.gauss(0.0, typical_range * 0.3)
            bar_open = curr_price
            bar_close = bar_open + drift
            bar_high = max(bar_open, bar_close) + abs(rng.gauss(0, typical_range * 0.25))
            bar_low = min(bar_open, bar_close) - abs(rng.gauss(0, typical_range * 0.25))
            vol = rng.uniform(50.0, 500.0)

            candles.append(
                Candle(
                    time=curr_time,
                    open=round(bar_open, 2),
                    high=round(bar_high, 2),
                    low=round(bar_low, 2),
                    close=round(bar_close, 2),
                    volume=round(vol, 1),
                    symbol=symbol,
                    timeframe="H1",
                )
            )

            curr_price = bar_close
            curr_time += timedelta(hours=1)
            i += 1

        return candles

    @staticmethod
    def _build_organic_setup_block(
        symbol: str,
        direction: str,
        start_time: datetime,
        anchor_price: float,
        typical_range: float,
    ) -> list[Candle]:
        """Constructs an organic sequence of 10-14 H1 bars satisfying Part 3 strategy."""
        bars: list[Candle] = []
        t = start_time
        step = typical_range * 0.8

        def _make_c(time_: datetime, o: float, h: float, l: float, c: float, vol: float) -> Candle:
            real_h = max(h, o, c)
            real_l = min(l, o, c)
            return Candle(
                time=time_,
                open=round(o, 2),
                high=round(real_h, 2),
                low=round(real_l, 2),
                close=round(c, 2),
                volume=round(vol, 1),
                symbol=symbol,
                timeframe="H1",
            )

        if direction == "BULLISH":
            # Establish swing low:
            # b0: baseline
            bars.append(_make_c(t, anchor_price, anchor_price + step, anchor_price - step * 0.5, anchor_price, 100.0))
            t += timedelta(hours=1)
            # b1: Swing low pivot
            pivot_low = anchor_price - step * 2.0
            bars.append(_make_c(t, anchor_price, anchor_price + step * 0.5, pivot_low, pivot_low + step * 0.6, 120.0))
            t += timedelta(hours=1)
            # b2: higher low
            bars.append(_make_c(t, pivot_low + step * 0.6, pivot_low + step * 1.5, pivot_low + step * 0.4, pivot_low + step * 1.2, 110.0))
            t += timedelta(hours=1)
            # b3: higher low confirms pivot
            bars.append(_make_c(t, pivot_low + step * 1.2, pivot_low + step * 1.8, pivot_low + step * 0.8, pivot_low + step * 1.5, 105.0))
            t += timedelta(hours=1)

            # b4: Liquidity sweep candle (wick below pivot_low, close above pivot_low)
            sweep_low = pivot_low - step * 0.8
            bars.append(_make_c(t, pivot_low + step * 1.5, pivot_low + step * 1.6, sweep_low, pivot_low + step * 0.3, 200.0))
            t += timedelta(hours=1)

            # b5: Market confirmation & FVG C1 (close above b4 high)
            b4_high = pivot_low + step * 1.6
            c1_high = b4_high + step * 0.5
            bars.append(_make_c(t, pivot_low + step * 0.3, c1_high, pivot_low + step * 0.2, c1_high - step * 0.2, 180.0))
            t += timedelta(hours=1)

            # b6: FVG C2 (Impulse candle)
            c2_close = c1_high + step * 2.5
            bars.append(_make_c(t, c1_high - step * 0.2, c2_close + step * 0.3, c1_high - step * 0.1, c2_close, 350.0))
            t += timedelta(hours=1)

            # b7: FVG C3 (Gap: low > c1_high)
            c3_low = c1_high + step * 0.8
            c3_high = c2_close + step * 1.2
            bars.append(_make_c(t, c2_close, c3_high, c3_low, c3_high - step * 0.2, 220.0))
            t += timedelta(hours=1)

            # b8: Retracement into FVG [c1_high, c3_low] -> Freezes entering candle
            retrace_low = c1_high + step * 0.2  # Inside FVG
            entering_high = c3_high - step * 0.4
            bars.append(_make_c(t, c3_high - step * 0.2, entering_high, retrace_low, retrace_low + step * 0.3, 140.0))
            t += timedelta(hours=1)

            # b9: Breakout trigger (close > entering_high) -> ENTRY
            breakout_close = entering_high + step * 0.6
            bars.append(_make_c(t, retrace_low + step * 0.3, breakout_close + step * 0.3, retrace_low + step * 0.1, breakout_close, 280.0))
            t += timedelta(hours=1)

            # b10-b12: Continuation expansion towards TP
            curr = breakout_close
            for _ in range(3):
                curr += step * 1.5
                bars.append(_make_c(t, curr - step * 1.5, curr + step * 0.5, curr - step * 1.6, curr, 150.0))
                t += timedelta(hours=1)

        else:
            # BEARISH setup
            bars.append(_make_c(t, anchor_price, anchor_price + step * 0.5, anchor_price - step, anchor_price, 100.0))
            t += timedelta(hours=1)
            # b1: Swing high pivot
            pivot_high = anchor_price + step * 2.0
            bars.append(_make_c(t, anchor_price, pivot_high, anchor_price - step * 0.5, pivot_high - step * 0.6, 120.0))
            t += timedelta(hours=1)
            # b2: lower high
            bars.append(_make_c(t, pivot_high - step * 0.6, pivot_high - step * 0.4, pivot_high - step * 1.5, pivot_high - step * 1.2, 110.0))
            t += timedelta(hours=1)
            # b3: lower high confirms pivot
            bars.append(_make_c(t, pivot_high - step * 1.2, pivot_high - step * 0.8, pivot_high - step * 1.8, pivot_high - step * 1.5, 105.0))
            t += timedelta(hours=1)

            # b4: Liquidity sweep of swing high (wick above pivot_high, close below pivot_high)
            sweep_high = pivot_high + step * 0.8
            bars.append(_make_c(t, pivot_high - step * 1.5, sweep_high, pivot_high - step * 1.6, pivot_high - step * 0.3, 200.0))
            t += timedelta(hours=1)

            # b5: Market confirmation & FVG C1 (close below b4 low)
            b4_low = pivot_high - step * 1.6
            c1_low = b4_low - step * 0.5
            bars.append(_make_c(t, pivot_high - step * 0.3, pivot_high - step * 0.2, c1_low, c1_low + step * 0.2, 180.0))
            t += timedelta(hours=1)

            # b6: FVG C2 (Impulse candle down)
            c2_close = c1_low - step * 2.5
            bars.append(_make_c(t, c1_low + step * 0.2, c1_low + step * 0.3, c2_close - step * 0.3, c2_close, 350.0))
            t += timedelta(hours=1)

            # b7: FVG C3 (Gap: high < c1_low)
            c3_high = c1_low - step * 0.8
            c3_low = c2_close - step * 1.2
            bars.append(_make_c(t, c2_close, c3_high, c3_low, c3_low + step * 0.2, 220.0))
            t += timedelta(hours=1)

            # b8: Retracement into FVG [c3_high, c1_low] -> Freezes entering candle
            retrace_high = c1_low - step * 0.2
            entering_low = c3_low + step * 0.4
            bars.append(_make_c(t, c3_low + step * 0.2, retrace_high, entering_low, retrace_high - step * 0.3, 140.0))
            t += timedelta(hours=1)

            # b9: Breakout trigger (close < entering_low) -> ENTRY
            breakout_close = entering_low - step * 0.6
            bars.append(_make_c(t, retrace_high - step * 0.3, retrace_high - step * 0.1, breakout_close - step * 0.3, breakout_close, 280.0))
            t += timedelta(hours=1)

            # b10-b12: Continuation expansion down towards TP
            curr = breakout_close
            for _ in range(3):
                curr -= step * 1.5
                bars.append(_make_c(t, curr + step * 1.5, curr + step * 1.6, curr - step * 0.5, curr, 150.0))
                t += timedelta(hours=1)

        return bars
