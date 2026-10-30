"""
Risk Management Engine.

Responsibilities:
- Calculate position size using broker symbol specifications.
- Validate stop-loss distance, spread, margin, volume constraints.
- Enforce daily trade limits, daily loss limits, consecutive-loss lockout.
- Block new entries when any lockout is active.

All limits are persisted via DailyRiskState so restarts cannot reset them.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.config.settings import RiskSettings
from src.data.market_data_adapter import SymbolInfo
from src.journal.models import DailyRiskState
from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class SizingResult:
    """Output of the position-sizing calculation."""
    approved: bool
    volume: float
    risk_usd: float
    reward_usd: float
    rr_ratio: float
    sl_distance_pips: float
    tp_distance_pips: float
    rejection_reason: str = ""


@dataclass
class RiskCheckResult:
    approved: bool
    rejection_reason: str = ""


class RiskEngine:
    """
    Stateless sizing + stateful daily-limit enforcement.

    Usage:
        engine = RiskEngine(settings, db, account_label)
        sizing = engine.calculate_size(...)
        check  = engine.check_daily_limits(symbol, sizing, db)
    """

    def __init__(
        self,
        settings: RiskSettings,
        account_label: str = "default",
    ) -> None:
        self.settings = settings
        self.account_label = account_label

    # ─────────────────────────────────────────────────────────────────────────
    # Position sizing
    # ─────────────────────────────────────────────────────────────────────────

    def calculate_size(
        self,
        symbol_info: SymbolInfo,
        direction: str,
        entry_price: float,
        sl_price: float,
        equity: float,
    ) -> SizingResult:
        """
        Calculate valid position volume that risks exactly risk_pct of equity.

        Returns SizingResult.approved=False with a reason if the trade
        cannot be sized within broker constraints.
        """
        s = self.settings
        si = symbol_info

        # ── Spread check (R59, R60) ───────────────────────────────────────────
        spread_pips = si.spread_pips
        # Per-symbol dict; None or missing key = unconfigured → block (R60)
        max_spread: float | None = s.max_spread_pips.get(si.name) if hasattr(s, "max_spread_pips") else None
        if max_spread is None:
            return SizingResult(
                approved=False, volume=0, risk_usd=0, reward_usd=0,
                rr_ratio=0, sl_distance_pips=0, tp_distance_pips=0,
                rejection_reason=(
                    f"Spread limit not configured for {si.name} — "
                    "entries blocked until calibrated (R60)"
                ),
            )
        if spread_pips > max_spread:
            return SizingResult(
                approved=False,
                volume=0,
                risk_usd=0,
                reward_usd=0,
                rr_ratio=0,
                sl_distance_pips=0,
                tp_distance_pips=0,
                rejection_reason=(
                    f"Spread {spread_pips:.1f} pips exceeds max {max_spread:.1f}"
                ),
            )

        # ── SL distance ───────────────────────────────────────────────────────
        if direction == "BULLISH":
            sl_distance = entry_price - sl_price
        else:
            sl_distance = sl_price - entry_price

        if sl_distance <= 0:
            return SizingResult(
                approved=False,
                volume=0, risk_usd=0, reward_usd=0, rr_ratio=0,
                sl_distance_pips=0, tp_distance_pips=0,
                rejection_reason=f"Invalid SL distance: {sl_distance}",
            )

        sl_distance_pips = sl_distance / si.point

        # ── Min stop level check ──────────────────────────────────────────────
        min_stop_points = si.trade_stops_level
        if sl_distance_pips < min_stop_points:
            return SizingResult(
                approved=False,
                volume=0, risk_usd=0, reward_usd=0, rr_ratio=0,
                sl_distance_pips=sl_distance_pips, tp_distance_pips=0,
                rejection_reason=(
                    f"SL distance {sl_distance_pips:.1f} pts < "
                    f"broker minimum {min_stop_points}"
                ),
            )

        # ── Monetary risk target ──────────────────────────────────────────────
        risk_usd_target = equity * (s.risk_pct_per_trade / 100.0)

        # ── Value per pip per 1 lot ───────────────────────────────────────────
        # value_per_pip = tick_value / tick_size * point
        # tick_value is already per contract per tick_size movement
        if si.tick_size == 0:
            return SizingResult(
                approved=False,
                volume=0, risk_usd=0, reward_usd=0, rr_ratio=0,
                sl_distance_pips=0, tp_distance_pips=0,
                rejection_reason="tick_size is zero (bad symbol spec)",
            )

        pip_value_per_lot = (si.tick_value / si.tick_size) * si.point

        # ── Volume calculation ────────────────────────────────────────────────
        # risk = volume * sl_distance_pips * pip_value_per_lot
        # => volume = risk / (sl_distance_pips * pip_value_per_lot)
        if pip_value_per_lot <= 0 or sl_distance_pips <= 0:
            return SizingResult(
                approved=False,
                volume=0, risk_usd=0, reward_usd=0, rr_ratio=0,
                sl_distance_pips=sl_distance_pips, tp_distance_pips=0,
                rejection_reason="Cannot compute pip value — check symbol spec",
            )

        raw_volume = risk_usd_target / (sl_distance_pips * pip_value_per_lot)

        # Round DOWN to valid volume step
        volume = self._round_volume(raw_volume, si.volume_step, si.volume_min)

        if volume < si.volume_min:
            return SizingResult(
                approved=False,
                volume=volume,
                risk_usd=volume * sl_distance_pips * pip_value_per_lot,
                reward_usd=0,
                rr_ratio=0,
                sl_distance_pips=sl_distance_pips,
                tp_distance_pips=0,
                rejection_reason=(
                    f"Computed volume {volume} < broker minimum {si.volume_min}. "
                    f"Account equity too small or stop too wide."
                ),
            )

        if volume > si.volume_max:
            volume = si.volume_max

        actual_risk_usd = volume * sl_distance_pips * pip_value_per_lot

        # ── TP / R:R ─────────────────────────────────────────────────────────
        tp_distance = sl_distance * s.min_reward_to_risk
        tp_distance_pips = tp_distance / si.point
        reward_usd = volume * tp_distance_pips * pip_value_per_lot
        rr_ratio = reward_usd / actual_risk_usd if actual_risk_usd > 0 else 0

        return SizingResult(
            approved=True,
            volume=volume,
            risk_usd=actual_risk_usd,
            reward_usd=reward_usd,
            rr_ratio=rr_ratio,
            sl_distance_pips=sl_distance_pips,
            tp_distance_pips=tp_distance_pips,
        )

    def calculate_tp(
        self,
        direction: str,
        entry_price: float,
        sl_price: float,
        rr_ratio: float | None = None,
    ) -> float:
        """Calculate take-profit price for a given R:R."""
        if rr_ratio is None:
            rr_ratio = self.settings.min_reward_to_risk
        if direction == "BULLISH":
            return entry_price + (entry_price - sl_price) * rr_ratio
        else:
            return entry_price - (sl_price - entry_price) * rr_ratio

    # ─────────────────────────────────────────────────────────────────────────
    # Daily limits
    # ─────────────────────────────────────────────────────────────────────────

    def get_or_create_daily_state(
        self, db: Session, symbol: str, today: date, start_equity: float | None
    ) -> DailyRiskState:
        row = (
            db.query(DailyRiskState)
            .filter(
                DailyRiskState.trade_date == today,
                DailyRiskState.account_label == self.account_label,
                DailyRiskState.symbol == symbol,
            )
            .first()
        )
        if row is None:
            row = DailyRiskState(
                trade_date=today,
                account_label=self.account_label,
                symbol=symbol,
                start_equity=start_equity,
                new_entries_today=0,
                realized_pnl_today=0.0,
                daily_loss_lock=False,
                daily_trade_lock=False,
                news_lock=False,
                consecutive_loss_lock=False,
                consecutive_losses=0,
                updated_at=datetime.now(tz=timezone.utc),
            )
            db.add(row)
            db.commit()
        return row

    def check_daily_limits(
        self,
        db: Session,
        symbol: str,
        sizing: SizingResult,
        current_equity: float,
        today: date | None = None,
    ) -> RiskCheckResult:
        """
        Check all daily limits. Returns approved=True only when ALL pass.
        """
        if today is None:
            today = datetime.now(tz=timezone.utc).date()

        row = self.get_or_create_daily_state(db, symbol, today, current_equity)

        # ── Lockout checks ────────────────────────────────────────────────────
        if row.news_lock:
            return RiskCheckResult(False, "News lockout is active")
        if row.consecutive_loss_lock:
            return RiskCheckResult(
                False,
                f"Consecutive-loss lockout ({row.consecutive_losses} losses)"
            )
        if row.daily_loss_lock:
            return RiskCheckResult(False, "Daily loss limit reached")
        if row.daily_trade_lock:
            return RiskCheckResult(
                False,
                f"Daily trade limit reached ({row.new_entries_today} entries)"
            )

        # ── Daily trade count ─────────────────────────────────────────────────
        if row.new_entries_today >= self.settings.max_daily_trades:
            row.daily_trade_lock = True
            row.updated_at = datetime.now(tz=timezone.utc)
            db.commit()
            return RiskCheckResult(
                False,
                f"Daily trade limit ({self.settings.max_daily_trades}) reached"
            )

        # ── Daily loss check ─────────────────────────────────────────────────
        if row.start_equity and row.start_equity > 0:
            max_loss = row.start_equity * (self.settings.daily_loss_pct / 100.0)
            if row.realized_pnl_today <= -max_loss:
                row.daily_loss_lock = True
                row.updated_at = datetime.now(tz=timezone.utc)
                db.commit()
                return RiskCheckResult(
                    False,
                    f"Daily loss limit reached: "
                    f"P/L={row.realized_pnl_today:.2f} limit=-{max_loss:.2f}"
                )

        return RiskCheckResult(True)

    def record_new_entry(
        self, db: Session, symbol: str, today: date | None = None
    ) -> None:
        if today is None:
            today = datetime.now(tz=timezone.utc).date()
        row = self.get_or_create_daily_state(db, symbol, today, None)
        row.new_entries_today += 1
        row.updated_at = datetime.now(tz=timezone.utc)
        db.commit()

    def record_closed_trade(
        self,
        db: Session,
        symbol: str,
        pnl: float,
        today: date | None = None,
    ) -> None:
        if today is None:
            today = datetime.now(tz=timezone.utc).date()
        row = self.get_or_create_daily_state(db, symbol, today, None)
        row.realized_pnl_today += pnl

        if pnl < 0:
            row.consecutive_losses += 1
            if (
                self.settings.max_consecutive_losses > 0
                and row.consecutive_losses >= self.settings.max_consecutive_losses
            ):
                row.consecutive_loss_lock = True
                log.warning(
                    "consecutive_loss_lockout",
                    symbol=symbol,
                    count=row.consecutive_losses,
                )
        else:
            row.consecutive_losses = 0

        row.updated_at = datetime.now(tz=timezone.utc)
        db.commit()

    def set_news_lock(
        self, db: Session, symbol: str, locked: bool, today: date | None = None
    ) -> None:
        if today is None:
            today = datetime.now(tz=timezone.utc).date()
        row = self.get_or_create_daily_state(db, symbol, today, None)
        row.news_lock = locked
        row.updated_at = datetime.now(tz=timezone.utc)
        db.commit()
        log.info("news_lock_set", symbol=symbol, locked=locked)

    def clear_consecutive_loss_lock(
        self, db: Session, symbol: str, today: date | None = None
    ) -> None:
        if today is None:
            today = datetime.now(tz=timezone.utc).date()
        row = self.get_or_create_daily_state(db, symbol, today, None)
        row.consecutive_loss_lock = False
        row.consecutive_losses = 0
        row.updated_at = datetime.now(tz=timezone.utc)
        db.commit()

    def get_lockout_status(
        self, db: Session, symbol: str, today: date | None = None
    ) -> dict:
        if today is None:
            today = datetime.now(tz=timezone.utc).date()
        row = self.get_or_create_daily_state(db, symbol, today, None)
        return {
            "daily_loss_lock": row.daily_loss_lock,
            "daily_trade_lock": row.daily_trade_lock,
            "news_lock": row.news_lock,
            "consecutive_loss_lock": row.consecutive_loss_lock,
            "consecutive_losses": row.consecutive_losses,
            "new_entries_today": row.new_entries_today,
            "realized_pnl_today": row.realized_pnl_today,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _round_volume(raw: float, step: float, minimum: float) -> float:
        """Round DOWN to the nearest valid volume step, respecting minimum."""
        if step <= 0:
            return max(minimum, raw)
        # Floor to step
        steps = math.floor(raw / step)
        volume = steps * step
        # Round to 2 decimal places to avoid floating-point artifacts
        volume = round(volume, 8)
        return volume
