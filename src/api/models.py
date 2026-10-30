"""
Account profile and API user models.
Passwords are never stored here — they live in Windows Credential Manager.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.utils.database import Base


class AccountProfile(Base):
    """Named MT5 account profile (no passwords stored)."""
    __tablename__ = "account_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    broker_server: Mapped[str] = mapped_column(String(128), nullable=False)
    mt5_terminal_path: Mapped[str | None] = mapped_column(Text)
    # Login number as string to avoid precision issues
    expected_login: Mapped[str | None] = mapped_column(String(32))
    permitted_symbols: Mapped[str] = mapped_column(Text, default="XAUUSD,BTCUSD")
    execution_mode: Mapped[str] = mapped_column(String(10), default="paper")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class APIUser(Base):
    """Local API user for the mobile web interface."""
    __tablename__ = "api_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
