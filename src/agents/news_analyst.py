"""
Agent 2: The News Analyst — Macroeconomic Calendar and Event Risk Evaluator

Role:
- Evaluates economic event risk without external paid APIs (100% local operation).
- Tracks high-impact USD economic events (NFP, CPI, FOMC, PPI, Retail Sales).
- Enforces pre-event and post-event blackout windows (default: 30 min before, 30 min after).
- CRITICAL REQUIREMENT: If economic calendar data is stale (> 24 hours old or unavailable),
  The News Analyst MUST report status UNKNOWN with a risk score of 0.5/1.0 and advise caution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.utils.logging_config import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class EconomicEvent:
    """A scheduled economic calendar event."""
    event_id: str
    name: str                   # e.g., "US Non-Farm Payrolls", "US CPI YoY", "FOMC Rate Decision"
    currency: str               # e.g., "USD"
    event_time: datetime        # UTC
    impact: str                 # "HIGH", "MEDIUM", "LOW"
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None


@dataclass(frozen=True)
class NewsReport:
    """Structured report produced by The News Analyst."""
    timestamp: datetime
    status: str                 # "CLEAR", "HIGH_RISK_WINDOW", "UNKNOWN"
    blackout_active: bool       # True if trading should be locked due to high-impact news
    risk_score: float           # 0.0 (low risk) to 1.0 (extreme risk)
    upcoming_events: list[EconomicEvent]
    active_blackout_event: EconomicEvent | None
    data_age_hours: float       # Age of economic calendar dataset
    is_data_stale: bool         # True if data is > 24 hours old or missing
    reason: str


class NewsAnalystAgent:
    """
    Agent 2: The News Analyst.
    Evaluates macroeconomic risk locally and determines news-lock eligibility.
    """

    def __init__(
        self,
        blackout_minutes_before: int = 30,
        blackout_minutes_after: int = 30,
        max_data_age_hours: float = 24.0,
    ) -> None:
        self.blackout_minutes_before = blackout_minutes_before
        self.blackout_minutes_after = blackout_minutes_after
        self.max_data_age_hours = max_data_age_hours
        self._events: list[EconomicEvent] = []
        self._calendar_last_updated: datetime | None = None

    def update_calendar(self, events: list[EconomicEvent], updated_at: datetime | None = None) -> None:
        """Update the local economic calendar store."""
        self._events = list(events)
        self._calendar_last_updated = updated_at or datetime.now(tz=timezone.utc)
        log.info("news_calendar_updated", count=len(events), updated_at=self._calendar_last_updated.isoformat())

    def analyze(self, current_time: datetime | None = None) -> NewsReport:
        """
        Analyze economic news risk at current_time.
        Evaluates blackout windows and data freshness.
        """
        ts = current_time or datetime.now(tz=timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # 1. Check Data Freshness
        if self._calendar_last_updated is None:
            data_age = 999.0
            is_stale = True
        else:
            diff = (ts - self._calendar_last_updated).total_seconds()
            data_age = max(diff / 3600.0, 0.0)
            is_stale = data_age > self.max_data_age_hours

        # If data is stale, Master Spec mandates status UNKNOWN with risk_score = 0.5
        if is_stale or not self._events:
            return NewsReport(
                timestamp=ts,
                status="UNKNOWN",
                blackout_active=False,
                risk_score=0.5,
                upcoming_events=[],
                active_blackout_event=None,
                data_age_hours=data_age,
                is_data_stale=True,
                reason=f"Economic calendar data is stale ({data_age:.1f}h old) or empty. Status UNKNOWN.",
            )

        # 2. Check Active Blackout Windows for HIGH impact USD events
        active_event: EconomicEvent | None = None
        upcoming: list[EconomicEvent] = []

        before_delta = timedelta(minutes=self.blackout_minutes_before)
        after_delta = timedelta(minutes=self.blackout_minutes_after)

        for ev in self._events:
            ev_time = ev.event_time
            if ev_time.tzinfo is None:
                ev_time = ev_time.replace(tzinfo=timezone.utc)

            # Look for upcoming events within next 12 hours
            if ts <= ev_time <= ts + timedelta(hours=12):
                upcoming.append(ev)

            # Check if current time falls in [event_time - before, event_time + after]
            if ev.impact.upper() == "HIGH" and ev.currency.upper() in ("USD", "ALL"):
                if (ev_time - before_delta) <= ts <= (ev_time + after_delta):
                    active_event = ev

        if active_event is not None:
            return NewsReport(
                timestamp=ts,
                status="HIGH_RISK_WINDOW",
                blackout_active=True,
                risk_score=1.0,
                upcoming_events=upcoming,
                active_blackout_event=active_event,
                data_age_hours=data_age,
                is_data_stale=False,
                reason=(
                    f"Active news blackout for high-impact event '{active_event.name}' "
                    f"at {active_event.event_time.strftime('%H:%M')} UTC. New entries blocked."
                ),
            )

        # 3. Market is clear
        return NewsReport(
            timestamp=ts,
            status="CLEAR",
            blackout_active=False,
            risk_score=0.0,
            upcoming_events=upcoming,
            active_blackout_event=None,
            data_age_hours=data_age,
            is_data_stale=False,
            reason=f"No high-impact economic news within blackout window. {len(upcoming)} upcoming event(s).",
        )
