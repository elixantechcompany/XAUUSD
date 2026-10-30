"""
Central application settings — v1.0 (aligned with STRATEGY_SPEC.md v1.0).

All tuneable values live here.
Secrets (MT5 password, API secret key) come from environment variables
or Windows Credential Manager — never from this file.

Values labelled PROPOSED_DEFAULT are configurable initial values from the spec.
They are not claimed to be optimal or profitable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parents[2]
DATA_DIR   = ROOT_DIR / "data"
DB_DIR     = DATA_DIR / "db"
LOG_DIR    = DATA_DIR / "logs"
EXPORT_DIR = DATA_DIR / "exports"

for _d in (DB_DIR, LOG_DIR, EXPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── Spread limits: None means "not yet calibrated — block entries" ─────────────
# Per STRATEGY_SPEC.md R59/R60: no hardcoded default; must be set from real data.
_UNCONFIGURED_SPREAD = None


class StrategySettings(BaseSettings):
    """
    Strategy configuration.

    APPROVED values (✅): fixed — changing them requires a new spec version.
    PROPOSED_DEFAULT values (🔶): configurable initial values from spec v1.0.
    """
    model_config = SettingsConfigDict(env_prefix="STRATEGY_")

    # ── Instruments (R1 ✅) ───────────────────────────────────────────────────
    # Actual broker symbol names discovered at runtime via MT5; these are the
    # base names used for lookup. Suffixes are resolved by the adapter.
    symbols: list[str] = ["XAUUSD", "BTCUSD"]

    # ── Timeframe (R2 ✅) ─────────────────────────────────────────────────────
    timeframe: str = "H1"

    # ── Entry trigger mode (R29 ✅ default, R30 ✅ alternative) ──────────────
    # "CANDLE_CLOSE" is the approved default.
    entry_trigger_mode: Literal["CANDLE_CLOSE", "TICK_BREAK"] = "CANDLE_CLOSE"

    # ── Tick-break staleness (R31 ✅) ─────────────────────────────────────────
    # Maximum age of a tick quote before it is considered stale.
    max_tick_age_seconds: int = 5

    # ── FVG minimum size (R8 🔶 PROPOSED_DEFAULT) ────────────────────────────
    # gap >= max(min_fvg_atr_factor × ATR(14), min_fvg_ticks × tick_size)
    min_fvg_atr_factor: float = 0.1        # PROPOSED_DEFAULT — not proven optimal
    min_fvg_ticks: int = 2                 # PROPOSED_DEFAULT — minimum 2 ticks

    # ── FVG maximum age (R9 🔶 PROPOSED_DEFAULT) ─────────────────────────────
    max_fvg_age_bars: int = 24             # PROPOSED_DEFAULT — completed H1 bars

    # ── Swing detection (R12 🔶 PROPOSED_DEFAULT) ─────────────────────────────
    pivot_left_bars: int = 2               # PROPOSED_DEFAULT
    pivot_right_bars: int = 2              # PROPOSED_DEFAULT

    # ── Gap exit mode (R26 🔶 PROPOSED_DEFAULT) ───────────────────────────────
    # "candle_close" = completed candle closes beyond FVG boundary
    gap_exit_mode: Literal["candle_close"] = "candle_close"

    # ── Setup expiry (R64, R65 🔶 PROPOSED_DEFAULT) ───────────────────────────
    max_setup_age_bars_after_sweep: int = 12   # PROPOSED_DEFAULT — bars after sweep

    # ── Late-entry guard (R33 🔶 PROPOSED_DEFAULT) ───────────────────────────
    late_entry_atr_factor: float = 0.1     # PROPOSED_DEFAULT — not proven optimal

    # ── ATR period ────────────────────────────────────────────────────────────
    atr_period: int = 14                   # used for R8, R33, R36


class RiskSettings(BaseSettings):
    """
    Risk and money-management configuration.

    APPROVED values are fixed per STRATEGY_SPEC.md v1.0.
    PROPOSED_DEFAULT values are configurable initial values.
    """
    model_config = SettingsConfigDict(env_prefix="RISK_")

    # ── Risk per trade (R44 ✅) ───────────────────────────────────────────────
    risk_pct_per_trade: float = 1.0        # APPROVED — 1% of equity, not configurable below 0.01

    # ── Minimum R:R (R40 ✅) ─────────────────────────────────────────────────
    min_reward_to_risk: float = 2.0        # APPROVED — minimum 2.0; cannot be set below 2.0

    # ── Daily trades (R50 ✅) ─────────────────────────────────────────────────
    max_daily_trades: int = 5              # APPROVED

    # ── Concurrent positions per symbol (R52 🔶 PROPOSED_DEFAULT) ────────────
    max_open_per_symbol: int = 1           # PROPOSED_DEFAULT

    # ── Daily loss limit (R54 🔶 PROPOSED_DEFAULT) ───────────────────────────
    daily_loss_pct: float = 3.0            # PROPOSED_DEFAULT — not claimed optimal

    # ── Consecutive-loss lockout (R58 🔶 PROPOSED_DEFAULT) ───────────────────
    # 0 = disabled
    max_consecutive_losses: int = 3        # PROPOSED_DEFAULT

    # ── Stop-loss buffer (R36 🔶 PROPOSED_DEFAULT) ───────────────────────────
    sl_buffer_atr_factor: float = 0.05     # PROPOSED_DEFAULT
    sl_buffer_min_ticks: int = 2           # PROPOSED_DEFAULT

    # ── Spread limits (R59 🔶 PROPOSED_DEFAULT — unconfigured until calibrated)
    # None = not yet calibrated; entries blocked per R60.
    # Must be set from actual Exness demo data before entries are permitted.
    # Keys are resolved broker symbol names (e.g. "XAUUSD", "XAUUSD.").
    max_spread_pips: dict[str, float | None] = {}

    # ── Session filters (R61 🔶 PROPOSED_DEFAULT) ─────────────────────────────
    # None = no additional restriction beyond broker availability.
    # UTC hour values: e.g. {"XAUUSD": {"start": 7, "end": 20}}
    session_filter: dict[str, dict | None] = {}

    # ── Stop retries (IMPL5 ✅) ───────────────────────────────────────────────
    max_sl_retry: int = 3

    # ── Dashboard heartbeat thresholds (IMPL9 🔶 PROPOSED_DEFAULT) ───────────
    heartbeat_online_secs: int = 15
    heartbeat_offline_secs: int = 60

    # ── Command TTL (IMPL10 ✅) ───────────────────────────────────────────────
    command_ttl_seconds: int = 30

    @field_validator("risk_pct_per_trade")
    @classmethod
    def clamp_risk(cls, v: float) -> float:
        if not (0.01 <= v <= 5.0):
            raise ValueError("risk_pct_per_trade must be between 0.01 and 5.0")
        return v

    @field_validator("min_reward_to_risk")
    @classmethod
    def enforce_min_rr(cls, v: float) -> float:
        if v < 2.0:
            raise ValueError(
                "min_reward_to_risk cannot be set below 2.0 (STRATEGY_SPEC.md R40)"
            )
        return v


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_")

    host: str = "127.0.0.1"
    port: int = 8000
    secret_key: str = Field(
        default="CHANGE_ME_IN_PRODUCTION_SET_API_SECRET_KEY_ENV_VAR",
        description="JWT signing secret — override with API_SECRET_KEY env var",
    )
    token_expire_minutes: int = 60
    algorithm: str = "HS256"

    @field_validator("secret_key")
    @classmethod
    def warn_placeholder_key(cls, v: str) -> str:
        if v == "CHANGE_ME_IN_PRODUCTION_SET_API_SECRET_KEY_ENV_VAR":
            import warnings
            warnings.warn(
                "API_SECRET_KEY is using an insecure placeholder. "
                "Set the API_SECRET_KEY environment variable before use.",
                stacklevel=2,
            )
        return v


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Execution mode (IMPL7 ✅) ─────────────────────────────────────────────
    # "paper" is the only permitted mode in this release.
    # "demo" requires explicit opt-in AND all required tests passing.
    # "live" is permanently blocked.
    execution_mode: Literal["paper", "demo"] = "paper"

    # ── Database ──────────────────────────────────────────────────────────────
    db_path: Path = DB_DIR / "fvg_trader.db"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_dir: Path = LOG_DIR

    # ── Sub-settings ──────────────────────────────────────────────────────────
    strategy: StrategySettings = Field(default_factory=StrategySettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    api: APISettings = Field(default_factory=APISettings)

    @field_validator("execution_mode")
    @classmethod
    def no_live_mode(cls, v: str) -> str:
        if v == "live":
            raise ValueError(
                "Live trading is disabled in this release. "
                "Set execution_mode='demo' only after all readiness gates pass."
            )
        return v


# ── Singleton ─────────────────────────────────────────────────────────────────
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reload_settings() -> AppSettings:
    """Force re-read of settings (useful in tests)."""
    global _settings
    _settings = AppSettings()
    return _settings
