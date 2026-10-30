# FINAL BOT AUDIT
**Date:** 2026-10-17  
**Auditor:** Kiro  
**Purpose:** Pre-frontend integration readiness check against STRATEGY_SPEC.md v1.0 and Developer Guide v1.0

---

## Summary Verdict

| Area | Status | Notes |
|---|---|---|
| Strategy logic (FVG, sweep, ref candle, trigger) | PASS | Implemented in `src/strategy/strategy_core.py` |
| State machine (12 stages, persistence) | PASS | `src/state/state_machine.py` — all transitions persisted |
| Engine loop (auto-monitoring) | PARTIAL | Loop exists in `src/engine/trading_engine.py`; no VPS service wrapper |
| Risk engine (1%, 1:2, 5/day, locks) | PASS | `src/risk/engine.py` |
| Paper execution isolation | PASS | `src/execution/paper_executor.py` — no MT5 import by design |
| SQLite persistence + restart recovery | PASS | WAL mode, `DailyRiskState` survives restart |
| MT5 integration | PARTIAL | Adapter complete; live connection untested (no VPS) |
| Signal output fields | PARTIAL | Setup/decision log exist; signal-specific output schema (§4.3) not yet a separate table |
| Supabase bridge | **FAIL** | No Supabase client, no heartbeat writer, no event publisher anywhere in codebase |
| Frontend | **FAIL** | `frontend/` is entirely empty |
| Tests | PARTIAL | 12 test files written; cannot run (venv/pip blocked in IDE) |
| Security | PARTIAL | JWT auth in FastAPI; API_SECRET_KEY placeholder warning; no Supabase RLS defined |
| VPS / auto-restart | **FAIL** | No systemd unit, watchdog, or Windows service wrapper |
| Notifications (Telegram / push) | **FAIL** | Not implemented |

---

## Detailed Findings

### 1. Strategy Rules

| Requirement | Status | Evidence |
|---|---|---|
| XAUUSD + BTCUSD, H1 | PASS | `StrategySettings.symbols`, `FVGDetector(timeframe="H1")` |
| 3-candle FVG (C1.high < C3.low / C1.low > C3.high) | PASS | `strategy_core.py` R5/R6 |
| FVG confirmed after C3 close only | PASS | R7 enforced, live-bar stripped in `MT5DataAdapter` |
| Min FVG size: max(0.1×ATR14, 2 ticks) | PASS | R8 — `_min_size()` returns tuple, floor of 1 tick enforced |
| FVG max age: 24 bars | PASS | R9 `is_age_expired()` |
| Liquidity sweep: wick + close-back (strict) | PASS | R15/R16 `LiquiditySweepDetector` |
| Sweep must post-date FVG C3 | PASS | R17 `candle.time > fvg.c3_time` |
| Reference candle: most recent qualifying, frozen at gap exit | PASS | R21–R24 `ReferenceCandleSelector` |
| Gap exit: candle close beyond FVG boundary (candle_close mode) | PASS | R26 `GapExitChecker` |
| Entry trigger: candle close beyond ref high/low | PASS | R29 `EntryTriggerChecker.check_candle_close()` |
| Tick-break mode with stale-tick rejection | PASS | R30/R31 |
| SL: sweep extreme ± max(2 ticks, 0.05×ATR14) | PASS | R35/R36 `StopLossCalculator` |
| TP: entry ± 2×SL distance, conservative rounding | PASS | R40–R42 `TakeProfitCalculator` |
| No trailing stops, partial TPs, break-even | PASS | R43 — not implemented |

### 2. Engine Monitoring

| Requirement | Status | Evidence |
|---|---|---|
| Auto-advance setups without user prompt | PASS | `evaluate_symbol()` advances state machine per candle |
| Expiry + invalidation checked each evaluation | PASS | `SetupExpiryChecker` called before state advance |
| Restart recovery: rehydrate active setups from DB | PASS | `SetupRepository.get_active()`, reconciliation in `run_engine()` |
| Continuous scheduler | PARTIAL | APScheduler 60s interval in `main.py`; needs VPS service |
| Heartbeat to Supabase every 10s | **FAIL** | Not implemented |

### 3. Signal Output (§4.3)

| Field Required | Status | Notes |
|---|---|---|
| id, created_at | PASS | `setup.id`, `setup.created_at` in DB |
| instrument, timeframe, direction | PASS | Stored in `Setup` row |
| entry, SL, TP | PASS | `proposed_entry`, `proposed_sl`, `proposed_tp` |
| ATR value used for SL | PARTIAL | `fvg_atr_at_detection` stored; SL buffer ATR not separately persisted |
| R:R ratio | PASS | `estimated_rr` |
| Confidence / quality grade | **FAIL** | No grade (A/B/C) implemented |
| Suggested lot size | PASS | `proposed_volume` |
| Human-readable reason | PARTIAL | `rejection_reason` and `decision_reason` in `DecisionLog` |
| Session tag (Asia/London/NY) | **FAIL** | No session classification |
| Strategy version | PASS | `spec_version` in all ORM rows |
| Status (new/taken/skipped/expired/hit TP/SL) | PARTIAL | State machine covers most; "hit TP/hit SL" not separately tracked |
| expires_at | **FAIL** | No explicit expiry timestamp on signal |

### 4. Risk

| Requirement | Status | Evidence |
|---|---|---|
| 1% risk per trade | PASS | `RiskSettings.risk_pct_per_trade=1.0`, enforced in `calculate_size()` |
| Min 1:2 R:R | PASS | `min_reward_to_risk=2.0`, validator blocks < 2.0 |
| Max 5 trades/day | PASS | `max_daily_trades=5`, `DailyRiskState` persisted |
| Daily loss limit 3% | PASS (PROPOSED) | `daily_loss_pct=3.0` — configurable |
| Consecutive-loss lockout | PASS (PROPOSED) | 3 consecutive losses → lock |
| Spread limit per symbol | PASS | Dict-based, blocks when unconfigured |
| SL on every order | PASS | R39/R84 — paper confirms SL; demo would verify |
| News lockout (manual) | PASS | `set_news_lock()` API endpoint exists |
| Live trading disabled | PASS | Validator raises on `execution_mode="live"` |

### 5. Execution Safety

| Requirement | Status | Evidence |
|---|---|---|
| Paper mode cannot call MT5 order API | PASS | `PaperExecutor` does not import MetaTrader5 |
| Idempotent order IDs | PASS | `order_client_id(setup_id, attempt)` — SHA-256 deterministic |
| Duplicate order prevention | PASS | Client order ID persisted before submission |
| Broker SL confirmation required | PASS | `sl_confirmed_by_broker` field; R39 alert on failure |
| Timed-out order reconciliation | PASS | R76 documented; engine checks before retry |
| No fabricated prices/balances | PASS | Engine refuses to act with `equity=None` |

### 6. Persistence

| Requirement | Status | Evidence |
|---|---|---|
| SQLite WAL mode | PASS | `PRAGMA journal_mode=WAL` in `database.py` |
| Daily limits survive restart | PASS | `DailyRiskState` in DB, lock flags persisted |
| Setup states survive restart | PASS | `SetupRepository.get_active()` re-loads from DB |
| Order history | PASS | `Order` ORM with all fill fields |
| Decision log written before order | PASS | `_write_decision_log()` called before `submit_order()` |
| All transitions audited | PASS | `SetupTransition` immutable log |

### 7. Supabase Bridge — CRITICAL BLOCKER

**Status: FAIL**

Nothing in the codebase writes to Supabase. There is no:
- Heartbeat publisher
- Equity/position state publisher  
- Signal event publisher
- Command poller
- `supabase-py` in `requirements.txt`
- Any Supabase table schema or migration

**This is the primary blocker for frontend integration.** The frontend reads from Supabase; if the engine never writes to it, the dashboard has no live data.

**Required work:** Build a `src/supabase/publisher.py` bridge that:
1. Writes heartbeat rows every 10 seconds
2. Publishes signals, state changes, fills, and errors as events
3. Polls a `commands` table for PAUSE/RESUME/NEWS_LOCK instructions
4. Has `supabase-py` added to requirements

### 8. Frontend — FAIL

`frontend/` contains only empty directories. No Next.js app, no `package.json`, no components, no pages.

**This is the primary deliverable of Task 2.**

### 9. Security

| Item | Status | Notes |
|---|---|---|
| JWT auth on FastAPI routes | PASS | `python-jose`, `passlib` used |
| API_SECRET_KEY placeholder warning | PASS | Validator warns at startup |
| No passwords in DB | PASS | `AccountProfile` stores no credentials |
| Supabase RLS | **FAIL** | No schema defined yet |
| Two-factor for owner | **FAIL** | Not implemented |
| No credentials in frontend | N/A | Frontend not built yet |

### 10. VPS / Auto-restart

**Status: FAIL**  
No systemd service file, Windows service wrapper, or watchdog script. `main.py` runs manually only.

---

## Blockers Before Frontend Integration

| # | Blocker | Severity | Action |
|---|---|---|---|
| B1 | No Supabase bridge | Critical | Build `src/supabase/publisher.py` + Supabase schema |
| B2 | No Next.js frontend | Critical | Build full frontend (Task 2) |
| B3 | No signal `expires_at` field | Medium | Add to `Setup` ORM or derive from age |
| B4 | No session classification | Medium | Add session tagger to decision log |
| B5 | No quality/confidence grade | Low | Add grade computation to signal output |
| B6 | No VPS service wrapper | Low (for dev) | Document; add systemd unit |

---

## Files That Are Complete and Must Not Be Modified

- `src/strategy/strategy_core.py`
- `src/state/state_machine.py`  
- `src/state/models.py`
- `src/risk/engine.py`
- `src/execution/paper_executor.py`
- `src/data/candle.py`, `indicators.py`, `market_data_adapter.py`
- `src/utils/` (all)
- `src/journal/models.py`
- `src/config/settings.py`

---

*End of audit. Proceeding to Task 2 — frontend build.*
