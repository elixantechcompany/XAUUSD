"""
Supabase Publisher — bridges the Python engine to the Next.js dashboard.

Writes to Supabase (Postgres + Realtime) so the web app has live data.
Also polls the `commands` table for instructions from the dashboard.

Tables written:
  heartbeats          — every 10 seconds
  accounts_snapshot   — on every equity change
  signals             — when a setup reaches SIGNAL_READY or terminal state
  evaluations         — every engine evaluation cycle
  trades              — on fill and close
  commands            — polled; acknowledgements written back
  logs                — errors and important events

Security:
  - Uses SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from environment only
  - Never logs credentials
  - Service role key stays on the VPS / local machine only
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from src.utils.logging_config import get_logger

log = get_logger(__name__)

_client = None


def _get_client():
    """Lazy-init the Supabase client. Raises if env vars are not set."""
    global _client
    if _client is not None:
        return _client
    try:
        from supabase import create_client, Client
    except ImportError:
        raise RuntimeError(
            "supabase-py not installed. "
            "Run: pip install supabase==2.4.2"
        )
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
            "as environment variables. Never hardcode them."
        )
    _client = create_client(url, key)
    return _client


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ── Heartbeat ─────────────────────────────────────────────────────────────────

def publish_heartbeat(
    mt5_connected: bool,
    last_tick_ts: datetime | None,
    equity: float | None,
    balance: float | None,
    execution_mode: str,
) -> None:
    """
    Write a heartbeat row every 10 seconds.
    Dashboard uses this to determine ONLINE / STALE / OFFLINE status.
    """
    try:
        client = _get_client()
        client.table("heartbeats").insert({
            "ts": _now(),
            "mt5_connected": mt5_connected,
            "last_tick_ts": last_tick_ts.isoformat() if last_tick_ts else None,
            "equity": equity,
            "balance": balance,
            "execution_mode": execution_mode,
            "live_trading_enabled": False,
        }).execute()
    except Exception as exc:
        log.error("supabase_heartbeat_failed", exc=str(exc))


# ── Account snapshot ──────────────────────────────────────────────────────────

def publish_account_snapshot(
    equity: float,
    balance: float,
    daily_pnl: float,
    drawdown_pct: float,
    open_positions_count: int,
    execution_mode: str,
) -> None:
    try:
        client = _get_client()
        client.table("accounts_snapshot").insert({
            "ts": _now(),
            "equity": equity,
            "balance": balance,
            "daily_pnl": daily_pnl,
            "drawdown_pct": drawdown_pct,
            "open_positions_count": open_positions_count,
            "execution_mode": execution_mode,
        }).execute()
    except Exception as exc:
        log.error("supabase_account_snapshot_failed", exc=str(exc))


# ── Signal ────────────────────────────────────────────────────────────────────

def publish_signal(
    setup_id: str,
    symbol: str,
    timeframe: str,
    direction: str,
    state: str,
    fvg_low: float,
    fvg_high: float,
    sweep_level: float | None,
    sweep_extreme: float | None,
    ref_candle_high: float | None,
    ref_candle_low: float | None,
    trigger_level: float | None,
    proposed_entry: float | None,
    proposed_sl: float | None,
    proposed_tp: float | None,
    proposed_volume: float | None,
    estimated_risk_usd: float | None,
    estimated_rr: float | None,
    rejection_reason: str | None,
    spec_version: str,
    created_at: datetime,
    updated_at: datetime,
    session: str | None = None,
    quality_grade: str | None = None,
) -> None:
    """Upsert a signal row. Called whenever setup state changes."""
    try:
        client = _get_client()
        client.table("signals").upsert({
            "id": setup_id,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
            "instrument": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "state": state,
            "fvg_low": fvg_low,
            "fvg_high": fvg_high,
            "sweep_level": sweep_level,
            "sweep_extreme": sweep_extreme,
            "trigger_level": trigger_level,
            "ref_candle_high": ref_candle_high,
            "ref_candle_low": ref_candle_low,
            "entry": proposed_entry,
            "stop_loss": proposed_sl,
            "take_profit": proposed_tp,
            "suggested_lot_size": proposed_volume,
            "estimated_risk_usd": estimated_risk_usd,
            "rr_ratio": estimated_rr,
            "rejection_reason": rejection_reason,
            "session": session,
            "quality_grade": quality_grade,
            "strategy_version": spec_version,
            "status": _state_to_status(state),
        }, on_conflict="id").execute()
    except Exception as exc:
        log.error("supabase_signal_failed", setup_id=setup_id, exc=str(exc))


def _state_to_status(state: str) -> str:
    """Map engine state to signal status for the dashboard."""
    mapping = {
        "SIGNAL_READY": "new",
        "ORDER_PENDING": "taken",
        "POSITION_OPEN": "taken",
        "CLOSED": "hit_tp_or_sl",
        "EXPIRED": "expired",
        "INVALIDATED": "cancelled",
        "REJECTED": "skipped",
    }
    return mapping.get(state, "new")


# ── Evaluation log ────────────────────────────────────────────────────────────

def publish_evaluation(
    symbol: str,
    timeframe: str,
    decision: str,
    reason_codes: list[str],
    indicators: dict[str, Any],
    session: str | None = None,
) -> None:
    """Log every evaluation — including no-trade decisions."""
    try:
        client = _get_client()
        client.table("evaluations").insert({
            "ts": _now(),
            "instrument": symbol,
            "timeframe": timeframe,
            "decision": decision,
            "reason_codes": reason_codes,
            "indicators_json": json.dumps(indicators),
            "session": session,
        }).execute()
    except Exception as exc:
        log.error("supabase_evaluation_failed", exc=str(exc))


# ── Trade ─────────────────────────────────────────────────────────────────────

def publish_trade(
    ticket: str,
    signal_id: str,
    source: str,
    symbol: str,
    side: str,
    lots: float,
    open_time: datetime,
    open_price: float,
    sl: float,
    tp: float,
    execution_mode: str,
    close_time: datetime | None = None,
    close_price: float | None = None,
    pnl: float | None = None,
    r_multiple: float | None = None,
) -> None:
    try:
        client = _get_client()
        client.table("trades").upsert({
            "ticket": ticket,
            "signal_id": signal_id,
            "source": source,
            "instrument": symbol,
            "side": side,
            "lots": lots,
            "open_time": open_time.isoformat(),
            "open_price": open_price,
            "sl": sl,
            "tp": tp,
            "execution_mode": execution_mode,
            "close_time": close_time.isoformat() if close_time else None,
            "close_price": close_price,
            "pnl": pnl,
            "r_multiple": r_multiple,
        }, on_conflict="ticket").execute()
    except Exception as exc:
        log.error("supabase_trade_failed", ticket=ticket, exc=str(exc))


# ── Commands polling ──────────────────────────────────────────────────────────

def poll_pending_commands() -> list[dict]:
    """
    Return unacknowledged commands from the dashboard.
    Called every 2-5 seconds by the engine loop.
    """
    try:
        client = _get_client()
        resp = (
            client.table("commands")
            .select("*")
            .eq("status", "pending")
            .order("created_at")
            .limit(20)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        log.error("supabase_command_poll_failed", exc=str(exc))
        return []


def acknowledge_command(
    command_id: str,
    result: str,
    status: str = "done",
) -> None:
    """Write ack back to Supabase after executing a command."""
    try:
        client = _get_client()
        client.table("commands").update({
            "status": status,
            "result": result,
            "acked_at": _now(),
        }).eq("id", command_id).execute()
    except Exception as exc:
        log.error("supabase_ack_failed", command_id=command_id, exc=str(exc))


# ── Log ───────────────────────────────────────────────────────────────────────

def publish_log(
    level: str,
    code: str,
    message: str,
    context: dict | None = None,
) -> None:
    """Push a log entry to Supabase for the dashboard log viewer."""
    try:
        client = _get_client()
        client.table("logs").insert({
            "ts": _now(),
            "level": level,
            "code": code,
            "message": message,
            "context_json": json.dumps(context or {}),
        }).execute()
    except Exception as exc:
        # Never crash the engine because of a logging failure
        pass
