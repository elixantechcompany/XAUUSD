"""
SQLAlchemy ORM models for setup state machine persistence.

Every state transition is written to SetupTransition for full auditability.
The Setup row is the source of truth for the current state.

State enum aligned with STRATEGY_SPEC.md v1.0 IMPL3.

MIGRATION NOTE (EQ-6): The old WAITING_FOR_GAP_EXIT state has been renamed to
GAP_EXITED to accurately reflect the condition ("price has exited the gap").
A new WAITING_FOR_GAP_EXIT state replaces it to represent the monitoring phase
before exit is confirmed. See STRATEGY_SPEC.md EQ-6 for migration options.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.utils.database import Base

# ── Spec version (kept here so models can reference it without circular imports)
SPEC_VERSION = "1.0"


# ── State enum (IMPL3 ✅) ─────────────────────────────────────────────────────

class SetupState(str, enum.Enum):
    """
    Valid states for a trading setup, in sequence order.

    Terminal states (no further transitions): CLOSED, EXPIRED, INVALIDATED, REJECTED.
    """
    FVG_DETECTED             = "FVG_DETECTED"             # stage 1
    SWEEP_CONFIRMED          = "SWEEP_CONFIRMED"           # stage 2
    WAITING_FOR_RETRACEMENT  = "WAITING_FOR_RETRACEMENT"  # stage 3
    REFERENCE_CANDLE_SAVED   = "REFERENCE_CANDLE_SAVED"   # stage 4 (tracking)
    WAITING_FOR_GAP_EXIT     = "WAITING_FOR_GAP_EXIT"     # stage 5 (ref frozen; awaiting exit)
    GAP_EXITED               = "GAP_EXITED"               # stage 6 (exit confirmed)
    WAITING_FOR_TRIGGER      = "WAITING_FOR_TRIGGER"      # stage 7
    SIGNAL_READY             = "SIGNAL_READY"             # stage 8
    RISK_CHECK               = "RISK_CHECK"               # stage 9
    ORDER_PENDING            = "ORDER_PENDING"            # stage 10
    POSITION_OPEN            = "POSITION_OPEN"            # stage 11

    # ── Part 3 Master Specification Lifecycle States ─────────────────────────
    DETECTED                 = "DETECTED"                 # initial detection (sweep)
    MARKET_CONFIRMATION      = "MARKET_CONFIRMATION"      # break of preceding candle
    FVG_IDENTIFIED           = "FVG_IDENTIFIED"           # FVG formed
    FVG_ENTERED              = "FVG_ENTERED"              # first candle entered FVG & locked
    WAITING_FOR_BREAKOUT     = "WAITING_FOR_BREAKOUT"     # awaiting breakout of entering candle
    ENTRY_CONFIRMED          = "ENTRY_CONFIRMED"          # breakout confirmed
    TRADE_EXECUTED           = "TRADE_EXECUTED"           # position executed
    # ── Terminal ──────────────────────────────────────────────────────────────
    CLOSED                   = "CLOSED"
    EXPIRED                  = "EXPIRED"
    INVALIDATED              = "INVALIDATED"
    REJECTED                 = "REJECTED"


class SetupDirection(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


# ── ORM models ────────────────────────────────────────────────────────────────

class Setup(Base):
    """
    One FVG-based trade setup, from detection through close/expiry.

    Every field that affects trading decisions is stored here for full
    auditability and restart recovery (R73).
    """
    __tablename__ = "setups"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    direction: Mapped[SetupDirection] = mapped_column(
        SAEnum(SetupDirection), nullable=False
    )
    state: Mapped[SetupState] = mapped_column(
        SAEnum(SetupState), nullable=False, default=SetupState.FVG_DETECTED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # ── FVG fields (R10) ─────────────────────────────────────────────────────
    fvg_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    fvg_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    fvg_open_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fvg_c1_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fvg_c3_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fvg_atr_at_detection: Mapped[float | None] = mapped_column(Float)
    # Individual candle values needed for invalidation checks (R11, R66–R68)
    fvg_c1_high: Mapped[float | None] = mapped_column(Float)
    fvg_c1_low: Mapped[float | None] = mapped_column(Float)
    fvg_c3_high: Mapped[float | None] = mapped_column(Float)
    fvg_c3_low: Mapped[float | None] = mapped_column(Float)

    # ── Sweep fields (R18) ───────────────────────────────────────────────────
    sweep_level: Mapped[float | None] = mapped_column(Float)
    sweep_candle_time: Mapped[datetime | None] = mapped_column(DateTime)
    sweep_extreme: Mapped[float | None] = mapped_column(Float)

    # ── Market Confirmation fields (Part 3.D) ────────────────────────────────
    market_confirmation_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    market_confirmation_candle_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_confirmation_preceding_extreme: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Reference / Entering candle — FROZEN once gap entered (Part 3.E) ─────
    ref_candle_time: Mapped[datetime | None] = mapped_column(DateTime)
    ref_candle_open: Mapped[float | None] = mapped_column(Float)
    ref_candle_high: Mapped[float | None] = mapped_column(Float)
    ref_candle_low: Mapped[float | None] = mapped_column(Float)
    ref_candle_close: Mapped[float | None] = mapped_column(Float)
    ref_candle_frozen: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Trigger level (ref_high for bull, ref_low for bear) (R27, R28) ───────
    trigger_level: Mapped[float | None] = mapped_column(Float)
    trigger_fired_at: Mapped[datetime | None] = mapped_column(DateTime)

    # ── Proposed trade parameters ─────────────────────────────────────────────
    proposed_entry: Mapped[float | None] = mapped_column(Float)
    proposed_sl: Mapped[float | None] = mapped_column(Float)
    proposed_tp: Mapped[float | None] = mapped_column(Float)
    proposed_volume: Mapped[float | None] = mapped_column(Float)
    estimated_risk_usd: Mapped[float | None] = mapped_column(Float)
    estimated_rr: Mapped[float | None] = mapped_column(Float)

    # ── Rejection / expiry reason ─────────────────────────────────────────────
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # ── Spec traceability (IMPL2) ─────────────────────────────────────────────
    spec_version: Mapped[str] = mapped_column(String(16), default="1.0")
    spec_hash: Mapped[str | None] = mapped_column(String(64))

    # ── Relationships ─────────────────────────────────────────────────────────
    transitions: Mapped[list["SetupTransition"]] = relationship(
        "SetupTransition", back_populates="setup",
        order_by="SetupTransition.timestamp"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="setup"
    )


class SetupTransition(Base):
    """
    Immutable audit log of every state transition for a Setup.
    Written before any order is submitted (IMPL2).
    """
    __tablename__ = "setup_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    setup_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("setups.id"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    old_state: Mapped[SetupState | None] = mapped_column(SAEnum(SetupState))
    new_state: Mapped[SetupState] = mapped_column(SAEnum(SetupState), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)

    # ── Spec traceability (IMPL2) ─────────────────────────────────────────────
    spec_version: Mapped[str] = mapped_column(String(16), default="1.0")
    spec_hash: Mapped[str | None] = mapped_column(String(64))

    setup: Mapped["Setup"] = relationship("Setup", back_populates="transitions")


class Order(Base):
    """An order submitted (or simulated) for a setup."""
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    setup_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("setups.id"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(10), nullable=False)

    # ── Request ───────────────────────────────────────────────────────────────
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    requested_volume: Mapped[float] = mapped_column(Float, nullable=False)
    requested_entry: Mapped[float] = mapped_column(Float, nullable=False)
    requested_sl: Mapped[float] = mapped_column(Float, nullable=False)
    requested_tp: Mapped[float] = mapped_column(Float, nullable=False)
    client_order_id: Mapped[str | None] = mapped_column(String(32))   # IMPL4 idempotency

    # ── Fill ──────────────────────────────────────────────────────────────────
    filled_at: Mapped[datetime | None] = mapped_column(DateTime)
    filled_price: Mapped[float | None] = mapped_column(Float)
    filled_volume: Mapped[float | None] = mapped_column(Float)
    broker_ticket: Mapped[int | None] = mapped_column(Integer)
    is_paper: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Stop confirmation (R39) ───────────────────────────────────────────────
    sl_confirmed_by_broker: Mapped[bool] = mapped_column(Boolean, default=False)
    sl_broker_ticket: Mapped[int | None] = mapped_column(Integer)
    sl_retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Outcome ───────────────────────────────────────────────────────────────
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)
    close_price: Mapped[float | None] = mapped_column(Float)
    realized_pnl: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    # ── Spec traceability (IMPL2) ─────────────────────────────────────────────
    spec_version: Mapped[str] = mapped_column(String(16), default="1.0")
    spec_hash: Mapped[str | None] = mapped_column(String(64))

    setup: Mapped["Setup"] = relationship("Setup", back_populates="orders")


class DecisionLog(Base):
    """
    Per-evaluation decision record (IMPL2).

    Written before any order submission. Immutable after creation.
    """
    __tablename__ = "decision_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # ── Traceability (IMPL2) ─────────────────────────────────────────────────
    spec_version: Mapped[str] = mapped_column(String(16), nullable=False)
    spec_hash: Mapped[str | None] = mapped_column(String(64))
    git_commit: Mapped[str | None] = mapped_column(String(40))

    # ── Context ───────────────────────────────────────────────────────────────
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    setup_id: Mapped[str | None] = mapped_column(String(32), index=True)
    prev_state: Mapped[str | None] = mapped_column(String(32))
    new_state: Mapped[str | None] = mapped_column(String(32))

    # ── Decision (stored as JSON text) ────────────────────────────────────────
    rules_evaluated: Mapped[str | None] = mapped_column(Text)   # JSON list of rule IDs
    rule_results: Mapped[str | None] = mapped_column(Text)      # JSON list of results
    final_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text)

    # ── Market context ────────────────────────────────────────────────────────
    spread_at_decision: Mapped[float | None] = mapped_column(Float)
    quote_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    equity_at_decision: Mapped[float | None] = mapped_column(Float)
