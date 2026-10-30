"""
Agent 5: The Risk Manager — Capital Preservation, Position Sizing, and Exposure Gatekeeper

Role:
- Enforces strict capital preservation rules with explicit VETO authority.
- Calculates exact 1.0% risk per trade based on broker symbol specifications.
- Validates minimum 1:2 Risk/Reward ratio (hard rule R40).
- Enforces maximum 5 trades per calendar day (hard limit).
- Enforces daily loss lock (3.0% max daily drawdown).
- Enforces consecutive-loss lockout (3 consecutive losses).
- Prevents concurrent over-exposure (max 1 position per instrument).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.config.settings import RiskSettings
from src.data.market_data_adapter import SymbolInfo
from src.risk.engine import RiskEngine, SizingResult
from src.strategy.part3_strategy import Part3TradeSignal
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class RiskManagerReport:
    """Structured report produced by The Risk Manager."""
    approved: bool              # True if risk check passes; False triggers VETO
    lot_size: float
    risk_usd: float
    reward_usd: float
    actual_rr: float
    sl_distance_pips: float
    tp_distance_pips: float
    daily_trades_count: int
    daily_loss_locked: bool
    consecutive_loss_locked: bool
    rejection_reason: str = ""


class RiskManagerAgent:
    """
    Agent 5: The Risk Manager.
    Has full VETO authority. If approved=False, Coordinator aborts order submission.
    """

    def __init__(
        self,
        risk_settings: RiskSettings,
        account_label: str = "default",
    ) -> None:
        self.settings = risk_settings
        self.risk_engine = RiskEngine(settings=risk_settings, account_label=account_label)

    def evaluate_risk(
        self,
        signal: Part3TradeSignal,
        symbol_info: SymbolInfo,
        equity: float,
        db: Session | None = None,
        open_positions_count: int = 0,
        trade_date: date | None = None,
    ) -> RiskManagerReport:
        """
        Evaluate proposed trade parameters against all risk rules.
        """
        # 1. Check concurrent position limit (max 1 per instrument)
        if open_positions_count >= 1:
            return RiskManagerReport(
                approved=False,
                lot_size=0.0,
                risk_usd=0.0,
                reward_usd=0.0,
                actual_rr=signal.rr,
                sl_distance_pips=0.0,
                tp_distance_pips=0.0,
                daily_trades_count=0,
                daily_loss_locked=False,
                consecutive_loss_locked=False,
                rejection_reason=f"Concurrent position limit reached: {symbol_info.name} already has open trade.",
            )

        # 2. Minimum 1:2 R:R verification
        min_rr = getattr(self.settings, "min_reward_to_risk", 2.0)
        if signal.rr < min_rr:
            return RiskManagerReport(
                approved=False,
                lot_size=0.0,
                risk_usd=0.0,
                reward_usd=0.0,
                actual_rr=signal.rr,
                sl_distance_pips=0.0,
                tp_distance_pips=0.0,
                daily_trades_count=0,
                daily_loss_locked=False,
                consecutive_loss_locked=False,
                rejection_reason=f"R:R ratio {signal.rr:.2f} is below mandatory minimum {min_rr:.1f} (R40).",
            )

        # 3. Position Sizing calculation (1% dollar risk)
        sizing: SizingResult = self.risk_engine.calculate_size(
            symbol_info=symbol_info,
            direction=signal.direction,
            entry_price=signal.entry_price,
            sl_price=signal.sl_price,
            equity=equity,
        )

        if not sizing.approved:
            return RiskManagerReport(
                approved=False,
                lot_size=sizing.volume,
                risk_usd=sizing.risk_usd,
                reward_usd=sizing.reward_usd,
                actual_rr=sizing.rr_ratio,
                sl_distance_pips=sizing.sl_distance_pips,
                tp_distance_pips=sizing.tp_distance_pips,
                daily_trades_count=0,
                daily_loss_locked=False,
                consecutive_loss_locked=False,
                rejection_reason=f"Position sizing rejected: {sizing.rejection_reason}",
            )

        # 4. Daily limits & lockout check (persisted state)
        daily_count = 0
        loss_locked = False
        consec_locked = False

        if db is not None:
            t_date = trade_date or datetime.now(tz=timezone.utc).date()
            check = self.risk_engine.check_daily_limits(
                db=db,
                symbol=symbol_info.name,
                sizing=sizing,
                current_equity=equity,
                today=t_date,
            )
            state = self.risk_engine.get_or_create_daily_state(
                db=db,
                symbol=symbol_info.name,
                today=t_date,
                start_equity=equity,
            )
            daily_count = state.new_entries_today
            loss_locked = state.daily_loss_lock
            consec_locked = state.consecutive_loss_lock

            if not check.approved:
                return RiskManagerReport(
                    approved=False,
                    lot_size=sizing.volume,
                    risk_usd=sizing.risk_usd,
                    reward_usd=sizing.reward_usd,
                    actual_rr=sizing.rr_ratio,
                    sl_distance_pips=sizing.sl_distance_pips,
                    tp_distance_pips=sizing.tp_distance_pips,
                    daily_trades_count=daily_count,
                    daily_loss_locked=loss_locked,
                    consecutive_loss_locked=consec_locked,
                    rejection_reason=f"Daily risk limit active: {check.rejection_reason}",
                )

        # 5. Risk Approved
        log.info(
            "risk_manager_approved",
            symbol=symbol_info.name,
            direction=signal.direction,
            volume=sizing.volume,
            risk_usd=sizing.risk_usd,
            rr=sizing.rr_ratio,
        )

        return RiskManagerReport(
            approved=True,
            lot_size=sizing.volume,
            risk_usd=sizing.risk_usd,
            reward_usd=sizing.reward_usd,
            actual_rr=sizing.rr_ratio,
            sl_distance_pips=sizing.sl_distance_pips,
            tp_distance_pips=sizing.tp_distance_pips,
            daily_trades_count=daily_count,
            daily_loss_locked=loss_locked,
            consecutive_loss_locked=consec_locked,
            rejection_reason="",
        )
