# AUDIT REPORT
**Project:** XAUUSD / BTCUSD FVG Liquidity-Sweep Trader
**Audit date:** 2026-10-17
**Auditor:** Kiro
**Phase 0 status:** ✅ Complete
**Phase 1 status:** ✅ Complete — STRATEGY_SPEC.md v1.0 written with all owner-approved rules
**Phase 2 status:** 🔄 In progress — deterministic strategy core implementation

---

## 1. Repository Architecture and Important File Paths

```
XAUUSD/
├── pyproject.toml              Project metadata, pytest config, coverage config
├── requirements.txt            All Python dependencies (pinned versions)
├── src/
│   ├── config/
│   │   └── settings.py         Pydantic-settings config (StrategySettings, RiskSettings,
│   │                            APISettings, AppSettings). Singleton via get_settings().
│   ├── data/
│   │   ├── candle.py           Immutable frozen Candle dataclass (OHLCV + symbol + timeframe)
│   │   └── market_data_adapter.py  MT5DataAdapter (live), HistoricalDataAdapter (backtest),
│   │                                SymbolInfo, MarketDataProtocol interface
│   ├── strategy/
│   │   └── fvg_detector.py     FVGDetector, SwingDetector, LiquiditySweepDetector,
│   │                            ReferenceCandelSelector, EntryTriggerChecker, and data classes
│   │                            FVG, Swing, LiquiditySweep, ReferenceCandle
│   ├── state/
│   │   ├── models.py           SQLAlchemy ORM: Setup, SetupTransition, Order
│   │   │                       SetupState enum (15 states), SetupDirection enum
│   │   └── state_machine.py    SetupStateMachine (one per setup), SetupRepository
│   ├── risk/
│   │   └── engine.py           RiskEngine: position sizing, daily-limit enforcement,
│   │                            lockout management. SizingResult, RiskCheckResult.
│   ├── journal/
│   │   └── models.py           JournalEntry, DailyRiskState ORM models
│   ├── execution/
│   │   └── paper_executor.py   PaperExecutor, PaperLedger, PaperPosition (no MT5 import)
│   ├── api/
│   │   ├── models.py           AccountProfile, APIUser ORM models
│   │   ├── __init__.py         EMPTY
│   │   └── routers/__init__.py EMPTY
│   ├── engine/
│   │   └── __init__.py         EMPTY — no trading loop implemented
│   ├── backtest/
│   │   └── __init__.py         EMPTY — no backtest runner implemented
│   ├── desktop/
│   │   ├── __init__.py         EMPTY
│   │   ├── pages/              EMPTY directory
│   │   └── widgets/            EMPTY directory
│   └── utils/
│       ├── database.py         SQLAlchemy engine (SQLite + WAL), session factory,
│       │                        Base, init_db(), reset_db_for_tests()
│       ├── ids.py              setup_id() (SHA-256 deterministic), order_client_id()
│       └── logging_config.py   structlog configuration, get_logger()
├── tests/
│   ├── unit/                   EMPTY (no test files)
│   ├── integration/            EMPTY (no test files)
│   └── fixtures/               EMPTY (no fixture files)
├── frontend/
│   └── src/
│       ├── api/                EMPTY
│       ├── components/         EMPTY
│       ├── hooks/              EMPTY
│       └── pages/              EMPTY
└── data/
    ├── db/                     EMPTY — no database file yet
    ├── logs/                   EMPTY
    └── exports/                EMPTY
```

**No files outside the above inventory exist in the repository.** The `docs/` directory is empty. There are no `.env` files, YAML configs, migration scripts, Expert Advisors, or deployment manifests.

---

## 2. Working Components and Evidence

The following components have well-formed source code and are plausibly functional (but untested — see Section 4):

| Component | File | Evidence of Implementation |
|---|---|---|
| `Candle` dataclass | `src/data/candle.py` | Immutable, validates OHLCV invariants, no external deps |
| `MT5DataAdapter` | `src/data/market_data_adapter.py` | Full connect/disconnect/get_candles/get_tick/get_account_info. Strips live bar. |
| `HistoricalDataAdapter` | `src/data/market_data_adapter.py` | Offline adapter for backtests. Reasonable hardcoded symbol specs. |
| `SymbolInfo` | `src/data/market_data_adapter.py` | All MT5 symbol fields captured |
| `FVGDetector` | `src/strategy/fvg_detector.py` | Detects bullish/bearish FVGs on 3-candle triples. Min-gap filter. |
| `SwingDetector` | `src/strategy/fvg_detector.py` | Pivot detection with configurable left/right bars, no look-ahead |
| `LiquiditySweepDetector` | `src/strategy/fvg_detector.py` | Wick-through/close-back pattern on confirmed swings |
| `ReferenceCandelSelector` | `src/strategy/fvg_detector.py` | Most-recent qualifying candle in FVG. Note: class name is misspelled (`Candel`) |
| `EntryTriggerChecker` | `src/strategy/fvg_detector.py` | Candle-close and tick-break modes |
| `SetupStateMachine` | `src/state/state_machine.py` | 15-state machine, every transition written to DB |
| `SetupRepository` | `src/state/state_machine.py` | CRUD, active-setup query, non-terminal filter |
| `RiskEngine` | `src/risk/engine.py` | Pip-value sizing, daily limits, consecutive-loss lockout, spread check |
| `PaperExecutor` | `src/execution/paper_executor.py` | Simulated fills, SL/TP checks — no MT5 import (architecturally enforced) |
| `DatabaseUtils` | `src/utils/database.py` | SQLite engine, WAL mode, session factory, init_db() |
| `Settings` | `src/config/settings.py` | Pydantic-settings, live-mode blocked at validator |
| `StructuredLogging` | `src/utils/logging_config.py` | structlog, JSON or console renderer |
| `IDs` | `src/utils/ids.py` | Deterministic SHA-256 setup IDs, idempotent order client IDs |

---

## 3. Legacy Strategy Components and Dependencies

### Classification

| Component | File | Classification | Reason |
|---|---|---|---|
| `FVGDetector` | `src/strategy/fvg_detector.py` | **LEGACY_STRATEGY** | Implements the old 3-candle FVG detection rules. Whether the new strategy uses the same definition is an open question. |
| `SwingDetector` | `src/strategy/fvg_detector.py` | **LEGACY_STRATEGY** | Old pivot parameters (5L/5R). New strategy swing definition not yet confirmed. |
| `LiquiditySweepDetector` | `src/strategy/fvg_detector.py` | **LEGACY_STRATEGY** | Old sweep definition (wick-through/close-back). New strategy sweep rules not yet approved. |
| `ReferenceCandelSelector` | `src/strategy/fvg_detector.py` | **LEGACY_STRATEGY** | Old retracement/reference-candle logic. Must not control new strategy. |
| `EntryTriggerChecker` | `src/strategy/fvg_detector.py` | **LEGACY_STRATEGY** | Old trigger mode (candle-close vs tick-break). New strategy entry rules not yet approved. |
| `SetupState` enum | `src/state/models.py` | **SHARED_COMPONENT** | State names partly describe the old flow. New strategy may need a different state sequence. |
| `SetupStateMachine` | `src/state/state_machine.py` | **SHARED_COMPONENT** | The infrastructure (DB persistence, transition log) is reusable. The specific transition sequence reflects the old strategy flow and must be reviewed. |
| `StrategySettings` | `src/config/settings.py` | **LEGACY_STRATEGY** | Contains old parameters: `min_fvg_pips`, `max_fvg_age_bars`, `pivot_left_bars`, `pivot_right_bars`, `entry_trigger_mode`, `retracement_tolerance_pips`, `max_setup_age_bars`. None approved for new strategy. |
| `RiskSettings` | `src/config/settings.py` | **LEGACY_STRATEGY** (values) / **SHARED_COMPONENT** (structure) | The risk limits (`risk_pct_per_trade=1%`, `min_reward_to_risk=2.0`, `max_daily_trades=5`, `daily_loss_pct=3%`, `sl_buffer_pips=2`, spread limits, `max_consecutive_losses=3`) are old values not yet approved for new strategy. The Pydantic structure is reusable. |
| `RiskEngine` | `src/risk/engine.py` | **SHARED_COMPONENT** | Position-sizing math, daily-limit enforcement, and lockout logic are reusable infrastructure. The TP calculation (`entry ± sl_distance × min_rr`) must be reviewed against new strategy exit rules. |
| `PaperExecutor` | `src/execution/paper_executor.py` | **REUSABLE_INFRASTRUCTURE** | Architecturally clean, no MT5, paper-only. The fill logic (immediate market fill at ask/bid) is reasonable but should be reviewed against the new strategy's entry mechanics. |
| `Candle` dataclass | `src/data/candle.py` | **REUSABLE_INFRASTRUCTURE** | Pure value object, no strategy logic |
| `MT5DataAdapter` | `src/data/market_data_adapter.py` | **REUSABLE_INFRASTRUCTURE** | MT5 connection, candle fetching, live-bar stripping — not strategy-specific |
| `HistoricalDataAdapter` | `src/data/market_data_adapter.py` | **REUSABLE_INFRASTRUCTURE** | Offline candle source for backtests |
| `setup_id / order_client_id` | `src/utils/ids.py` | **REUSABLE_INFRASTRUCTURE** | Deterministic IDs, no strategy logic |
| `DatabaseUtils` | `src/utils/database.py` | **REUSABLE_INFRASTRUCTURE** | Pure infrastructure |
| `StructuredLogging` | `src/utils/logging_config.py` | **REUSABLE_INFRASTRUCTURE** | Pure infrastructure |
| `JournalEntry / DailyRiskState` | `src/journal/models.py` | **REUSABLE_INFRASTRUCTURE** | Good audit trail and risk-lock schema |
| `AccountProfile / APIUser` | `src/api/models.py` | **REUSABLE_INFRASTRUCTURE** | Account management, no passwords stored |
| `Setup / SetupTransition / Order` ORM | `src/state/models.py` | **SHARED_COMPONENT** | Schema is generally reusable; `proposed_sl`, `trigger_level`, and field semantics may need modification for new strategy |

### Isolation recommendation (for approval, not yet enacted)

The safest isolation approach is to create a new `src/strategy/` module file (e.g., `new_strategy.py`) for all new strategy rules, leaving the legacy `fvg_detector.py` untouched until tests confirm the new module covers all required cases. The state machine, risk engine, and paper executor can be retained but configured with approved parameters only.

---

## 4. Confirmed Defects, Suspected Defects, and Missing Tests

### 4a. Confirmed facts (directly verifiable from source code)

| # | Finding | Severity | File | Detail |
|---|---|---|---|---|
| CF-1 | **No trading loop implemented** | Critical | `src/engine/__init__.py` | The engine package is empty. There is no main loop, scheduler, or candle-evaluation cycle. The system cannot trade at all in its current state. |
| CF-2 | **No FastAPI application or routes implemented** | High | `src/api/__init__.py`, `src/api/routers/__init__.py` | The API package and routers are empty. No HTTP endpoints exist. |
| CF-3 | **No desktop UI implemented** | High | `src/desktop/` | All desktop directories and `__init__.py` files are empty. |
| CF-4 | **No frontend implementation** | High | `frontend/src/` | All frontend source directories (api, components, hooks, pages) are empty. |
| CF-5 | **No tests of any kind** | High | `tests/unit/`, `tests/integration/`, `tests/fixtures/` | All test directories contain only empty `__init__.py` files. pytest is configured but there is nothing to run. |
| CF-6 | **No database file exists** | Medium | `data/db/` | `init_db()` has never been called. There is no SQLite file and no Alembic migration history. |
| CF-7 | **No backtest engine** | High | `src/backtest/__init__.py` | Empty. No candle-by-candle replay, no backtest runner, no result reporter. |
| CF-8 | **Typo in class name** | Low | `src/strategy/fvg_detector.py` line ~145 | `ReferenceCandelSelector` should be `ReferenceCandleSelector`. Not a runtime bug (the class works) but will cause confusion. Do not rename until legacy code is replaced. |
| CF-9 | **`pyproject.toml` project name/description reflects old strategy** | Low | `pyproject.toml` | Name is `xauusd-fvg-trader`, description mentions "H1 Fair Value Gap trading system for XAUUSD and BTCUSD". Should be updated once new strategy is approved. |
| CF-10 | **BTCUSD listed as a supported symbol** | Medium | `src/config/settings.py`, `pyproject.toml` | The current settings default includes `BTCUSD`. Whether the new strategy trades BTCUSD is unconfirmed. |
| CF-11 | **`execution_mode` blocks "live" but not "demo" with no safeguard** | Medium | `src/config/settings.py` | The validator blocks only `"live"`. If `execution_mode="demo"` is set, a future MT5 executor could submit real orders to a demo account. There is no demo-account order-submission code yet, but the gap should be noted before one is built. |
| CF-12 | **`HistoricalDataAdapter` hardcodes symbol spec values** | Low | `src/data/market_data_adapter.py` | Default `tick_value=1.0` for XAUUSD is not sourced from the broker. This could produce incorrect position sizes in backtest mode. Must be validated against actual Exness contract specs before backtest results are trusted. |
| CF-13 | **No `.env` file, no config file, no migration scripts** | High | — | The system cannot be started without manual configuration. `API_SECRET_KEY` default is a placeholder string. `AppSettings` reads `.env` but no such file exists. |
| CF-14 | **No `pyproject.toml` entry point or `main.py`** | High | — | There is no application entry point. It is unknown how the system is intended to be started. |
| CF-15 | **No Supabase integration** | High | — | requirements.txt does not include `supabase-py` or any Supabase client. The frontend directory is empty. Despite being in the project brief, Supabase is not present. |
| CF-16 | **`state_machine.py` `confirm_gap_exit` transitions to `WAITING_FOR_GAP_EXIT` but `confirm_ready_to_trigger` transitions FROM `WAITING_FOR_GAP_EXIT`** | Medium | `src/state/state_machine.py` | The state naming is confusing/backwards. `confirm_gap_exit` sets state to `WAITING_FOR_GAP_EXIT` — this means "we have exited the gap and are now waiting to trigger". `confirm_ready_to_trigger` then moves from `WAITING_FOR_GAP_EXIT` to `WAITING_FOR_TRIGGER`. These two states describe the same condition; the model may represent an unnecessary split. This is a logic-flow smell, not necessarily a bug, but warrants review. |

### 4b. Suspected defects (not confirmed — would require test reproduction)

| # | Suspicion | Reason for suspicion |
|---|---|---|
| SD-1 | `RiskEngine.calculate_size()` may produce incorrect pip values for Exness XAUUSD | `pip_value_per_lot = (tick_value / tick_size) * point`. For XAUUSD on Exness the actual USD pip value per lot depends on account currency and contract size. The formula is plausible but has not been validated against real Exness MT5 symbol specs. |
| SD-2 | `ReferenceCandelSelector.find_reference_candle()` may select the wrong candle when multiple candles are in the FVG | The selector picks the most recent intersecting candle. Depending on the new strategy's definition of the reference candle, this may or may not be correct. |
| SD-3 | `DailyRiskState` `start_equity` may remain `None` if `get_or_create_daily_state()` is called with `start_equity=None` on a new day | In `record_new_entry()` and `record_closed_trade()`, `start_equity=None` is passed. If no earlier call set `start_equity`, the daily loss check `if row.start_equity and row.start_equity > 0` silently skips the loss limit. |
| SD-4 | Setup IDs could theoretically collide if two symbols produce the same `{symbol}|{direction}|{time}` string | Practically impossible but the truncation to 16 hex characters means `setup_id()` is not collision-proof for large-scale backtests. |

---

## 5. Security and Operational Risks

| # | Risk | Severity | Notes |
|---|---|---|---|
| SR-1 | `API_SECRET_KEY` has an insecure placeholder default | High | "CHANGE_ME_IN_PRODUCTION_SET_API_SECRET_KEY_ENV_VAR" will be accepted as a valid JWT signing key if no env var is set. Any token signed with this key could authenticate to the API. |
| SR-2 | No `.env` file and no secrets management guidance documented | High | There is no `.env.example` or documented procedure for setting secrets safely on this Windows machine. |
| SR-3 | `execution_mode="demo"` allows real-account order submission on a demo account | Medium | Once a real MT5 executor is built, a misconfiguration here could send orders. Should require an explicit per-run flag, not just a settings value. |
| SR-4 | No rate limiting, authentication middleware, or CORS configuration on the (currently empty) FastAPI app | Medium | Will need to be addressed before any API endpoint is exposed to the network. |
| SR-5 | SQLite WAL mode does not prevent data loss on hard power-off | Low | Acceptable for development; would need consideration for a production deployment. |
| SR-6 | `keyring==25.2.1` is in requirements but there is no code using it | Low | Dead dependency, or intended future use. Either way, should be confirmed. |

---

## 6. Proposed Implementation Sequence (for approval)

This is a suggestion only. No work should begin until the strategy spec is approved.

1. **Approve STRATEGY_SPEC.md** — resolve all open questions.  
2. **Write unit tests for `Candle`, `FVGDetector`, `SwingDetector`, `LiquiditySweepDetector`** — establish baseline coverage before any modification.  
3. **Implement new strategy rules** in isolated `src/strategy/new_strategy.py` (or equivalent), leaving legacy `fvg_detector.py` intact.  
4. **Validate position sizing** against real Exness XAUUSD symbol spec (MT5 live connection needed).  
5. **Build the trading loop** in `src/engine/`.  
6. **Build FastAPI routes** for engine-to-dashboard communication.  
7. **Build the Next.js dashboard** (Supabase integration or direct API, as approved).  
8. **Paper trading dry run** — full cycle from FVG detection to PaperExecutor close, all logged.  
9. **Backtest engine** — candle-by-candle replay with real Exness historical data.  
10. **Demo account testing** — only after readiness gates pass.

---

## 7. Files That Should Be Preserved

The following files must not be deleted without explicit approval:

| File | Reason |
|---|---|
| `src/data/candle.py` | Core data structure, no strategy content |
| `src/data/market_data_adapter.py` | MT5 connectivity, live-bar stripping — reusable |
| `src/utils/database.py` | SQLite engine + WAL + session factory |
| `src/utils/ids.py` | Deterministic IDs |
| `src/utils/logging_config.py` | Structured logging |
| `src/journal/models.py` | Audit trail and risk lock schema |
| `src/api/models.py` | Account profile schema |
| `src/execution/paper_executor.py` | Paper execution — no live trading risk |
| `src/risk/engine.py` | Sizing and daily-limit infrastructure (parameters pending approval) |
| `src/state/models.py` | ORM models (schema may need revision) |
| `src/state/state_machine.py` | Transition infrastructure (flow may need revision) |
| `pyproject.toml` | Build and test configuration |
| `requirements.txt` | Pinned dependencies |

The following files are legacy strategy logic and should **not** be modified yet but are candidates for eventual replacement:

| File | Reason |
|---|---|
| `src/strategy/fvg_detector.py` | Contains old entry, sweep, reference-candle, and trigger rules |
| `src/config/settings.py` (StrategySettings, RiskSettings values) | Old parameter values — retain structure, replace values after approval |

---

## 8. Decisions Requiring Owner Approval

| # | Decision |
|---|---|
| D-1 | What are the full trading rules for the new strategy? (See STRATEGY_SPEC.md open questions) |
| D-2 | Should BTCUSD remain a supported symbol, or is this a XAUUSD-only system? |
| D-3 | Which state names in `SetupState` should be retained, renamed, or removed for the new strategy? |
| D-4 | Are the existing `RiskSettings` default values (`risk_pct=1%`, `daily_loss=3%`, `max_daily_trades=5`, `min_rr=2.0`) approved for the new strategy, or must they be replaced? |
| D-5 | Is the `execution_mode="demo"` path intended to be built in this phase, or is paper-only sufficient for now? |
| D-6 | Is Supabase still the intended backend, or has that decision changed? (Nothing in the repo points to Supabase.) |
| D-7 | Is PySide6 desktop UI still required, or has the dashboard pivoted entirely to Next.js/web? |
| D-8 | Should `ReferenceCandelSelector` (misspelled) be renamed now or only when the new strategy module is written? |

---

*End of Audit Report*
