"""
Shared pytest fixtures — all test suites.

Provides:
  - in-memory SQLite session isolated per test (no listener leaks)
  - candle factory helpers
  - symbol info stubs
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.data.candle import Candle
from src.data.market_data_adapter import SymbolInfo
from src.utils.database import Base

# Register all ORM models so Base.metadata knows about every table
import src.state.models    # noqa: F401
import src.journal.models  # noqa: F401
import src.api.models      # noqa: F401


# ── Time helpers ──────────────────────────────────────────────────────────────

BASE_TIME = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)


def t(hours: int) -> datetime:
    """Return BASE_TIME + hours."""
    return BASE_TIME + timedelta(hours=hours)


# ── In-memory database ────────────────────────────────────────────────────────

@pytest.fixture
def db() -> Session:
    """
    Fully isolated in-memory SQLite session, created fresh for each test.
    Uses a brand-new engine per fixture call so SA event listeners never
    accumulate across tests (B10 fix).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Enable FK constraints via a post-connect hook on the raw DBAPI level
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))

    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autocommit=False,
                           autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Candle factory ────────────────────────────────────────────────────────────

def make_candle(
    hour: int,
    lo: float,
    hi: float,
    o: float | None = None,
    c: float | None = None,
    symbol: str = "XAUUSD",
    timeframe: str = "H1",
) -> Candle:
    if o is None:
        o = (lo + hi) / 2
    if c is None:
        c = (lo + hi) / 2
    return Candle(
        time=t(hour), open=o, high=hi, low=lo, close=c,
        volume=100.0, symbol=symbol, timeframe=timeframe,
    )


def flat_candles(
    n: int,
    start_hour: int = 0,
    lo: float = 2000.0,
    hi: float = 2004.0,
    symbol: str = "XAUUSD",
) -> list[Candle]:
    """n candles with identical range — predictable ATR = hi - lo = 4.0."""
    return [make_candle(start_hour + i, lo, hi, symbol=symbol) for i in range(n)]


@pytest.fixture
def xauusd_candles_20() -> list[Candle]:
    """20 flat H1 XAUUSD candles — enough for ATR(14)."""
    return flat_candles(20, lo=2000.0, hi=2004.0)


@pytest.fixture
def xauusd_candles_50() -> list[Candle]:
    """50 flat H1 XAUUSD candles."""
    return flat_candles(50, lo=2000.0, hi=2004.0)


# ── Symbol info stubs ─────────────────────────────────────────────────────────

def make_xauusd_info() -> SymbolInfo:
    """Realistic XAUUSD symbol spec for unit tests (not live broker values)."""
    return SymbolInfo(
        name="XAUUSD",
        digits=2,
        point=0.01,
        tick_size=0.01,
        tick_value=1.0,
        contract_size=100.0,
        volume_min=0.01,
        volume_max=500.0,
        volume_step=0.01,
        trade_stops_level=0,
        spread=20,
        currency_profit="USD",
        currency_margin="USD",
    )


def make_btcusd_info() -> SymbolInfo:
    """Realistic BTCUSD symbol spec for unit tests (not live broker values)."""
    return SymbolInfo(
        name="BTCUSD",
        digits=2,
        point=0.01,
        tick_size=0.01,
        tick_value=0.01,
        contract_size=1.0,
        volume_min=0.01,
        volume_max=10.0,
        volume_step=0.01,
        trade_stops_level=0,
        spread=5000,
        currency_profit="USD",
        currency_margin="USD",
    )


@pytest.fixture
def xauusd_info() -> SymbolInfo:
    return make_xauusd_info()


@pytest.fixture
def btcusd_info() -> SymbolInfo:
    return make_btcusd_info()
