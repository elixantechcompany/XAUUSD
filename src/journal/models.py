"""
Trade journal and daily-risk-limit persistence models.
"""
from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.utils.database import Base


class JournalEntry(Base):
    """Every notable event: fill, rejection, manual trade, modification, close."""
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # event_type values: SIGNAL, ORDER_SENT, FILL, MODIFICATION, CLOSE,
    #   MANUAL_TRADE, REJECTION, RISK_LOCK, NEWS_LOCK, RESTART, etc.

    setup_id: Mapped[str | None] = mapped_column(String(32), index=True)
    order_id: Mapped[str | None] = mapped_column(String(32))
    symbol: Mapped[str | None] = mapped_column(String(20))
    direction: Mapped[str | None] = mapped_column(String(8))
    execution_mode: Mapped[str | None] = mapped_column(String(10))
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    price: Mapped[float | None] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float)
    sl: Mapped[float | None] = mapped_column(Float)
    tp: Mapped[float | None] = mapped_column(Float)
    pnl: Mapped[float | None] = mapped_column(Float)

    notes: Mapped[str | None] = mapped_column(Text)


class DailyRiskState(Base):
    """
    Persisted per-account per-day risk counters.
    Survives application restarts so daily limits cannot be gamed by restarting.
    """
    __tablename__ = "daily_risk_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    account_label: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    # Start-of-day equity snapshot (captured once per day on first connection)
    start_equity: Mapped[float | None] = mapped_column(Float)

    # Running counters
    new_entries_today: Mapped[int] = mapped_column(Integer, default=0)
    realized_pnl_today: Mapped[float] = mapped_column(Float, default=0.0)

    # Risk locks (latched — cleared only by explicit operator action)
    daily_loss_lock: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_trade_lock: Mapped[bool] = mapped_column(Boolean, default=False)
    news_lock: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_loss_lock: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
