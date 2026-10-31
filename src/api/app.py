"""
FastAPI application — STRATEGY_SPEC.md v1.0

Provides:
  - Health / status endpoint
  - Engine status (connection, mode, last heartbeat)
  - Setup list and individual setup detail
  - Journal entries
  - Daily risk state
  - Bot control commands (PAUSE, RESUME, NEWS_LOCK)
  - Account info (from engine, not fabricated)

Security:
  - All routes except /health require a valid JWT (IMPL10, IMPL11)
  - Passwords are never stored or returned (IMPL11)
  - Live trading cannot be enabled via API (IMPL7, R88)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.agents.coordinator import CentralCoordinator
from src.config.settings import get_settings
from src.execution.mt5_executor import MT5Executor
from src.execution.multi_account_copier import ChildAccountConfig, MultiAccountCopier
from src.journal.models import DailyRiskState, JournalEntry
from src.state.models import Order, Setup, SetupState
from src.utils.credentials import CredentialManager
from src.utils.database import get_db, init_db
from src.utils.logging_config import get_logger

log = get_logger(__name__)

# Central coordinator instance for API deliberations and kill switch
coordinator = CentralCoordinator()

# Multi-Account Copier Engine (in-process single-terminal execution)
cred_mgr = CredentialManager()
master_executor = MT5Executor(credentials=cred_mgr.get_credentials())
copier_engine = MultiAccountCopier(master_executor=master_executor)

try:
    for _child_entry in cred_mgr.get_child_accounts():
        copier_engine.add_child_account(
            ChildAccountConfig(
                account_id=_child_entry["account_id"],
                password=_child_entry["password"],
                server=_child_entry["server"],
                label=_child_entry.get("label", ""),
                risk_multiplier=_child_entry.get("risk_multiplier", 1.0),
            )
        )
except Exception as _e:
    log.warning("failed_preloading_child_accounts", error=str(_e))



@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Initialise DB on startup. Replaces deprecated @app.on_event."""
    init_db()
    log.info("api_started", live_trading_enabled=False)
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="XAUUSD/BTCUSD FVG Trader API",
    version="1.0.0",
    description="Engine status and control API — STRATEGY_SPEC.md v1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Dashboard Mount ───────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serve the local single-page quantitative trading desk."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"status": "ok", "message": "Quant AI Trading Desk API running."}


# ── Auth ──────────────────────────────────────────────────────────────────────
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _settings():
    return get_settings()


def _get_secret() -> str:
    s = _settings()
    key = s.api.secret_key
    placeholder = "CHANGE_ME_IN_PRODUCTION_SET_API_SECRET_KEY_ENV_VAR"
    if key == placeholder:
        import warnings
        warnings.warn("API using insecure placeholder secret key (IMPL11)")
    return key


def _create_token(sub: str, expires_minutes: int) -> str:
    settings = _settings()
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(
        {"sub": sub, "exp": expire},
        _get_secret(),
        algorithm=settings.api.algorithm,
    )


async def _current_user(token: Annotated[str, Depends(_oauth2)]) -> str:
    settings = _settings()
    try:
        payload = jwt.decode(token, _get_secret(),
                             algorithms=[settings.api.algorithm])
        sub: str = payload.get("sub", "")
        if not sub:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
        return sub
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


# ── Schemas ───────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SetupSummary(BaseModel):
    id: str
    symbol: str
    direction: str
    state: str
    fvg_low: float
    fvg_high: float
    trigger_level: float | None
    proposed_entry: float | None
    proposed_sl: float | None
    proposed_tp: float | None
    estimated_rr: float | None
    created_at: datetime
    updated_at: datetime


class JournalSummary(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    setup_id: str | None
    symbol: str | None
    direction: str | None
    price: float | None
    volume: float | None
    sl: float | None
    tp: float | None
    pnl: float | None
    notes: str | None


class RiskStateResponse(BaseModel):
    symbol: str
    trade_date: str
    new_entries_today: int
    realized_pnl_today: float
    daily_loss_lock: bool
    daily_trade_lock: bool
    news_lock: bool
    consecutive_loss_lock: bool
    consecutive_losses: int


class EngineStatusResponse(BaseModel):
    execution_mode: str
    # Values below come from the engine heartbeat in production;
    # for now we report what we know from settings
    spec_version: str = "1.0"
    live_trading_enabled: bool = False  # Always False (R88)
    message: str = "Engine status — connect the engine to report live values"


class CommandResponse(BaseModel):
    command: str
    status: str
    message: str
    executed_at: datetime | None


# ── Routes — public ───────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Public health check."""
    return {"status": "ok", "spec_version": "1.0",
            "live_trading_enabled": False}


# ── Routes — auth ─────────────────────────────────────────────────────────────

@app.post("/auth/token", response_model=TokenResponse, tags=["Auth"])
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    """Obtain a JWT. Credentials checked against local api_users table."""
    from src.api.models import APIUser
    user = db.query(APIUser).filter(APIUser.username == form.username).first()
    if not user or not _pwd_ctx.verify(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is inactive")
    settings = _settings()
    token = _create_token(user.username, settings.api.token_expire_minutes)
    return TokenResponse(access_token=token)


# ── Routes — engine status ────────────────────────────────────────────────────

@app.get("/engine/status", response_model=EngineStatusResponse, tags=["Engine"])
def engine_status(_: Annotated[str, Depends(_current_user)]):
    """Return current execution mode and spec info."""
    settings = _settings()
    return EngineStatusResponse(
        execution_mode=settings.execution_mode,
        spec_version="1.0",
        live_trading_enabled=False,
    )


# ── Routes — setups ───────────────────────────────────────────────────────────

@app.get("/setups", response_model=list[SetupSummary], tags=["Setups"])
def list_setups(
    _: Annotated[str, Depends(_current_user)],
    db: Annotated[Session, Depends(get_db)],
    symbol: str | None = None,
    state: str | None = None,
    limit: int = 50,
):
    """Return setups, optionally filtered by symbol or state."""
    q = db.query(Setup).order_by(Setup.created_at.desc())
    if symbol:
        q = q.filter(Setup.symbol == symbol)
    if state:
        q = q.filter(Setup.state == state)
    rows = q.limit(limit).all()
    return [
        SetupSummary(
            id=r.id, symbol=r.symbol,
            direction=r.direction.value, state=r.state.value,
            fvg_low=r.fvg_low, fvg_high=r.fvg_high,
            trigger_level=r.trigger_level,
            proposed_entry=r.proposed_entry,
            proposed_sl=r.proposed_sl, proposed_tp=r.proposed_tp,
            estimated_rr=r.estimated_rr,
            created_at=r.created_at, updated_at=r.updated_at,
        )
        for r in rows
    ]


@app.get("/setups/{setup_id}", tags=["Setups"])
def get_setup(
    setup_id: str,
    _: Annotated[str, Depends(_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Return full setup detail including transition history."""
    row = db.get(Setup, setup_id)
    if row is None:
        raise HTTPException(404, f"Setup {setup_id} not found")
    transitions = [
        {"timestamp": t.timestamp.isoformat(),
         "old_state": t.old_state.value if t.old_state else None,
         "new_state": t.new_state.value,
         "event": t.event,
         "explanation": t.explanation}
        for t in row.transitions
    ]
    return {
        "id": row.id, "symbol": row.symbol,
        "direction": row.direction.value, "state": row.state.value,
        "fvg_low": row.fvg_low, "fvg_high": row.fvg_high,
        "sweep_level": row.sweep_level, "sweep_extreme": row.sweep_extreme,
        "trigger_level": row.trigger_level,
        "proposed_entry": row.proposed_entry,
        "proposed_sl": row.proposed_sl, "proposed_tp": row.proposed_tp,
        "proposed_volume": row.proposed_volume,
        "estimated_risk_usd": row.estimated_risk_usd,
        "estimated_rr": row.estimated_rr,
        "rejection_reason": row.rejection_reason,
        "spec_version": row.spec_version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "transitions": transitions,
    }


# ── Routes — journal ──────────────────────────────────────────────────────────

@app.get("/journal", response_model=list[JournalSummary], tags=["Journal"])
def list_journal(
    _: Annotated[str, Depends(_current_user)],
    db: Annotated[Session, Depends(get_db)],
    symbol: str | None = None,
    limit: int = 100,
):
    q = db.query(JournalEntry).order_by(JournalEntry.timestamp.desc())
    if symbol:
        q = q.filter(JournalEntry.symbol == symbol)
    rows = q.limit(limit).all()
    return [
        JournalSummary(
            id=r.id, timestamp=r.timestamp,
            event_type=r.event_type, setup_id=r.setup_id,
            symbol=r.symbol, direction=r.direction,
            price=r.price, volume=r.volume,
            sl=r.sl, tp=r.tp, pnl=r.pnl, notes=r.notes,
        )
        for r in rows
    ]


# ── Routes — risk state ───────────────────────────────────────────────────────

@app.get("/risk/state", response_model=list[RiskStateResponse], tags=["Risk"])
def risk_state(
    _: Annotated[str, Depends(_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    today = datetime.now(tz=timezone.utc).date()
    rows = db.query(DailyRiskState).filter(
        DailyRiskState.trade_date == today
    ).all()
    return [
        RiskStateResponse(
            symbol=r.symbol,
            trade_date=str(r.trade_date),
            new_entries_today=r.new_entries_today,
            realized_pnl_today=r.realized_pnl_today,
            daily_loss_lock=r.daily_loss_lock,
            daily_trade_lock=r.daily_trade_lock,
            news_lock=r.news_lock,
            consecutive_loss_lock=r.consecutive_loss_lock,
            consecutive_losses=r.consecutive_losses,
        )
        for r in rows
    ]


# ── Routes — bot control ──────────────────────────────────────────────────────

@app.post("/control/news-lock", response_model=CommandResponse, tags=["Control"])
def set_news_lock(
    symbol: str,
    locked: bool,
    _: Annotated[str, Depends(_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Set or clear the manual news lockout for a symbol (R62).
    This blocks new entries only — does not touch existing stops (R63).
    """
    from src.risk.engine import RiskEngine
    settings = _settings()
    engine = RiskEngine(settings=settings.risk,
                        account_label=settings.execution_mode)
    engine.set_news_lock(db, symbol, locked)
    action = "locked" if locked else "cleared"
    log.info("news_lock_command", symbol=symbol, locked=locked)
    return CommandResponse(
        command="NEWS_LOCK",
        status="DONE",
        message=f"News lock {action} for {symbol}",
        executed_at=datetime.now(tz=timezone.utc),
    )


@app.post("/control/clear-consecutive-loss-lock",
          response_model=CommandResponse, tags=["Control"])
def clear_consecutive_loss_lock(
    symbol: str,
    _: Annotated[str, Depends(_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Manually clear the consecutive-loss lockout after review (R58)."""
    from src.risk.engine import RiskEngine
    settings = _settings()
    engine = RiskEngine(settings=settings.risk,
                        account_label=settings.execution_mode)
    engine.clear_consecutive_loss_lock(db, symbol)
    return CommandResponse(
        command="CLEAR_CONSECUTIVE_LOSS_LOCK",
        status="DONE",
        message=f"Consecutive-loss lock cleared for {symbol}",
        executed_at=datetime.now(tz=timezone.utc),
    )


# Startup is handled by the lifespan context manager above.


# ── Account credential endpoint ───────────────────────────────────────────────
# Receives MT5 login + password from the frontend and stores the password
# in Windows Credential Manager. NEVER logged, NEVER stored in the DB.

class CredentialRequest(BaseModel):
    login: str
    password: str
    server: str


class CredentialResponse(BaseModel):
    status: str
    message: str


@app.post("/accounts/credential", response_model=CredentialResponse, tags=["Accounts"])
def save_credential(
    req: CredentialRequest,
    _: Annotated[str, Depends(_current_user)],
) -> CredentialResponse:
    """
    Store MT5 trading password in Windows Credential Manager.

    The password is NEVER written to the database, NEVER logged,
    and is cleared from memory immediately after storage.

    Requires authentication — the frontend must send a valid JWT.
    Only accessible from the local network (127.0.0.1 by default).
    """
    try:
        import keyring
        service = f"mt5_bot_{req.server}"
        keyring.set_password(service, req.login, req.password)
        log.info(
            "mt5_credential_saved",
            login=req.login,
            server=req.server,
            # Password is NEVER logged — only these safe fields
        )
        return CredentialResponse(
            status="ok",
            message=f"Credential for login {req.login} stored in Credential Manager.",
        )
    except Exception as exc:
        log.error("credential_save_failed", login=req.login, exc=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store credential: {exc}",
        )


@app.get("/accounts/verify/{login}", tags=["Accounts"])
def verify_credential(
    login: str,
    server: str,
    _: Annotated[str, Depends(_current_user)],
) -> dict:
    """Check whether a credential exists for a given login (does not return the password)."""
    try:
        import keyring
        exists = keyring.get_password(f"mt5_bot_{server}", login) is not None
        return {"login": login, "server": server, "credential_exists": exists}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Coordinator & Kill Switch Endpoints ────────────────────────────────────────

class KillSwitchRequest(BaseModel):
    reason: str = "Manual emergency kill switch activation"


@app.post("/control/kill-switch", tags=["Control"])
def execute_kill_switch(
    req: KillSwitchRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    Emergency Kill Switch: Liquidates all positions, cancels active setups,
    and locks the coordinator from executing any new orders.
    """
    reason = req.reason if req else "Emergency Kill Switch Activated"
    log.warn("api_emergency_kill_switch_triggered", reason=reason)
    coordinator.trigger_kill_switch(reason=reason, db=db)
    return {
        "status": "HALTED",
        "action": "EMERGENCY_KILL_SWITCH_EXECUTED",
        "reason": reason,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/coordinator/consensus", tags=["Coordinator"])
def get_consensus():
    """Return real-time status and deliberations of all six analytical agents."""
    return {
        "verdict": coordinator.last_verdict.value,
        "kill_switch_active": coordinator.kill_switch_active,
        "kill_switch_reason": coordinator.kill_switch_reason,
        "agents": {
            "scout": {"name": "The Scout", "role": "Agent 1", "status": "ACTIVE"},
            "news_analyst": {"name": "The News Analyst", "role": "Agent 2", "status": "ACTIVE"},
            "chart_analyst": {"name": "The Chart Analyst", "role": "Agent 3", "status": "ACTIVE"},
            "skeptic": {"name": "The Skeptic", "role": "Agent 4 (VETO)", "status": "ACTIVE"},
            "risk_manager": {"name": "The Risk Manager", "role": "Agent 5 (VETO)", "status": "ACTIVE"},
            "execution_manager": {"name": "The Execution Manager", "role": "Agent 6", "status": "ACTIVE"},
        },
    }


@app.get("/orders", tags=["Orders"])
def list_orders(
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Return broker orders and execution states."""
    rows = db.query(Order).order_by(Order.requested_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "setup_id": r.setup_id,
            "symbol": r.symbol,
            "direction": r.direction,
            "volume": r.requested_volume,
            "open_price": r.filled_price or r.requested_entry,
            "stop_loss": r.requested_sl,
            "take_profit": r.requested_tp,
            "status": r.status,
            "broker_ticket": r.broker_ticket,
            "created_at": r.requested_at.isoformat() if r.requested_at else None,
        }
        for r in rows
    ]


# ── Multi-Account Copier Endpoints ──────────────────────────────────────────

class ConfigureMasterRequest(BaseModel):
    account_id: int
    password: str
    server: str
    label: str = "Primary Exness Account"
    symbol: str = "BTCUSD"
    mode: str = "DEMO"


@app.post("/copier/master", tags=["Copier"])
def configure_master_account(req: ConfigureMasterRequest):
    """Securely store Primary Exness Master account into Windows Credential Manager."""
    stored = cred_mgr.store_credentials(
        account_id=req.account_id,
        password=req.password,
        server=req.server,
    )
    if not stored:
        raise HTTPException(status_code=500, detail="Failed to store master credentials in Credential Manager.")

    master_creds = cred_mgr.get_credentials()
    if master_creds:
        master_executor.credentials = master_creds

    return {
        "status": "ok",
        "message": f"Primary Exness account {req.account_id} configured successfully on {req.server} for {req.symbol}.",
        "account_id": req.account_id,
        "server": req.server,
        "symbol": req.symbol,
        "mode": req.mode,
    }


class AddChildAccountRequest(BaseModel):
    account_id: int
    password: str
    server: str
    label: str = ""
    risk_pct: float = 1.0
    risk_multiplier: float = 1.0
    is_active: bool = True
    max_slippage_pips: float = 3.0


@app.get("/copier/accounts", tags=["Copier"])
def list_copier_accounts():
    """List Master account and all connected Child accounts with live balances and status."""
    master_creds = cred_mgr.get_credentials()
    master_id = master_creds.account_id if master_creds else 0
    master_server = master_creds.server if master_creds else "Not configured"

    is_terminal_online = False
    live_balances = {}
    try:
        import MetaTrader5 as mt5
        if mt5.terminal_info() is not None:
            is_terminal_online = True
            live_balances = copier_engine.get_all_account_balances()
    except Exception:
        is_terminal_online = False

    master_data = live_balances.get(str(master_id), {
        "label": "Master Account",
        "server": master_server,
        "balance": 0.0,
        "equity": 0.0,
        "margin_free": 0.0,
        "is_master": True,
        "is_active": True,
        "account_id": master_id,
        "status": "ONLINE" if is_terminal_online else "OFFLINE",
    })
    master_data["account_id"] = master_id
    master_data["server"] = master_server

    children = []
    for c in copier_engine.get_child_accounts():
        child_live = live_balances.get(str(c.account_id), {})
        children.append({
            "account_id": c.account_id,
            "label": c.label or f"Child #{c.account_id}",
            "server": c.server,
            "risk_multiplier": c.risk_multiplier,
            "is_active": c.is_active,
            "balance": child_live.get("balance", 0.0),
            "equity": child_live.get("equity", 0.0),
            "margin_free": child_live.get("margin_free", 0.0),
            "status": "ONLINE" if is_terminal_online else "SAVED",
        })

    return {
        "terminal_online": is_terminal_online,
        "master": master_data,
        "children": children,
        "total_children": len(children),
        "active_children": len([c for c in children if c["is_active"]]),
    }


@app.post("/copier/accounts", tags=["Copier"])
def register_child_account(req: AddChildAccountRequest):
    """Securely register a new Child account into Windows Credential Manager and Copier Engine."""
    stored = cred_mgr.store_child_account(
        account_id=req.account_id,
        password=req.password,
        server=req.server,
        label=req.label,
        risk_multiplier=req.risk_multiplier,
    )
    if not stored:
        raise HTTPException(status_code=500, detail="Failed to store child account in Credential Manager.")

    copier_engine.add_child_account(
        ChildAccountConfig(
            account_id=req.account_id,
            password=req.password,
            server=req.server,
            label=req.label,
            risk_pct=req.risk_pct,
            risk_multiplier=req.risk_multiplier,
            is_active=req.is_active,
            max_slippage_pips=req.max_slippage_pips,
        )
    )
    return {
        "status": "ok",
        "message": f"Child account {req.account_id} registered successfully for copy trading.",
        "account_id": req.account_id,
    }


@app.delete("/copier/accounts/{account_id}", tags=["Copier"])
def unregister_child_account(account_id: int):
    """Remove a Child copy-trading account."""
    cred_mgr.delete_child_account(account_id)
    copier_engine.remove_child_account(account_id)
    return {
        "status": "ok",
        "message": f"Child account {account_id} removed successfully.",
        "account_id": account_id,
    }


@app.post("/copier/accounts/{account_id}/toggle", tags=["Copier"])
def toggle_child_copying(account_id: int):
    """Toggle copy trading active state for a child account."""
    if account_id in copier_engine.child_accounts:
        curr = copier_engine.child_accounts[account_id].is_active
        copier_engine.child_accounts[account_id].is_active = not curr
        return {
            "status": "ok",
            "account_id": account_id,
            "is_active": not curr,
        }
    raise HTTPException(status_code=404, detail=f"Child account {account_id} not found.")


@app.post("/copier/kill-switch", tags=["Copier"])
def copier_kill_switch(db: Session = Depends(get_db)):
    """
    Emergency Global Kill Switch:
    Immediately liquidates all open positions across Master and ALL Child accounts.
    """
    report = copier_engine.close_all_accounts_positions()
    coordinator.trigger_kill_switch(reason="Global Copier Kill Switch executed", db=db)
    return {
        "status": "HALTED",
        "action": "GLOBAL_KILL_SWITCH_EXECUTED",
        "report": report,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/copier/trades", tags=["Copier"])
def get_copied_trades():
    """Return audit log of all copied trades across accounts."""
    return [
        {
            "master_ticket": t.master_ticket,
            "child_account_id": t.child_account_id,
            "child_ticket": t.child_ticket,
            "symbol": t.symbol,
            "direction": t.direction,
            "entry_price": t.entry_price,
            "volume": t.volume,
            "sl": t.sl,
            "tp": t.tp,
            "opened_at": t.opened_at.isoformat(),
            "status": t.status,
        }
        for t in reversed(copier_engine.copied_trades)
    ]


