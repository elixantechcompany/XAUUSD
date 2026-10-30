"""
Reusable candle sequence builders for tests.

These build realistic but fully synthetic candle sequences that produce
known FVGs, swings, sweeps, and reference candles — so test assertions
can be written against known ground truth.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from src.data.candle import Candle

BASE = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def _t(h: int) -> datetime:
    return BASE + timedelta(hours=h)


def _c(
    h: int, lo: float, hi: float,
    o: float | None = None, c: float | None = None,
    symbol: str = "XAUUSD",
) -> Candle:
    if o is None:
        o = (lo + hi) / 2
    if c is None:
        c = (lo + hi) / 2
    return Candle(
        time=_t(h), open=o, high=hi, low=lo, close=c,
        volume=100.0, symbol=symbol, timeframe="H1",
    )


def bullish_setup_sequence() -> list[Candle]:
    """
    A complete synthetic candle sequence producing one clear bullish setup:

    Hours 0–13:   14 baseline candles (range 2000–2004) — ATR window
    Hours 14–16:  Bullish FVG:
                    C1(14) high=2010, C2(15) impulse up, C3(16) low=2016 → gap [2010,2016]
    Hours 17–20:  Swing low formation around 2005 (pivot at 18, confirmed at 20)
    Hour  21:     Bullish sweep candle — wick below 2005, close above 2005
    Hours 22–23:  Retracement into FVG — candle at 22 intersects [2010,2016]
    Hour  24:     Gap exit — candle closes above fvg_high=2016
    Hour  25:     Trigger break — candle closes above reference candle high

    Returns the full list of completed candles (live bar already excluded).
    """
    candles: list[Candle] = []

    # Baseline ATR window
    for i in range(14):
        candles.append(_c(i, lo=2000.0, hi=2004.0))

    # Bullish FVG: C1.high=2010 < C3.low=2016
    c1 = _c(14, lo=2005.0, hi=2010.0)          # C1 high = 2010
    c2 = _c(15, lo=2010.0, hi=2020.0,
            o=2011.0, c=2019.0)                 # impulse up
    c3 = _c(16, lo=2016.0, hi=2024.0,
            o=2017.0, c=2022.0)                 # C3 low = 2016 → gap [2010, 2016]
    candles += [c1, c2, c3]

    # Swing low formation: pivot at hour 18, lows at 17,19,20 are higher
    candles.append(_c(17, lo=2008.0, hi=2014.0))   # left bar 2
    candles.append(_c(18, lo=2003.0, hi=2010.0))   # pivot low = 2003
    candles.append(_c(19, lo=2007.0, hi=2013.0))   # right bar 1
    candles.append(_c(20, lo=2008.0, hi=2014.0))   # right bar 2 — swing confirmed

    # Bullish sweep: wick below 2003, close above 2003
    candles.append(_c(21, lo=2001.0, hi=2012.0,
                      o=2009.0, c=2008.0))          # sweep — low=2001 < 2003, close=2008 > 2003

    # Retracement into FVG [2010, 2016]
    candles.append(_c(22, lo=2011.0, hi=2016.0,
                      o=2015.0, c=2012.0))          # reference candle: low=2011 ≤ fvg_high=2016

    # Gap exit: candle closes above fvg_high=2016
    candles.append(_c(23, lo=2014.0, hi=2020.0,
                      o=2015.0, c=2018.0))          # close=2018 > 2016 → gap exited

    # Trigger break: candle closes above reference candle high (2016)
    candles.append(_c(25, lo=2017.0, hi=2023.0,
                      o=2018.0, c=2022.0))          # close=2022 > trigger=2016

    return candles


def bearish_setup_sequence() -> list[Candle]:
    """
    A complete synthetic candle sequence producing one clear bearish setup.

    Hours 0–13:   14 baseline candles (range 2050–2054) — ATR window
    Hours 14–16:  Bearish FVG: C1.low=2060 > C3.high=2054 → gap [2054, 2060]
    Hours 17–20:  Swing high at hour 18 = 2065, confirmed at 20
    Hour  21:     Bearish sweep: wick above 2065, close below 2065
    Hours 22–23:  Retracement into FVG — candle at 22 intersects [2054,2060]
    Hour  24:     Gap exit — candle closes below fvg_low=2054
    Hour  25:     Trigger break — candle closes below reference candle low
    """
    candles: list[Candle] = []

    for i in range(14):
        candles.append(_c(i, lo=2050.0, hi=2054.0))

    c1 = _c(14, lo=2060.0, hi=2066.0, o=2065.0, c=2061.0)  # C1 low = 2060
    c2 = _c(15, lo=2052.0, hi=2060.0, o=2059.0, c=2053.0)  # impulse down
    c3 = _c(16, lo=2046.0, hi=2054.0, o=2053.0, c=2048.0)  # C3 high = 2054 → gap [2054,2060]
    candles += [c1, c2, c3]

    candles.append(_c(17, lo=2055.0, hi=2062.0))   # left bar 2
    candles.append(_c(18, lo=2058.0, hi=2065.0))   # pivot high = 2065
    candles.append(_c(19, lo=2055.0, hi=2062.0))   # right bar 1
    candles.append(_c(20, lo=2055.0, hi=2061.0))   # right bar 2 — confirmed

    # Bearish sweep: wick above 2065, close below 2065
    candles.append(_c(21, lo=2058.0, hi=2068.0,
                      o=2062.0, c=2061.0))

    # Retracement into FVG [2054, 2060]
    candles.append(_c(22, lo=2054.0, hi=2059.0,
                      o=2055.0, c=2058.0))          # reference: high=2059 ≥ fvg_low=2054

    # Gap exit: candle closes below fvg_low=2054
    candles.append(_c(23, lo=2050.0, hi=2057.0,
                      o=2056.0, c=2052.0))          # close=2052 < 2054

    # Trigger break: candle closes below reference candle low (2054)
    candles.append(_c(25, lo=2048.0, hi=2055.0,
                      o=2054.0, c=2050.0))

    return candles
