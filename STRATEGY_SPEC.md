# STRATEGY SPECIFICATION
**Project:** XAUUSD / BTCUSD FVG Liquidity-Sweep Trader
**Version:** 1.2
**Approval status:** ✅ OWNER-APPROVED
- v1.0 rules (2026-10-17)
- v1.1 break-even + ATR trailing stop (R89–R96, 2026-10-17)
- v1.2 Market Clarity Engine, multi-timeframe analysis, two-position execution, setup grading, M15 entry trigger (R97–R130, 2026-10-17)
**Spec hash:** NOT YET ESTABLISHED
**Last updated:** 2026-10-17

### Changelog v1.1 → v1.2
- R43 amended further: two-position execution is now approved under R110–R118
- R97–R130: new rules covering H4 trend filter, M15 entry trigger, Market Clarity Engine, setup grading, structural TP detection, two-position execution, break-even management, and backtesting modes

---

> **Key:**
> - ✅ APPROVED — owner explicitly confirmed in Part 1 message
> - 🔶 PROPOSED DEFAULT — owner-supplied initial value that is configurable; not claimed optimal
> - ❌ PROHIBITED — explicitly listed as a rule that must never be used

> **Implementation safety:** No rule marked 🔶 PROPOSED DEFAULT may be silently changed. Any change requires a new spec version and owner re-approval before it affects live or demo execution.

> **No profitability is claimed or implied by any value in this specification.**

---

## 1. Rule Index

| Rule ID | Topic | Status | Configurable |
|---|---|---|---|
| R1 | Instruments | ✅ | No |
| R2 | Timeframe | ✅ | No |
| R3 | Candle data requirement | ✅ | No |
| R4 | Symbol discovery | ✅ | No |
| R5 | FVG definition — bullish | ✅ | No |
| R6 | FVG definition — bearish | ✅ | No |
| R7 | FVG confirmation timing | ✅ | No |
| R8 | FVG minimum size | 🔶 | Yes — per symbol |
| R9 | FVG maximum age | 🔶 | Yes |
| R10 | FVG stored fields | ✅ | No |
| R11 | FVG full traversal invalidation | ✅ | No |
| R12 | Swing detection method | 🔶 | Yes — left/right bars |
| R13 | Swing tie-handling | ✅ | No |
| R14 | Swing confirmation timing | ✅ | No |
| R15 | Bullish liquidity sweep definition | ✅ | No |
| R16 | Bearish liquidity sweep definition | ✅ | No |
| R17 | Sweep ordering (FVG must precede sweep) | ✅ | No |
| R18 | Sweep stored fields | ✅ | No |
| R19 | Setup sequence — required order | ✅ | No |
| R20 | Out-of-order stage rejection | ✅ | No |
| R21 | Retracement reference candle — bullish | ✅ | No |
| R22 | Retracement reference candle — bearish | ✅ | No |
| R23 | Reference candle update rule | ✅ | No |
| R24 | Reference candle freeze condition | ✅ | No |
| R25 | Reference candle rejection | ✅ | No |
| R26 | Gap-exit condition | 🔶 | Yes |
| R27 | Entry trigger — bullish | ✅ | No |
| R28 | Entry trigger — bearish | ✅ | No |
| R29 | Entry trigger mode — CANDLE_CLOSE | ✅ | Default |
| R30 | Entry trigger mode — TICK_BREAK | ✅ | Alternative |
| R31 | Tick-break quote validity | ✅ | No |
| R32 | Entry pre-submission checklist | ✅ | No |
| R33 | Late-entry guard | 🔶 | Yes |
| R34 | Signal-only mode | ✅ | No |
| R35 | Stop-loss structural reference | ✅ | No |
| R36 | Stop-loss buffer | 🔶 | Yes |
| R37 | Stop-loss broker constraints | ✅ | No |
| R38 | Stop-loss post-entry widening prohibition | ✅ | No |
| R39 | Stop-loss broker confirmation requirement | ✅ | No |
| R40 | Take-profit minimum R:R | ✅ | No |
| R41 | Take-profit calculation | ✅ | No |
| R42 | Take-profit rounding | ✅ | No |
| R43 | Disabled exit features | ❌ | N/A |
| R44 | Risk per trade | ✅ | No |
| R45 | Position sizing method | ✅ | No |
| R46 | Volume rounding | ✅ | No |
| R47 | Minimum volume rejection | ✅ | No |
| R48 | Instrument-specific sizing | ✅ | No |
| R49 | Loss-recovery sizing prohibition | ❌ | N/A |
| R50 | Maximum entries per day | ✅ | No |
| R51 | Daily entry counter scope | ✅ | No |
| R52 | Maximum concurrent positions per symbol | 🔶 | Yes |
| R53 | Manual position handling | ✅ | No |
| R54 | Daily loss limit | 🔶 | Yes |
| R55 | Daily loss P&L method | ✅ | No |
| R56 | Daily loss lock persistence | ✅ | No |
| R57 | Daily loss alert and resume | ✅ | No |
| R58 | Consecutive-loss lockout | 🔶 | Yes |
| R59 | Spread limit | 🔶 | Yes — per symbol |
| R60 | Spread limit unconfigured behaviour | ✅ | No |
| R61 | Session filter | 🔶 | Yes — per symbol |
| R62 | News lockout | ✅ | No |
| R63 | News lockout scope | ✅ | No |
| R64 | Setup expiry — post-sweep | 🔶 | Yes |
| R65 | Setup expiry — FVG age | 🔶 | Yes |
| R66 | Setup invalidation conditions | ✅ | No |
| R67 | Bullish setup invalidation event | ✅ | No |
| R68 | Bearish setup invalidation event | ✅ | No |
| R69 | No-resurrection rule | ✅ | No |
| R70 | Re-entry prohibition (same setup) | ✅ | No |
| R71 | New setup re-entry requirement | ✅ | No |
| R72 | Opposite-signal handling | ✅ | No |
| R73 | Persistence scope | ✅ | No |
| R74 | Restart reconciliation sequence | ✅ | No |
| R75 | Broker/local disagreement handling | ✅ | No |
| R76 | Timed-out order handling | ✅ | No |
| R77–R88 | Prohibited rules | ❌ | N/A |
| IMPL1 | Deterministic engine interface | ✅ | No |
| IMPL2 | Decision log fields | ✅ | No |
| IMPL3 | State machine states | ✅ | No |
| IMPL4 | Order idempotency | ✅ | No |
| IMPL5 | MT5 error handling | ✅ | No |
| IMPL6 | Bot pause safety | ✅ | No |
| IMPL7 | Execution mode isolation | ✅ | No |
| IMPL8 | Engine/dashboard communication | ✅ | No |
| IMPL9 | Dashboard status thresholds | 🔶 | Yes |
| IMPL10 | Command lifecycle | ✅ | No |
| IMPL11 | Credential storage | ✅ | No |

---

## 2. Rules (Full Detail)

---

### R1 — Instruments
**Status:** ✅ APPROVED

**Rule:** The strategy trades exactly two instruments: XAUUSD (gold) and BTCUSD (Bitcoin). Both are traded on the same timeframe and use the same strategy sequence. They never share position-sizing parameters, pip values, lot sizes, or trading-hour assumptions.

**Required inputs:** Approved symbol list `["XAUUSD", "BTCUSD"]`
**Condition:** Signal is only generated for a symbol on this list
**Expected outcome:** Signals on any other symbol are silently discarded with a log entry
**Rejection reason:** `"Symbol {sym} not in approved instrument list"`

**Actual broker symbol names** must be verified via `MT5DataAdapter.get_available_symbols()` at startup. Exness may append suffixes (e.g. `XAUUSDm`, `XAUUSD.`). The engine must attempt exact match first, then suffix-tolerant match, and log the resolved name.

**Test requirement:** T-R1-1: Engine rejects signal for unapproved symbol. T-R1-2: Suffix resolution returns correct symbol when exact name absent.

---

### R2 — Timeframe
**Status:** ✅ APPROVED

**Rule:** All FVG detection, swing detection, sweep detection, reference-candle selection, gap-exit, and trigger evaluation use the H1 (one-hour) timeframe for both XAUUSD and BTCUSD.

**Required inputs:** Timeframe string `"H1"`
**Condition:** All candle requests use `timeframe="H1"`
**Expected outcome:** No other timeframe is used for strategy decisions

**Test requirement:** T-R2-1: Engine raises an error if instantiated with any timeframe other than H1.

---

### R3 — Candle data requirement
**Status:** ✅ APPROVED

**Rule:** Only completed (closed) H1 candles are used for all strategy decisions. The live (forming/current) bar is never used for FVG detection, swing detection, reference-candle selection, gap-exit evaluation, or trigger evaluation.

Live ticks are permitted exclusively for the TICK_BREAK entry trigger mode (R30), and only after the reference candle has been frozen (R24) and gap-exit confirmed (R26).

**Required inputs:** Candle list from `MT5DataAdapter.get_candles()` (which strips the forming bar)
**Condition:** Every candle evaluated satisfies `candle.time < current_bar_open_time`
**Expected outcome:** No look-ahead into unfinished price action
**Rejection reason:** `"Candle at {time} is not yet closed — rejected"`

**Test requirement:** T-R3-1: Detector rejects a candle list containing the live bar. T-R3-2: Detector produces identical results whether the live bar is present or stripped.

---

### R4 — Symbol discovery
**Status:** ✅ APPROVED

**Rule:** At startup, the engine calls `MT5DataAdapter.get_symbol_info()` for each approved instrument. It records and logs: `name`, `digits`, `point`, `tick_size`, `tick_value`, `contract_size`, `volume_min`, `volume_max`, `volume_step`, `trade_stops_level`, `spread`, `currency_profit`, `currency_margin`.

If any required field is absent, zero, or nonsensical (e.g. `tick_size == 0`, `volume_step == 0`), the symbol is disabled and no orders are submitted until the spec is valid.

**Never assume** that XAUUSD and BTCUSD share any contract parameter.

**Test requirement:** T-R4-1: Engine disables a symbol if `tick_size == 0`. T-R4-2: Engine correctly reads and stores distinct specs for two different instruments.

---

### R5 — FVG definition — bullish
**Status:** ✅ APPROVED

For three consecutive completed H1 candles C1, C2, C3:

```
Bullish FVG exists when:  C1.high < C3.low
Gap lower boundary (fvg_low)  = C1.high
Gap upper boundary (fvg_high) = C3.low
Gap size = fvg_high − fvg_low
```

C2 is the impulse candle. The gap is the unfilled space between C1's top and C3's bottom.

**Required inputs:** Three consecutive completed candles
**Condition:** `C1.high < C3.low`
**Expected outcome:** Bullish FVG object with direction `"BULLISH"`, `fvg_low = C1.high`, `fvg_high = C3.low`

**Test requirement:** T-R5-1: Correct FVG boundaries on a known bullish triple. T-R5-2: No FVG when C1.high >= C3.low.

---

### R6 — FVG definition — bearish
**Status:** ✅ APPROVED

For three consecutive completed H1 candles C1, C2, C3:

```
Bearish FVG exists when:  C1.low > C3.high
Gap upper boundary (fvg_high) = C1.low
Gap lower boundary (fvg_low)  = C3.high
Gap size = fvg_high − fvg_low
```

**Required inputs:** Three consecutive completed candles
**Condition:** `C1.low > C3.high`
**Expected outcome:** Bearish FVG object with direction `"BEARISH"`, `fvg_high = C1.low`, `fvg_low = C3.high`

**Test requirement:** T-R6-1: Correct FVG boundaries on a known bearish triple. T-R6-2: No FVG when C1.low <= C3.high.

---

### R7 — FVG confirmation timing
**Status:** ✅ APPROVED

**Rule:** An FVG is confirmed only after C3 has fully closed. The detector must never register an FVG from a candle that is still forming.

**Test requirement:** T-R7-1: Detector called with candle list where C3 is live returns no FVG at that position.

---

### R8 — FVG minimum size
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** A detected FVG is valid only if its size meets both of the following thresholds simultaneously:

```
min_size = max(
    0.1 × ATR(14, completed H1 candles),
    2 × symbol_info.tick_size
)
```

where ATR(14) is the simple average of the last 14 completed H1 true ranges.

The threshold is **configurable per symbol**. If ATR cannot be computed (fewer than 14 completed candles) or `symbol_info` is unavailable, the FVG is **rejected** with reason `"ATR or symbol spec unavailable"`.

**This threshold is an initial noise filter, not a proven optimal value.**

**Configurable parameter:** `min_fvg_atr_factor` (default `0.1`) and `min_fvg_ticks` (default `2`) per symbol in `StrategySettings`.

**Test requirement:** T-R8-1: FVG below threshold is rejected. T-R8-2: FVG at exactly the threshold is accepted. T-R8-3: Rejection when ATR unavailable. T-R8-4: Threshold computed independently per symbol.

---

### R9 — FVG maximum age
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** An FVG becomes **ineligible** (no new sweep can be associated with it) after **24 completed H1 bars** have elapsed since its confirmation candle (C3's close bar), measured by counting completed bars, not wall-clock time.

**Configurable parameter:** `max_fvg_age_bars` (default `24`) in `StrategySettings`.

**Condition:** `bars_since_c3 < max_fvg_age_bars`
**Expected outcome:** FVG transitions to `EXPIRED` state; no new sweeps associated
**Rejection reason:** `"FVG exceeded max age of {n} completed bars"`

**This default is not claimed to be optimal.**

**Test requirement:** T-R9-1: FVG at bar 23 is still eligible. T-R9-2: FVG at bar 24 is expired. T-R9-3: Bar counting uses completed candles, not timestamps.

---

### R10 — FVG stored fields
**Status:** ✅ APPROVED

Every confirmed FVG must store:

| Field | Description |
|---|---|
| `id` | Deterministic SHA-256 ID derived from symbol, direction, C1 open time |
| `symbol` | Broker symbol name (resolved) |
| `timeframe` | Always `"H1"` |
| `direction` | `"BULLISH"` or `"BEARISH"` |
| `fvg_low` | Lower boundary price |
| `fvg_high` | Upper boundary price |
| `c1_time` | C1 open time (UTC) |
| `c3_time` | C3 open time (UTC) — confirmation time |
| `c1_high` | C1 high |
| `c1_low` | C1 low |
| `c3_high` | C3 high |
| `c3_low` | C3 low |
| `atr_at_detection` | ATR(14) value used for size filter at detection time |
| `created_at` | System timestamp (UTC) when FVG was stored |

**Test requirement:** T-R10-1: All fields present in a stored FVG. T-R10-2: ID is stable across restarts for same inputs.

---

### R11 — FVG full traversal invalidation
**Status:** ✅ APPROVED

**Rule:** An FVG is invalidated if price **fully traverses** it — i.e., a completed candle closes beyond the far boundary in the direction opposite to the gap:

- Bullish FVG: invalidated when a completed candle closes **below** `fvg_low`
- Bearish FVG: invalidated when a completed candle closes **above** `fvg_high`

A fully traversed gap must not be resurrected or treated as a new gap.

**Condition:** For bullish: `candle.close < fvg_low`. For bearish: `candle.close > fvg_high`.
**Expected outcome:** Setup transitions to `INVALIDATED`; reason and timestamp recorded

**Test requirement:** T-R11-1: Bullish FVG invalidated when candle closes below fvg_low. T-R11-2: Bearish FVG invalidated when candle closes above fvg_high. T-R11-3: Invalidated FVG cannot be used for a new setup.

---

### R12 — Swing detection method
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** Swing highs and lows are identified using a **confirmed 2-left / 2-right pivot**:

- **Swing high** at candle index `i`: `candles[i].high` is strictly greater than `candles[i-1].high`, `candles[i-2].high`, `candles[i+1].high`, and `candles[i+2].high`.
- **Swing low** at candle index `i`: `candles[i].low` is strictly less than `candles[i-1].low`, `candles[i-2].low`, `candles[i+1].low`, and `candles[i+2].low`.

**Configurable parameters:** `pivot_left_bars` (default `2`) and `pivot_right_bars` (default `2`) in `StrategySettings`.

**This is an initial value, not a proven optimal pivot period.**

**Test requirement:** T-R12-1: Correct swing high detected on known data. T-R12-2: Correct swing low detected on known data. T-R12-3: Swing requires exactly 2+2 surrounding bars per side.

---

### R13 — Swing tie-handling
**Status:** ✅ APPROVED

**Rule:** If two surrounding candles have identical highs (for a swing high) or identical lows (for a swing low), the pivot condition fails (strict inequality required). A tie is not a confirmed pivot.

**Condition:** All comparisons use `>` for highs and `<` for lows, never `>=` or `<=`.
**Expected outcome:** No swing registered on equal values

**Test requirement:** T-R13-1: Equal-high candle does not produce a swing high. T-R13-2: Equal-low candle does not produce a swing low.

---

### R14 — Swing confirmation timing
**Status:** ✅ APPROVED

**Rule:** A pivot at index `i` is **not usable** until candles at `i+1` and `i+2` have closed. The confirmed-at timestamp is the open time of candle `i+2`.

Future candles must never be used to confirm a historical pivot.

**Test requirement:** T-R14-1: Pivot at index i is absent from results when only i+1 has closed. T-R14-2: Pivot appears only after i+2 closes.

---

### R15 — Bullish liquidity sweep definition
**Status:** ✅ APPROVED

All four conditions must be met by a single completed H1 candle:

1. A **previously confirmed** swing low exists (confirmed before this candle's open time).
2. This candle's low is **strictly below** the swing low level: `candle.low < swing.level`.
3. This candle's close is **strictly above** the swing low level: `candle.close > swing.level` (close-back required).
4. The swing low was confirmed **before** this candle opened.

A wick-through without the close-back condition is **not** a confirmed sweep.

**Stored fields:** swing level, sweep candle timestamp (UTC), sweep candle low (the extreme).

**Test requirement:** T-R15-1: All four conditions satisfied → sweep confirmed. T-R15-2: Wick below but close below → not a sweep. T-R15-3: Wick below but close exactly at swing level → not a sweep (strict inequality). T-R15-4: Swing confirmed after candle open → not eligible.

---

### R16 — Bearish liquidity sweep definition
**Status:** ✅ APPROVED

All four conditions must be met by a single completed H1 candle:

1. A **previously confirmed** swing high exists.
2. This candle's high is **strictly above** the swing high level: `candle.high > swing.level`.
3. This candle's close is **strictly below** the swing high level: `candle.close < swing.level` (close-back required).
4. The swing high was confirmed **before** this candle opened.

**Stored fields:** swing level, sweep candle timestamp (UTC), sweep candle high (the extreme).

**Test requirement:** T-R16-1: All four conditions → sweep confirmed. T-R16-2: Wick above but close above → not a sweep. T-R16-3: Strict inequality at close.

---

### R17 — Sweep ordering (FVG must precede sweep)
**Status:** ✅ APPROVED

**Rule:** The qualifying sweep must occur **after** the FVG is confirmed (C3 close). The sweep candle's open time must be strictly greater than the FVG's C3 close time.

A sweep that predates the FVG confirmation cannot be associated with that FVG.

**Condition:** `sweep_candle.time > fvg.c3_time`
**Expected outcome:** Pre-FVG sweeps are not associated with this setup

**Test requirement:** T-R17-1: Sweep before C3 → not associated. T-R17-2: Sweep after C3 → associated correctly.

---

### R18 — Sweep stored fields
**Status:** ✅ APPROVED

Every confirmed sweep must store:

| Field | Description |
|---|---|
| `swing_level` | The swept swing high or low price |
| `sweep_candle_time` | UTC open time of the sweep candle |
| `sweep_extreme` | Lowest low (bullish) or highest high (bearish) of the sweep candle |
| `direction` | `"BULLISH"` or `"BEARISH"` |

**Test requirement:** T-R18-1: All fields stored correctly on a confirmed sweep.

---

### R19 — Setup sequence — required order
**Status:** ✅ APPROVED

**Rule:** The following stages must occur in this exact order for every valid setup. No stage may be skipped. No stage may repeat in a different order.

```
Stage 1:  FVG_DETECTED          — C3 closes, FVG confirmed, size filter passes
Stage 2:  SWEEP_CONFIRMED       — qualifying liquidity sweep detected
Stage 3:  WAITING_FOR_RETRACEMENT — engine monitors for price to enter FVG
Stage 4:  REFERENCE_CANDLE_SAVED  — first qualifying retracement candle saved
Stage 5:  WAITING_FOR_GAP_EXIT    — reference candle tracking; awaiting gap exit
Stage 6:  GAP_EXITED              — gap-exit candle closes; reference candle frozen
Stage 7:  WAITING_FOR_TRIGGER     — monitoring for trigger level break
Stage 8:  SIGNAL_READY            — trigger broken; pre-submission checks pending
Stage 9:  RISK_CHECK              — all risk, sizing, and broker checks run
Stage 10: ORDER_PENDING           — order submitted to executor
Stage 11: POSITION_OPEN           — fill confirmed
Stage 12: CLOSED                  — position closed (SL, TP, or manual exit)
```

Terminal states (no further transitions): `CLOSED`, `EXPIRED`, `INVALIDATED`, `REJECTED`.

**Test requirement:** T-R19-1: Happy-path state sequence produces correct terminal state. T-R19-2: Every transition recorded in audit log.

---

### R20 — Out-of-order stage rejection
**Status:** ✅ APPROVED

**Rule:** If any required stage condition is detected **out of order** (e.g. a sweep is detected before an FVG exists for it, or a trigger fires before gap exit is confirmed), the event is **rejected and logged**. The setup is not advanced.

**Expected outcome:** State machine rejects the transition; `SetupTransition` records the rejected event with explanation

**Test requirement:** T-R20-1: Sweep detected before FVG → rejected. T-R20-2: Trigger detected before gap exit → rejected.

---

### R21 — Retracement reference candle — bullish
**Status:** ✅ APPROVED

**Rule (bullish setup):** During the `WAITING_FOR_RETRACEMENT` / `REFERENCE_CANDLE_SAVED` stages, every completed H1 candle is evaluated against the following qualification criteria:

1. The candle's range intersects the FVG: `candle.low < fvg_high AND candle.high > fvg_low`
2. The candle participates in the **downward retracement**: `candle.low <= fvg_high` (the low reaches into or below the gap top)

Among all qualifying candles, the **most recent** (latest `candle.time`) is selected as the current reference candle. The reference candle is updated as new qualifying candles appear, until the gap-exit condition (R26) fires.

The reference candle's `high` is the trigger level for a bullish entry.

**Test requirement:** T-R21-1: Most recent qualifying candle selected. T-R21-2: Non-intersecting candle not selected. T-R21-3: Candle fully above FVG not selected as reference.

---

### R22 — Retracement reference candle — bearish
**Status:** ✅ APPROVED

**Rule (bearish setup):** Same logic, mirrored:

1. `candle.low < fvg_high AND candle.high > fvg_low` (range intersects)
2. `candle.high >= fvg_low` (the high reaches into or above the gap bottom — upward retracement)

Most recent qualifying candle selected. Updated until gap exit. The reference candle's `low` is the trigger level.

**Test requirement:** T-R22-1: Correct reference candle selected for bearish setup. T-R22-2: Candle fully below FVG not selected.

---

### R23 — Reference candle update rule
**Status:** ✅ APPROVED

**Rule:** While the setup is in `REFERENCE_CANDLE_SAVED` state (before gap exit), new qualifying candles **replace** the stored reference candle. The trigger level updates accordingly. Every update is recorded as a `REFERENCE_CANDLE_UPDATED` transition in the audit log with old and new trigger levels.

This continues until gap exit (R26), at which point the reference candle is frozen permanently.

**Test requirement:** T-R23-1: Reference candle is updated when a newer qualifying candle arrives before gap exit. T-R23-2: Update recorded in audit log with both trigger levels.

---

### R24 — Reference candle freeze condition
**Status:** ✅ APPROVED

**Rule:** The reference candle is **frozen permanently** when the gap-exit condition (R26) is confirmed. After freezing:
- The OHLC values, timestamp, and trigger level stored in the Setup row are immutable.
- No subsequent candle may update the reference candle or the trigger level.
- The setup transitions to `WAITING_FOR_TRIGGER`.

**Test requirement:** T-R24-1: Reference candle not updated after gap exit. T-R24-2: Setup in WAITING_FOR_TRIGGER cannot change its trigger level.

---

### R25 — Reference candle rejection
**Status:** ✅ APPROVED

**Rule:** If no qualifying candle can be identified during the retracement phase before the setup expires, the setup is **rejected** with reason `"No qualifying reference candle found during retracement"`.

A setup must not be advanced to WAITING_FOR_TRIGGER without a valid, frozen reference candle.

**Test requirement:** T-R25-1: Setup rejected when no qualifying candle exists. T-R25-2: Rejection recorded with timestamp and reason.

---

### R26 — Gap-exit condition
**Status:** 🔶 PROPOSED DEFAULT

**Rule:**
- **Bullish setup:** A completed H1 candle closes **strictly above** `fvg_high` (the FVG upper boundary). This confirms price has exited the gap on the bullish side.
- **Bearish setup:** A completed H1 candle closes **strictly below** `fvg_low` (the FVG lower boundary). This confirms price has exited the gap on the bearish side.

`candle.close > fvg_high` (bullish) / `candle.close < fvg_low` (bearish)

This condition is conservative (close-based, not wick-based). **It is configurable.** Any change to this condition requires a new spec version.

**Configurable parameter:** `gap_exit_mode` (`"candle_close"` default; may be extended to other modes in a future spec version).

**Test requirement:** T-R26-1: Bullish gap exit when candle closes above fvg_high. T-R26-2: No gap exit when candle closes at or below fvg_high. T-R26-3: Symmetric bearish test.

---

### R27 — Entry trigger — bullish
**Status:** ✅ APPROVED

**Rule:** For a bullish setup, the entry trigger fires when price breaks **above** the frozen reference candle's `high`.

`trigger_level = frozen_reference_candle.high`

This must occur **after** gap exit is confirmed and the reference candle is frozen.

---

### R28 — Entry trigger — bearish
**Status:** ✅ APPROVED

**Rule:** For a bearish setup, the entry trigger fires when price breaks **below** the frozen reference candle's `low`.

`trigger_level = frozen_reference_candle.low`

---

### R29 — Entry trigger mode — CANDLE_CLOSE (default)
**Status:** ✅ APPROVED — default mode

**Rule:** In `CANDLE_CLOSE` mode:
- **Bullish:** trigger fires when a completed H1 candle closes **strictly above** `trigger_level`: `candle.close > trigger_level`
- **Bearish:** trigger fires when a completed H1 candle closes **strictly below** `trigger_level`: `candle.close < trigger_level`

This is the **initial default** entry trigger mode.

**Test requirement:** T-R29-1: Trigger fires on close above trigger_level (bullish). T-R29-2: No trigger on close at or below trigger_level. T-R29-3: Symmetric bearish test.

---

### R30 — Entry trigger mode — TICK_BREAK
**Status:** ✅ APPROVED — alternative configurable mode

**Rule:** In `TICK_BREAK` mode:
- **Bullish:** trigger fires when the live `ask` price is **strictly above** `trigger_level`: `ask > trigger_level`
- **Bearish:** trigger fires when the live `bid` price is **strictly below** `trigger_level`: `bid < trigger_level`

The executable quote (`ask` for buys, `bid` for sells) is used, not `last`.

**Stale quote rejection:** A tick quote is considered stale if its timestamp is more than 5 seconds old (configurable: `max_tick_age_seconds`, default `5`).

The trigger event is **persisted** immediately upon detection to prevent duplicate entries on reconnection.

**Test requirement:** T-R30-1: Bullish tick trigger on ask > trigger_level. T-R30-2: Stale tick rejected. T-R30-3: Duplicate trigger not fired after persistence.

---

### R31 — Tick-break quote validity
**Status:** ✅ APPROVED

**Rule:** Before accepting a tick as an entry trigger in TICK_BREAK mode, validate:
1. Tick timestamp is within `max_tick_age_seconds` of the current system time.
2. Bid and ask are both positive non-zero values.
3. `ask > bid` (no inverted spread).
4. Spread `(ask - bid)` is within the configured spread limit for this symbol (R59).

**Test requirement:** T-R31-1: Invalid tick (stale, zero, inverted) rejected. T-R31-2: Wide-spread tick rejected at trigger check.

---

### R32 — Entry pre-submission checklist
**Status:** ✅ APPROVED

**Rule:** Before submitting any order (paper or demo), all of the following must pass. If any check fails, the order is not submitted and the failure reason is logged:

| Check # | Condition |
|---|---|
| C1 | Setup state is `SIGNAL_READY` |
| C2 | Setup has not expired (`EXPIRED` state not set) |
| C3 | Trigger event has been confirmed and persisted |
| C4 | Market quote is fresh (within `max_tick_age_seconds`) |
| C5 | Market is tradable (not closed, not in pre-open period per broker session) |
| C6 | Current spread ≤ configured limit for this symbol |
| C7 | Late-entry guard passes (R33) |
| C8 | Stop-loss price is valid and not within broker stop-distance |
| C9 | Computed volume ≥ `volume_min` AND ≤ `volume_max` |
| C10 | Estimated risk at stop ≤ 1% of current equity |
| C11 | Daily trade count < `max_daily_trades` |
| C12 | No daily loss lock active |
| C13 | No consecutive-loss lock active |
| C14 | No news lock active |
| C15 | No spread lock active |
| C16 | Concurrent position count for this symbol < `max_open_per_symbol` |
| C17 | Active account label and broker symbol verified |

**Test requirement:** T-R32-1 through T-R32-17: One test per check that confirms rejection when that check alone fails.

---

### R33 — Late-entry guard
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** The order is rejected if the executable entry price has moved **more than `0.1 × ATR(14)`** beyond the saved trigger level, measured in the **unfavorable direction** (away from the trade's expected profit direction):

- **Bullish:** `ask > trigger_level + (0.1 × ATR_14)` → reject (chased too far)
- **Bearish:** `bid < trigger_level - (0.1 × ATR_14)` → reject (chased too far)

**Configurable parameter:** `late_entry_atr_factor` (default `0.1`) per symbol in `StrategySettings`.

**This threshold is not claimed to be optimal.** Log the actual distance and threshold on every rejection.

**Test requirement:** T-R33-1: Entry rejected when price exceeds guard threshold (bullish). T-R33-2: Entry accepted when price is within threshold. T-R33-3: Symmetric bearish test. T-R33-4: Guard computed per-symbol using correct ATR.

---

### R34 — Signal-only mode
**Status:** ✅ APPROVED

**Rule:** The engine must support a `SIGNAL_ONLY` output mode that, when triggered, produces and logs the proposed entry price, stop-loss price, take-profit price, volume, estimated risk in USD, and estimated R:R — **without submitting any order**.

This mode must be activatable independently of `execution_mode`.

**Test requirement:** T-R34-1: Signal-only mode produces full signal record. T-R34-2: Signal-only mode calls no order-submission function.

---

### R35 — Stop-loss structural reference
**Status:** ✅ APPROVED

**Rule:** The stop-loss is placed beyond the **sweep candle's extreme**:

- **Bullish:** `sl = sweep_candle.low − buffer` (stop below the sweep candle's lowest point)
- **Bearish:** `sl = sweep_candle.high + buffer` (stop above the sweep candle's highest point)

`buffer` is defined in R36.

**Required inputs:** `sweep_extreme` (stored in sweep record), buffer value, symbol tick size
**Condition:** SL price is on the opposite side of the sweep extreme from entry
**Expected outcome:** Structural SL calculated from sweep candle extreme

**Test requirement:** T-R35-1: Bullish SL is below sweep_extreme. T-R35-2: Bearish SL is above sweep_extreme.

---

### R36 — Stop-loss buffer
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** The buffer added beyond the sweep extreme is the **greater of**:

```
buffer = max(2 × symbol_info.tick_size, 0.05 × ATR(14))
```

**Configurable parameter:** `sl_buffer_atr_factor` (default `0.05`) and `sl_buffer_min_ticks` (default `2`) per symbol in `StrategySettings`.

**This is not a proven optimal buffer.** The buffer must be recomputed with the ATR value at the time of the signal, not stored from FVG detection time.

**Test requirement:** T-R36-1: Buffer uses the greater of the two components. T-R36-2: Buffer at least 2 ticks when ATR-based value is smaller. T-R36-3: ATR-based buffer used when it is larger than 2 ticks.

---

### R37 — Stop-loss broker constraints
**Status:** ✅ APPROVED

**Rule:** The calculated SL price must satisfy:

1. `abs(entry - sl) >= symbol_info.trade_stops_level × symbol_info.point` (broker minimum stop distance)
2. SL price is rounded to the nearest valid `symbol_info.point` increment

If either condition cannot be satisfied, the trade is **rejected** with reason `"Stop-loss violates broker stop-distance or tick-increment constraint"`.

**Test requirement:** T-R37-1: Trade rejected when SL closer than broker stop-distance. T-R37-2: SL correctly rounded to tick increment.

---

### R38 — Stop-loss post-entry widening prohibition
**Status:** ❌ PROHIBITED

**Rule:** The stop-loss must **never** be moved in a direction that increases the originally approved risk (i.e. further from entry). This prohibition is permanent and cannot be overridden by any runtime logic.

---

### R39 — Stop-loss broker confirmation requirement
**Status:** ✅ APPROVED

**Rule:** After the entry order fills, the engine must verify that the protective stop order has been accepted by the broker (MT5 retcode confirms placement). The position is not declared "protected" until this confirmation is received.

If the stop order is rejected by MT5, the engine must:
1. Log the rejection with the MT5 retcode and full order details.
2. Block all new entries.
3. Raise a user-visible alert: `"UNPROTECTED POSITION — stop-loss rejected by broker"`
4. Attempt retry up to a configurable maximum (`max_sl_retry`, default `3`).
5. If retries exhausted, escalate alert to `CRITICAL` and await manual intervention.

**Test requirement:** T-R39-1: Unprotected position alert raised on stop rejection. T-R39-2: New entries blocked when unprotected position exists.

---

### R40 — Take-profit minimum R:R
**Status:** ✅ APPROVED

**Rule:** The minimum required reward-to-risk ratio is **1:2**.

The actual R:R is calculated after all rounding:

```
actual_rr = reward_usd / risk_usd
```

If `actual_rr < 2.0`, the trade is **rejected** with reason `"Computed R:R {actual_rr:.2f} below minimum 2.0"`.

**Test requirement:** T-R40-1: Trade rejected when R:R < 2.0 after rounding. T-R40-2: Trade accepted when R:R >= 2.0.

---

### R41 — Take-profit calculation
**Status:** ✅ APPROVED

**Rule:**

- **Long:** `tp = entry + 2 × (entry − sl)`
- **Short:** `tp = entry − 2 × (sl − entry)`

The multiplier is the `min_reward_to_risk` setting (default `2.0`, not configurable below 2.0).

**Required inputs:** Actual executable entry price, SL price
**Not inputs:** Reference candle level, FVG boundaries, ATR (TP is derived purely from entry and SL)

**Test requirement:** T-R41-1: TP is exactly `2 × sl_distance` from entry. T-R41-2: TP calculation uses actual entry price, not signal trigger price.

---

### R42 — Take-profit rounding
**Status:** ✅ APPROVED

**Rule:** The TP price is rounded to the nearest valid `symbol_info.point` increment. Rounding is done **conservatively**: the TP is rounded **toward entry** (reducing the reward), not away from it. After rounding, R:R is rechecked against R40.

**Test requirement:** T-R42-1: Rounded TP does not violate the 2:1 minimum. T-R42-2: TP rounded toward entry, not away.

---

### R43 — Disabled exit features (amended in v1.1)
**Status:** ❌ PROHIBITED for unlisted features — break-even and ATR trailing stop are now ✅ APPROVED via R89–R96

The following exit mechanisms remain **disabled** and must not be implemented:
- Partial take-profit (scale-out)
- Opposite-signal position reversal
- Discretionary or manual exit by the engine
- Time-based exit

Break-even and ATR trailing stop are governed by R89–R96 below.

---

### R44 — Risk per trade
**Status:** ✅ APPROVED

**Rule:** Each trade risks exactly **1% of current account equity** at the time of signal evaluation.

```
risk_usd = account_equity × 0.01
```

`account_equity` is the live equity value from `MT5DataAdapter.get_account_info()` at signal evaluation time, not a cached or estimated value.

**Test requirement:** T-R44-1: Risk computed as 1% of equity, not balance. T-R44-2: Stale equity value causes rejection (see R32 C4).

---

### R45 — Position sizing method
**Status:** ✅ APPROVED

**Rule:** Volume is computed as:

```
sl_distance_price = abs(entry − sl)
sl_distance_ticks = sl_distance_price / symbol_info.tick_size
pip_value_per_lot = symbol_info.tick_value   [this is already per tick_size move per lot]
risk_usd          = account_equity × 0.01
volume_raw        = risk_usd / (sl_distance_ticks × pip_value_per_lot)
```

This formula uses the instrument's actual `tick_size` and `tick_value` from MT5, sourced per symbol. It is **not interchangeable** between XAUUSD and BTCUSD.

**Test requirement:** T-R45-1: Correct volume for known XAUUSD parameters. T-R45-2: Different volume for BTCUSD with different tick_value. T-R45-3: Formula produces correct monetary risk at stop.

---

### R46 — Volume rounding
**Status:** ✅ APPROVED

**Rule:** The computed raw volume is rounded **down** to the nearest valid `volume_step` increment:

```
volume = floor(volume_raw / volume_step) × volume_step
volume = round(volume, 8)   # avoid floating-point artefacts
```

**Test requirement:** T-R46-1: Volume rounded down, never up. T-R46-2: Rounding does not cause volume to exceed volume_max.

---

### R47 — Minimum volume rejection
**Status:** ✅ APPROVED

**Rule:** If `volume < symbol_info.volume_min` after rounding, the trade is **rejected** with reason `"Computed volume {volume} below broker minimum {volume_min} — equity too small or stop too wide"`.

**Test requirement:** T-R47-1: Trade rejected when volume below minimum. T-R47-2: Rejection message includes actual and minimum volume.

---

### R48 — Instrument-specific sizing
**Status:** ✅ APPROVED

**Rule:** Position sizing must use each instrument's own `tick_size`, `tick_value`, `contract_size`, `volume_min`, `volume_max`, and `volume_step` sourced from `MT5DataAdapter.get_symbol_info()`. No hardcoded lot size or common per-pip value may be used across instruments.

**Test requirement:** T-R48-1: Engine uses XAUUSD-specific tick_value for XAUUSD sizing. T-R48-2: Engine uses BTCUSD-specific tick_value for BTCUSD sizing.

---

### R49 — Loss-recovery sizing prohibition
**Status:** ❌ PROHIBITED

**Rule:** Position size must **never** be increased to recover from previous losses (martingale, averaging-down, grid). The 1% equity risk rule applies unconditionally regardless of prior outcomes.

---

### R50 — Maximum entries per day
**Status:** ✅ APPROVED

**Rule:** Maximum **5 new executed entries** per account per broker trading day.

The counter increments only on confirmed fills (paper or demo), not on signals, rejected requests, retries, or duplicate callbacks. If a fill callback is received more than once for the same order ID, it is counted once.

**Configurable parameter:** `max_daily_trades` (default `5`), fixed and not reducible below 1.

**Test requirement:** T-R50-1: Sixth entry rejected after five fills. T-R50-2: Rejected orders do not increment counter. T-R50-3: Duplicate fill callback does not double-count.

---

### R51 — Daily entry counter scope
**Status:** ✅ APPROVED

**Rule:** The daily counter resets at the **broker's trading-day boundary**, not at midnight UTC or local time. The broker server's date is used. This boundary must be explicitly discovered from MT5 server time, not assumed.

The counter is persisted to SQLite and survives restarts.

**Test requirement:** T-R51-1: Counter does not reset on application restart. T-R51-2: Counter resets at broker day boundary, not UTC midnight.

---

### R52 — Maximum concurrent positions per symbol
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** Maximum **1** bot-managed open position per symbol at any time.

XAUUSD and BTCUSD are evaluated independently — each may have one open position simultaneously if their individual risk checks pass.

**Configurable parameter:** `max_open_per_symbol` (default `1`) per symbol in `RiskSettings`.

**This default is not claimed to be optimal.**

**Test requirement:** T-R52-1: Second entry for same symbol blocked when position open. T-R52-2: XAUUSD and BTCUSD can both have open positions simultaneously.

---

### R53 — Manual position handling
**Status:** ✅ APPROVED

**Rule:** Positions opened manually in MT5 (not by the bot) must be detected and displayed in the dashboard. The engine must **not** automatically close, reverse, or modify manual positions.

Manual positions are identified by the absence of a matching bot order record in the local database.

**Test requirement:** T-R53-1: Manual position detected and displayed. T-R53-2: Engine does not submit close/modify requests for manual positions.

---

### R54 — Daily loss limit
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** When realized plus unrealized P&L for the broker trading day reaches **−3% of start-of-day equity**, the engine immediately halts all new entries for the remainder of that trading day.

**Configurable parameter:** `daily_loss_pct` (default `3.0`) in `RiskSettings`.

**These are safety proposals. Gaps, slippage, or connectivity failures can cause losses exceeding this threshold.**

**Test requirement:** T-R54-1: New entry blocked after −3% daily loss. T-R54-2: Lock persists after restart. T-R54-3: Alert raised when limit breached.

---

### R55 — Daily loss P&L method
**Status:** ✅ APPROVED

**Rule:** Daily P&L is computed as:

```
daily_pnl = realized_pnl_today + unrealized_pnl_open_positions
```

`realized_pnl_today` = sum of all closed-trade P&L (after costs) since the broker day boundary.
`unrealized_pnl_open_positions` = sum of floating P&L on all open bot-managed positions, computed from current market prices.

`start_of_day_equity` is captured once per broker trading day on first connection, stored in `DailyRiskState`, and never overwritten mid-day.

**Test requirement:** T-R55-1: Unrealized loss included in daily P&L check. T-R55-2: Start-of-day equity not overwritten on reconnection within same day.

---

### R56 — Daily loss lock persistence
**Status:** ✅ APPROVED

**Rule:** The daily loss lock is persisted to `DailyRiskState` in SQLite. Restarting the application does **not** reset the lock. The lock clears automatically only when the broker trading-day boundary rolls over and a new day record is created.

**Test requirement:** T-R56-1: Lock survives application restart. T-R56-2: Lock clears on new broker day.

---

### R57 — Daily loss alert and resume
**Status:** ✅ APPROVED

**Rule:** When the daily loss limit is breached, the engine raises a visible alert in the dashboard labelled `"DAILY LOSS LIMIT REACHED — new entries halted"`. Resumption requires explicit manual action (dashboard button with confirmation) plus a safety check confirming the operator intends to override.

**Test requirement:** T-R57-1: Alert raised on breach. T-R57-2: Resume requires explicit confirmation.

---

### R58 — Consecutive-loss lockout
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** After **3 consecutive closed losing bot trades** (regardless of symbol or day), the engine locks out new entries until manual review and explicit resume.

**Configurable parameter:** `max_consecutive_losses` (default `3`, `0` = disabled) in `RiskSettings`.

The consecutive counter resets to zero on the first winning closed trade. It does not reset automatically at the start of a new day. Resumption requires explicit manual action.

**Test requirement:** T-R58-1: Lock triggered after 3 consecutive losses. T-R58-2: Counter resets on a win. T-R58-3: Lock persists across restart. T-R58-4: Counter=0 setting disables the lockout.

---

### R59 — Spread limit
**Status:** 🔶 PROPOSED DEFAULT (value unconfigured until calibrated)

**Rule:** The engine uses **configurable, symbol-specific spread limits** calibrated from actual Exness demo quotes. There is no hardcoded universal spread limit shared between XAUUSD and BTCUSD.

Until a valid limit is recorded for a symbol in `RiskSettings`, automated entries for that symbol are **blocked** (see R60).

**Configurable parameter:** `max_spread_pips` per symbol (no default — must be explicitly set from actual broker data before entries are permitted).

**Test requirement:** T-R59-1: Entry blocked when spread exceeds configured limit. T-R59-2: Spread checked using live ask−bid from MT5, not cached.

---

### R60 — Spread limit unconfigured behaviour
**Status:** ✅ APPROVED

**Rule:** If no spread limit has been configured for a symbol (`max_spread_pips` is `None` or `0`), automated entries for that symbol are **blocked** with reason `"Spread limit not configured — entries blocked until calibrated"`. The engine does not assume spread is acceptable.

**Test requirement:** T-R60-1: Entry blocked when limit unconfigured.

---

### R61 — Session filter
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** Session restrictions are **configurable per symbol** using broker-server time with explicit timezone handling. By default, no additional session restriction is applied, provided:
1. The broker is open (symbol is tradable per MT5 `symbol_info.session_*`).
2. All other entry checks pass.

BTCUSD trading hours must be discovered from the broker at startup, not assumed to be 24/7. If MT5 reports BTCUSD as closed, entries are blocked.

**Configurable parameter:** `session_start_utc` and `session_end_utc` per symbol (`None` = no filter beyond broker availability).

**Test requirement:** T-R61-1: Entry blocked when symbol is marked closed by MT5. T-R61-2: Session filter correctly uses broker server time, not local time.

---

### R62 — News lockout
**Status:** ✅ APPROVED

**Rule:** A **manual news lockout** is supported in the initial version. An operator may activate the news lock via the dashboard. When active, no new entries are placed for the locked symbol(s). No automatic news-calendar integration in this version.

The news lock is stored in `DailyRiskState.news_lock` and persists across restarts.

**Test requirement:** T-R62-1: Entry blocked when news lock active. T-R62-2: News lock persists across restart.

---

### R63 — News lockout scope
**Status:** ✅ APPROVED

**Rule:** A news lockout **blocks new entries only**. It does not remove, modify, or cancel existing protective stops on open positions. Existing positions remain protected by their broker-side stops.

**Test requirement:** T-R63-1: Existing position stops not removed when news lock activated.

---

### R64 — Setup expiry — post-sweep
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** A setup expires if it has not reached `SIGNAL_READY` within **12 completed H1 bars** after the qualifying sweep's candle close time.

**Configurable parameter:** `max_setup_age_bars_after_sweep` (default `12`) in `StrategySettings`.

**Test requirement:** T-R64-1: Setup expires at bar 12 after sweep. T-R64-2: Setup valid at bar 11.

---

### R65 — Setup expiry — FVG age
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** A setup expires if its underlying FVG has exceeded **24 completed H1 bars** since confirmation (R9), whichever expiry condition (R64 or R65) is reached first.

**Configurable parameter:** `max_fvg_age_bars` (default `24`) in `StrategySettings`.

**Test requirement:** T-R65-1: Setup expires when FVG exceeds 24 bars even if within post-sweep limit. T-R65-2: Earlier of the two expiry conditions applies.

---

### R66 — Setup invalidation conditions
**Status:** ✅ APPROVED

A setup is invalidated (transitions to `INVALIDATED`) under any of the following conditions, whichever occurs first:

1. The sweep-candle extreme is breached before entry (see R67, R68).
2. The underlying FVG is fully traversed (R11).
3. No qualifying reference candle can be identified (R25).
4. The required sequence is executed out of order (R20).

The invalidation reason and timestamp are recorded. An invalidated setup is never resurrected.

---

### R67 — Bullish setup invalidation event
**Status:** ✅ APPROVED

**Rule:** A bullish setup is invalidated when a completed candle closes **below** the sweep candle's low (`candle.close < sweep_extreme`) before entry.

**Test requirement:** T-R67-1: Bullish setup invalidated on close below sweep low. T-R67-2: Intrabar wick below sweep low without close does not invalidate.

---

### R68 — Bearish setup invalidation event
**Status:** ✅ APPROVED

**Rule:** A bearish setup is invalidated when a completed candle closes **above** the sweep candle's high (`candle.close > sweep_extreme`) before entry.

**Test requirement:** T-R68-1: Bearish setup invalidated on close above sweep high. T-R68-2: Intrabar wick above sweep high without close does not invalidate.

---

### R69 — No-resurrection rule
**Status:** ✅ APPROVED

**Rule:** An expired or invalidated setup must never be reactivated, resumed, or treated as a fresh setup. Once a setup reaches `EXPIRED` or `INVALIDATED`, it is permanently terminal.

**Test requirement:** T-R69-1: Transition from EXPIRED to any non-terminal state raises an error.

---

### R70 — Re-entry prohibition (same setup)
**Status:** ✅ APPROVED

**Rule:** Once a setup has produced an executed entry (reached `POSITION_OPEN`) or has been invalidated/expired/rejected, it may not produce a second entry. No re-entry using the same setup ID is permitted, regardless of outcome.

**Test requirement:** T-R70-1: Second entry attempt on same setup_id is rejected.

---

### R71 — New setup re-entry requirement
**Status:** ✅ APPROVED

**Rule:** A subsequent trade in the same direction requires a **genuinely new eligible setup** — a new FVG, a new confirmed sweep, and completion of the full sequence from stage 1. All risk checks (including the five-entry daily limit) must be passed independently.

**Test requirement:** T-R71-1: New setup correctly treated as independent from prior setup on same symbol.

---

### R72 — Opposite-signal handling
**Status:** ✅ APPROVED

**Rule:** An opposite-direction signal on the same symbol **must never** automatically reverse, close, or modify an existing position. The opposite signal is:
1. Logged independently with its own setup ID.
2. Evaluated against its own risk checks.
3. Blocked from entry by R52 (max 1 concurrent position per symbol) if a position is already open.

Any action involving an existing open position must follow the approved exit rules (SL hit, TP hit) only.

**Test requirement:** T-R72-1: Opposite signal with open position does not close existing position. T-R72-2: Opposite signal logged with own ID.

---

### R73 — Persistence scope
**Status:** ✅ APPROVED

**Rule:** The following must be persisted to SQLite and survive a complete application restart:

- All FVG boundaries, direction, timestamps, and confirmation data
- Sweep records (level, candle time, extreme, direction)
- Reference candle OHLC, timestamp, frozen status, and trigger level
- Gap-exit confirmation status
- Trigger-fired status and timestamp
- Order request IDs (for idempotency)
- Order fill status, fill price, and broker ticket number
- Position open/close status
- Daily trade count and broker day boundary
- All lockout states (daily_loss_lock, daily_trade_lock, news_lock, consecutive_loss_lock)
- Start-of-day equity snapshot

**Test requirement:** T-R73-1: Full state round-trip test — persist, restart, verify state matches pre-restart state.

---

### R74 — Restart reconciliation sequence
**Status:** ✅ APPROVED

**Rule:** After every restart, the engine executes these steps **in order** before resuming monitoring:

1. Connect to MT5 and verify connection.
2. Verify active account login, server name, and that approved symbols are available.
3. Reconcile local order records with MT5 positions and deal history.
4. Restore active setups and risk counters from SQLite.
5. Confirm state is internally consistent (no orphaned pending orders, no missing stops).
6. Resume monitoring only after all steps succeed.

If any step fails, the engine logs the failure, blocks new entries, and alerts the user. It does not attempt to trade in an unreconciled state.

**Test requirement:** T-R74-1: Engine does not emit signals before reconciliation completes. T-R74-2: Failed reconciliation blocks entries.

---

### R75 — Broker/local disagreement handling
**Status:** ✅ APPROVED

**Rule:** If the broker (MT5) and local SQLite database disagree on position status, fill status, or P&L, the engine:
1. Blocks new entries immediately.
2. Logs the exact discrepancy (field, local value, broker value).
3. Alerts the user with `"STATE MISMATCH — new entries blocked pending manual reconciliation"`.
4. Does not auto-resolve the discrepancy.

**Test requirement:** T-R75-1: Entry blocked when local and broker state disagree on open position.

---

### R76 — Timed-out order handling
**Status:** ✅ APPROVED

**Rule:** The engine must **never assume** a timed-out order has failed. A timed-out order request must be reconciled against MT5 deal history and position list before the engine either retries or marks it as failed. Retry uses the original idempotent order client ID (R4 of IMPL4).

**Test requirement:** T-R76-1: Timed-out order triggers reconciliation before retry. T-R76-2: Idempotent retry does not create a second position.

---

### R77–R88 — Rules that must never be used
**Status:** ❌ PROHIBITED

| Rule ID | Prohibition |
|---|---|
| R77 | No legacy strategy rules (from `src/strategy/fvg_detector.py` old logic) unless explicitly re-approved |
| R78 | No future candles, look-ahead bias, or repainting |
| R79 | No unrelated market-structure break used as an extra entry condition |
| R80 | No changing the frozen reference candle or trigger level after confirmation |
| R81 | No entries before the full 10-stage sequence is completed |
| R82 | No duplicate order submissions for the same setup |
| R83 | No position sizing that exceeds the approved 1% risk |
| R84 | No trades without a valid, broker-confirmed protective stop |
| R85 | No silent fallback to arbitrary lot sizes or fabricated prices |
| R86 | No automatic loss-recovery by increasing position size |
| R87 | No trailing stops, partial exits, break-even moves, or reversal logic (R43) |
| R88 | No real-money orders during development |

---

## 3. Implementation Rules (IMPL)

---

### IMPL1 — Deterministic engine interface
**Status:** ✅ APPROVED

**Rule:** The strategy core is a **pure function** of:
- A list of completed candles (no live bar)
- The approved strategy configuration (from `StrategySettings`)
- The current setup state (from SQLite)

It must not read the computer clock, call MT5 directly, or use any randomness for trading decisions. Clock values required for logging are injected from the caller.

---

### IMPL2 — Decision log fields
**Status:** ✅ APPROVED

**Rule:** For every decision, record:

| Field | Content |
|---|---|
| `spec_version` | `"1.0"` |
| `spec_hash` | SHA-256 of `STRATEGY_SPEC.md` (set after first Git commit) |
| `git_commit` | Short commit SHA at runtime |
| `symbol` | Resolved broker symbol name |
| `timeframe` | `"H1"` |
| `candles_evaluated` | List of (time, OHLCV) for all candles used |
| `setup_id` | SHA-256 derived setup ID |
| `prev_state` | Setup state before this evaluation |
| `new_state` | Setup state after this evaluation |
| `rules_evaluated` | List of rule IDs evaluated |
| `rule_results` | Per-rule: `{rule_id, passed, actual_value, threshold, explanation}` |
| `final_decision` | `"SIGNAL" / "REJECTED" / "EXPIRED" / "NO_ACTION"` |
| `decision_reason` | Human-readable explanation |
| `spread_at_decision` | Live spread in pips at decision time |
| `quote_timestamp` | MT5 tick timestamp used |
| `risk_checks` | All R32 check results |

The decision log is written to SQLite **before** any order submission attempt.

---

### IMPL3 — State machine states
**Status:** ✅ APPROVED

Required states (extending existing `SetupState` enum):

```
FVG_DETECTED
SWEEP_CONFIRMED
WAITING_FOR_RETRACEMENT
REFERENCE_CANDLE_SAVED
WAITING_FOR_GAP_EXIT       ← renamed from old WAITING_FOR_GAP_EXIT; semantics clarified
GAP_EXITED                 ← NEW: replaces ambiguous old naming
WAITING_FOR_TRIGGER
SIGNAL_READY
RISK_CHECK
ORDER_PENDING
POSITION_OPEN
CLOSED                     [terminal]
EXPIRED                    [terminal]
INVALIDATED                [terminal]
REJECTED                   [terminal]
```

The old `WAITING_FOR_GAP_EXIT` state is renamed `GAP_EXITED` to accurately describe the condition (gap has been exited; transition to trigger monitoring). The DB migration must handle the rename.

---

### IMPL4 — Order idempotency
**Status:** ✅ APPROVED

**Rule:** Every order request carries a **deterministic client order ID** derived from `setup_id` and attempt number (using `order_client_id()` from `src/utils/ids.py`). If the same client ID is submitted twice, MT5 returns the original response; the engine does not open a second position.

A timed-out order is never retried with a new client ID until reconciliation confirms it did not fill.

---

### IMPL5 — MT5 error handling
**Status:** ✅ APPROVED

**Rule:** The engine handles all MT5 error conditions explicitly:

| Condition | Action |
|---|---|
| Retcode not `TRADE_RETCODE_DONE` | Log retcode + description, mark order failed, alert |
| Partial fill | Log partial fill, block further entries for this setup |
| Rejected stop-loss | See R39 |
| Insufficient margin | Reject trade, log, alert |
| Disconnected terminal | Block new entries, alert, retry connection |
| Stale price | Block new entries until fresh quote |
| Market closed | Block new entries, log market state |
| Unexpected account change | Block new entries, alert, require reconciliation |

"Order successful" is only reported after `TRADE_RETCODE_DONE` or equivalent confirmed retcode.

---

### IMPL6 — Bot pause safety
**Status:** ✅ APPROVED

**Rule:** When the engine is paused (operator command or automatic lockout):
1. No new entry signals are generated or submitted.
2. Existing open positions retain their broker-side protective stops unchanged.
3. The engine continues to receive and log MT5 position updates.
4. The dashboard shows the paused state prominently.

An emergency stop blocks new submissions immediately, without requiring an internet connection to Supabase. The local SQLite `emergency_stop` flag is checked before every order submission.

---

### IMPL7 — Execution mode isolation
**Status:** ✅ APPROVED

**Rule:**

| Mode | Description | Order submission |
|---|---|---|
| `PAPER` | Simulated fills, `PaperExecutor` only | `PaperExecutor` — no MT5 order call |
| `DEMO` | Real fills on MT5 demo account | MT5 order API (demo account only) |
| `LIVE` | Disabled | Blocked at validator — raises exception |

Paper mode is **structurally isolated**: `PaperExecutor` does not import `MetaTrader5` and cannot call its order functions. This is an architectural enforcement, not just a flag check.

Demo mode may only be enabled after all required tests pass and owner approval is received.

Live mode remains permanently disabled in this release.

---

### IMPL8 — Engine/dashboard communication
**Status:** ✅ APPROVED

**Rule:**
- MT5 is the source of truth for balance, equity, positions, and deals.
- The engine sends authenticated outbound events to Supabase.
- Events are buffered locally when offline and replayed in sequence after reconnection.
- Every event has a monotonically increasing `sequence_number` and `idempotency_key`.
- Server timestamps are used; clock skew between local and server is detected and logged.
- UI values that cannot be verified display as `"Unknown"`, not `0` or stale cached values.
- Stale values are labelled with their last update time.

---

### IMPL9 — Dashboard status thresholds
**Status:** 🔶 PROPOSED DEFAULT

| Status | Condition |
|---|---|
| `ONLINE` | Last heartbeat < 15 seconds ago |
| `STALE` | Last heartbeat 15–60 seconds ago |
| `OFFLINE` | Last heartbeat > 60 seconds ago |

**Configurable parameters:** `heartbeat_online_secs` (default `15`), `heartbeat_offline_secs` (default `60`).

When `OFFLINE`, the dashboard shows a prominent warning: `"Engine not reporting — positions protected only by broker-side stops"`.

---

### IMPL10 — Command lifecycle
**Status:** ✅ APPROVED

**Rule:** Dashboard commands (PAUSE, RESUME, FLATTEN, KILL) require:
1. Authentication (valid JWT, not expired).
2. Authorization (user has the required role).
3. Expiry (command rejected if older than `command_ttl_seconds`, default `30`).
4. Audit record written before execution.
5. Confirmed outcome before status reported as `DONE`.
6. If engine is offline when command is received, command is queued and labelled `"QUEUED — not yet executed"`.

---

### IMPL11 — Credential storage
**Status:** ✅ APPROVED

**Rule:**
- MT5 trading passwords are stored in Windows Credential Manager (`keyring` library) only.
- MT5 passwords must never appear in: Supabase, Vercel environment variables, browser local storage, application logs, or any file in the repository.
- The `APISettings.secret_key` must be set via the `API_SECRET_KEY` environment variable. The placeholder default must cause a startup warning.

---

## 4. Rule-to-Test Coverage Map

| Rule ID | Required Tests |
|---|---|
| R1 | T-R1-1, T-R1-2 |
| R2 | T-R2-1 |
| R3 | T-R3-1, T-R3-2 |
| R4 | T-R4-1, T-R4-2 |
| R5 | T-R5-1, T-R5-2 |
| R6 | T-R6-1, T-R6-2 |
| R7 | T-R7-1 |
| R8 | T-R8-1, T-R8-2, T-R8-3, T-R8-4 |
| R9 | T-R9-1, T-R9-2, T-R9-3 |
| R10 | T-R10-1, T-R10-2 |
| R11 | T-R11-1, T-R11-2, T-R11-3 |
| R12 | T-R12-1, T-R12-2, T-R12-3 |
| R13 | T-R13-1, T-R13-2 |
| R14 | T-R14-1, T-R14-2 |
| R15 | T-R15-1, T-R15-2, T-R15-3, T-R15-4 |
| R16 | T-R16-1, T-R16-2, T-R16-3 |
| R17 | T-R17-1, T-R17-2 |
| R18 | T-R18-1 |
| R19 | T-R19-1, T-R19-2 |
| R20 | T-R20-1, T-R20-2 |
| R21 | T-R21-1, T-R21-2, T-R21-3 |
| R22 | T-R22-1, T-R22-2 |
| R23 | T-R23-1, T-R23-2 |
| R24 | T-R24-1, T-R24-2 |
| R25 | T-R25-1, T-R25-2 |
| R26 | T-R26-1, T-R26-2, T-R26-3 |
| R27–R28 | (covered by R29, R30 tests) |
| R29 | T-R29-1, T-R29-2, T-R29-3 |
| R30 | T-R30-1, T-R30-2, T-R30-3 |
| R31 | T-R31-1, T-R31-2 |
| R32 | T-R32-1 through T-R32-17 |
| R33 | T-R33-1, T-R33-2, T-R33-3, T-R33-4 |
| R34 | T-R34-1, T-R34-2 |
| R35 | T-R35-1, T-R35-2 |
| R36 | T-R36-1, T-R36-2, T-R36-3 |
| R37 | T-R37-1, T-R37-2 |
| R38 | (mutation test — verify stop widening raises error) |
| R39 | T-R39-1, T-R39-2 |
| R40 | T-R40-1, T-R40-2 |
| R41 | T-R41-1, T-R41-2 |
| R42 | T-R42-1, T-R42-2 |
| R43 | (mutation test — verify disabled features raise NotImplementedError) |
| R44 | T-R44-1, T-R44-2 |
| R45 | T-R45-1, T-R45-2, T-R45-3 |
| R46 | T-R46-1, T-R46-2 |
| R47 | T-R47-1, T-R47-2 |
| R48 | T-R48-1, T-R48-2 |
| R49 | (mutation test) |
| R50 | T-R50-1, T-R50-2, T-R50-3 |
| R51 | T-R51-1, T-R51-2 |
| R52 | T-R52-1, T-R52-2 |
| R53 | T-R53-1, T-R53-2 |
| R54 | T-R54-1, T-R54-2, T-R54-3 |
| R55 | T-R55-1, T-R55-2 |
| R56 | T-R56-1, T-R56-2 |
| R57 | T-R57-1, T-R57-2 |
| R58 | T-R58-1, T-R58-2, T-R58-3, T-R58-4 |
| R59 | T-R59-1, T-R59-2 |
| R60 | T-R60-1 |
| R61 | T-R61-1, T-R61-2 |
| R62 | T-R62-1, T-R62-2 |
| R63 | T-R63-1 |
| R64 | T-R64-1, T-R64-2 |
| R65 | T-R65-1, T-R65-2 |
| R66–R68 | T-R67-1, T-R67-2, T-R68-1, T-R68-2 |
| R69 | T-R69-1 |
| R70 | T-R70-1 |
| R71 | T-R71-1 |
| R72 | T-R72-1, T-R72-2 |
| R73 | T-R73-1 |
| R74 | T-R74-1, T-R74-2 |
| R75 | T-R75-1 |
| R76 | T-R76-1, T-R76-2 |
| R77–R88 | Mutation tests for each prohibition |

Total required tests: **≥ 120 named tests** before Phase 7 (demo execution) is unlocked.

---

## 5. Versioning and Hash Policy

1. This file is version `1.0`. Any change to a rule requires a version increment and owner approval.
2. After the first Git commit containing this file, compute:
   ```
   SHA256(STRATEGY_SPEC.md) → SPEC_HASH
   ```
3. Record `SPEC_HASH` and the Git commit SHA in:
   - Every `SetupTransition.explanation` (header line)
   - Every `JournalEntry` where `event_type = "SIGNAL"`
   - Every backtest result file header
   - Every decision log record (IMPL2)
4. The hash is not established until this file is committed. It is `NOT_YET_ESTABLISHED` until then.
5. Owner must explicitly say `"I approve version 1.0"` before the hash is locked and implementation begins.

---

## 6. Open Questions Remaining

All strategy open questions (OQ-1 through OQ-27) from the draft spec have been resolved by the owner's Part 1 and Part 2 messages. The following engineering decisions remain open and require answers before the phases they block:

| # | Question | Blocks |
|---|---|---|
| EQ-1 | What are the actual Exness XAUUSD and BTCUSD broker symbol names on this account (may have suffixes)? | Phase 2 — symbol validation |
| EQ-2 | What is the Exness server name used for the active account? | Phase 2 — connection |
| EQ-3 | What is the Exness broker trading day boundary time (server time offset vs UTC)? | R51 — daily counter |
| EQ-4 | What spread values are typical on the Exness demo account for XAUUSD and BTCUSD during active trading hours? | R59 — spread limit configuration |
| EQ-5 | What is the BTCUSD availability schedule on this Exness account? | R61 — session filter |
| EQ-6 | Should the `GAP_EXITED` state rename be applied via an Alembic migration (breaking change) or backward-compatible addition? | Phase 6 — SQLite persistence |
| EQ-7 | Is Supabase still the intended backend for engine-to-dashboard communication, or has that changed? (Nothing in the repo points to Supabase.) | Phase 8 |
| EQ-8 | Is the PySide6 desktop UI still required alongside the Next.js dashboard, or is the dashboard web-only? | Phase 9 |

---

*End of STRATEGY_SPEC.md v1.0*

---

## New Rules — v1.1: Break-Even and ATR Trailing Stop

---

### R89 — Break-even trigger condition
**Status:** ✅ APPROVED

**Rule:** The break-even move is triggered when the floating price has travelled at least **50% of the distance from the entry price to the take-profit price** in the favourable direction.

```
For a BULLISH position:
  progress = (current_bid - entry_price) / (tp_price - entry_price)
  trigger fires when progress >= 0.50

For a BEARISH position:
  progress = (entry_price - current_ask) / (entry_price - tp_price)
  trigger fires when progress >= 0.50
```

- Evaluation uses the **candle close price** of a completed H1 bar (R3 — no live tick during strategy decisions).
- The trigger fires **at most once per position** (R90 handles subsequent trailing).
- Progress is clamped to [0.0, 1.0]. A value ≥ 1.0 means TP was reached, not break-even.

**Configurable parameter:** `breakeven_trigger_pct` (default `0.50`) in `RiskSettings`.

**This threshold is not claimed to be optimal.**

**Required inputs:** entry price, TP price, candle close price, position direction
**Expected outcome:** Break-even move initiated when threshold crossed on candle close
**Rejection:** If SL is already at or above entry (bullish) or at or below entry (bearish), skip — already at break-even or better

**Test requirement:** T-R89-1: Break-even fires at exactly 50% progress (bullish). T-R89-2: Break-even fires at exactly 50% progress (bearish). T-R89-3: Break-even does not fire below 50%. T-R89-4: Break-even skipped if SL already at entry.

---

### R90 — Break-even stop placement
**Status:** ✅ APPROVED

**Rule:** When R89 triggers, the stop-loss is moved to the **exact entry price**:

```
new_sl = entry_price   (for both BULLISH and BEARISH)
```

- The stop is rounded to the nearest valid `symbol_info.tick_size` increment toward the entry (conservative rounding — never beyond entry).
- The new SL must satisfy the broker's minimum stop-distance (`trade_stops_level`). If it does not (because entry is too close to current price), the move is deferred until the distance is valid.
- The original SL is recorded before the move for audit purposes.

**Risk acknowledgement:** Moving the stop to entry does not guarantee a break-even exit. A gap or sudden spike can cause a fill beyond the stop level, resulting in a loss. The owner has acknowledged this (BEQ-6).

**Test requirement:** T-R90-1: SL set to exact entry price on trigger. T-R90-2: SL rounded toward entry when needed. T-R90-3: Move deferred when broker minimum stop distance not satisfied.

---

### R91 — Break-even broker verification
**Status:** ✅ APPROVED

**Rule:** After submitting the stop-loss modification to the broker (MT5), the engine must verify the new stop is accepted before declaring the position protected at the new level.

If MT5 rejects the SL modification:
1. Log the rejection with retcode and details.
2. Retry up to `max_sl_retry` times (default `3`, R39).
3. If all retries fail, raise a `CRITICAL` alert: `"BREAK-EVEN STOP REJECTED — position still protected at original SL {original_sl}"`.
4. The position remains protected at the original SL. Do not mark it as at break-even.

In **paper mode**, the stop modification is applied to the paper ledger directly. Broker confirmation is simulated as always-successful.

**Test requirement:** T-R91-1: Alert raised on rejection. T-R91-2: Original SL retained if modification fails. T-R91-3: Paper mode always succeeds.

---

### R92 — ATR trailing stop — activation
**Status:** ✅ APPROVED

**Rule:** After the break-even stop has been successfully placed (R90 + R91), the ATR trailing stop becomes **active** for that position. It replaces break-even as the active stop management mode.

The trailing stop is only active when:
1. The position is open (`POSITION_OPEN` state).
2. The break-even trigger has already fired and was confirmed by the broker.
3. Current price progress toward TP is > 50% (trailing never moves the stop backward).

**Test requirement:** T-R92-1: Trailing not active before break-even fires. T-R92-2: Trailing activates immediately after break-even confirmation.

---

### R93 — ATR trailing stop — distance
**Status:** 🔶 PROPOSED DEFAULT

**Rule:** The trailing stop distance is `1.0 × ATR(14)` computed from the most recent **completed H1 candles** at the time of evaluation:

```
For BULLISH:
  trail_sl = highest_close_since_entry - (1.0 × ATR(14))

For BEARISH:
  trail_sl = lowest_close_since_entry  + (1.0 × ATR(14))
```

- `highest_close_since_entry` / `lowest_close_since_entry` is the most favourable **candle close** seen since the position opened (not the intrabar wick).
- The trail distance is recomputed on every H1 candle close using the current ATR.
- The trailing stop **only moves in the favourable direction** — it never moves against the position.

**Configurable parameter:** `trailing_atr_factor` (default `1.0`) in `RiskSettings`.

**This distance is not claimed to be optimal.** It scales with volatility which is suitable for instruments like XAUUSD and BTCUSD.

**Test requirement:** T-R93-1: Trail computed as highest_close - 1×ATR (bullish). T-R93-2: Trail computed as lowest_close + 1×ATR (bearish). T-R93-3: ATR recomputed from latest candles on each evaluation. T-R93-4: Trail never moves backward.

---

### R94 — ATR trailing stop — evaluation timing
**Status:** ✅ APPROVED

**Rule:** The trailing stop is evaluated **once per completed H1 candle close** only. Live ticks are never used to evaluate or move the trailing stop. This is consistent with R3 (completed candles only for strategy decisions) and avoids stop-hunting by tick noise.

**Test requirement:** T-R94-1: Trail not evaluated on tick. T-R94-2: Trail evaluated exactly once per H1 close.

---

### R95 — ATR trailing stop — broker verification
**Status:** ✅ APPROVED

**Rule:** Every trailing stop modification follows the same broker verification process as the original SL (R39) and the break-even move (R91):

1. Submit the SL modification to MT5.
2. Verify MT5 confirms the new stop level.
3. Update the persisted `current_sl` only after confirmation.
4. If rejected, retain the previous stop level and log the failure. Do not treat the position as protected at the new level.

In **paper mode**, the modification is applied directly to the paper ledger.

**Test requirement:** T-R95-1: Trailing SL only updated after broker confirms. T-R95-2: Previous SL retained on rejection.

---

### R96 — Trail / break-even prohibition override
**Status:** ✅ APPROVED

**Rule:** The following remain permanently prohibited even with trailing stop active:

- The trailing stop may **never** move the SL in the direction that increases risk (i.e. away from entry after break-even is set).
- The trailing stop is **not** a partial take-profit, scale-out, or reversal.
- The trailing stop does **not** trigger a new entry in the opposite direction.
- The trailing stop activation does **not** change the original `proposed_tp` level — the position still closes at TP if hit first.

**Test requirement:** T-R96-1: SL never moves against position after break-even. T-R96-2: TP remains unchanged when trailing activates.

---

*End of STRATEGY_SPEC.md v1.1*


---

## New Rules — v1.2: Multi-Timeframe Analysis, Market Clarity Engine, Two-Position Execution

---

### R97 — H4 trend filter
**Status:** ✅ APPROVED

**Rule:** Before a setup can advance past SWEEP_CONFIRMED, the H4 chart must confirm macro directional alignment. H4 trend is defined by confirmed swing structure:

- **Bullish H4 trend:** The most recent confirmed H4 swing low is higher than the one before it AND the most recent confirmed H4 swing high is higher than the one before it (higher highs + higher lows).
- **Bearish H4 trend:** Lower highs + lower lows on H4 confirmed swings.

H4 swings are confirmed using the same pivot method (R12) with `pivot_left_bars=2, pivot_right_bars=2` applied to H4 candles.

A **bullish H1 setup** requires a bullish H4 trend. A **bearish H1 setup** requires a bearish H4 trend. If H4 trend is neutral (insufficient swing data) or opposite to the H1 setup, the setup is **rejected** with reason `"H4 trend does not confirm H1 direction (R97)"`.

**Configurable parameter:** `h4_trend_filter_enabled` (default `True`).

**Test requirement:** T-R97-1: Bullish setup rejected when H4 shows lower highs/lows. T-R97-2: Bullish setup approved when H4 shows higher highs/lows. T-R97-3: Filter correctly disabled when h4_trend_filter_enabled=False.

---

### R98 — M15 entry trigger
**Status:** ✅ APPROVED

**Rule:** When `entry_timeframe = "M15"` (the new default), the entry trigger fires on a completed **M15 candle close** beyond the frozen reference candle's trigger level, instead of waiting for an H1 candle close (R29).

The reference candle and trigger level are still identified on H1 (R21–R24). The M15 trigger is evaluated every time a completed M15 candle closes beyond that level.

All other entry pre-checks (R32 checklist) still apply.

**Configurable parameter:** `entry_timeframe` (default `"M15"`, alternative `"H1"` for backward compatibility).

**Test requirement:** T-R98-1: M15 trigger fires on M15 candle close beyond H1 trigger level. T-R98-2: H1 trigger still works when entry_timeframe="H1". T-R98-3: M15 trigger does not fire before gap exit is confirmed.

---

### R99 — Market Clarity Score definition
**Status:** ✅ APPROVED

**Rule:** The Market Clarity Score (MCS) is an integer from 0 to 100 computed from the quality of the current setup. It evaluates existing conditions — it does not independently generate entries.

**A high MCS is not a probability of winning.** It must never be displayed as such.

Scoring components (sum = 100 points maximum):

| # | Component | Points | Condition |
|---|---|---|---|
| MCS-1 | Valid H1 FVG | 20 | FVG confirmed, size filter passes |
| MCS-2 | Confirmed liquidity sweep | 20 | Sweep confirmed with close-back (R15/R16) |
| MCS-3 | Confirmed structure break | 20 | Trigger level broken on M15 or H1 close |
| MCS-4 | Sufficient distance to opposing liquidity | 15 | TP1 distance ≥ 2 × SL distance (structural target exists) |
| MCS-5 | Strong displacement candle | 10 | Sweep candle body ≥ 60% of candle range |
| MCS-6 | H4 directional alignment | 10 | H4 trend confirmed (R97) |
| MCS-7 | Spread and volatility | 5 | Spread within configured limit AND ATR within normal range |

**Configurable thresholds:**

| Threshold | Default | Meaning |
|---|---|---|
| `clarity_reject_below` | 60 | Score < 60 → reject setup |
| `clarity_one_position` | 60 | 60–74 → one position only |
| `clarity_two_positions` | 75 | 75–84 → two positions if TP2 qualifies |
| `clarity_high_confluence` | 85 | 85–100 → high-confluence, all checks mandatory |

**Test requirement:** T-R99-1: Each component scored independently. T-R99-2: Setup rejected when score < 60. T-R99-3: Two positions only when score ≥ 75.

---

### R100 — Setup quality grade
**Status:** ✅ APPROVED

**Rule:** The setup quality grade is derived from the Market Clarity Score:

| Grade | MCS range | Risk allocation |
|---|---|---|
| A | 85–100 | 1.5% of equity |
| B | 60–84 | 1.0% of equity |
| C | < 60 | Setup rejected — 0% |

**Configurable parameters:**
- `grade_a_min_score` (default `85`)
- `grade_b_min_score` (default `60`)
- `grade_a_risk_pct` (default `1.5`)
- `grade_b_risk_pct` (default `1.0`)
- `grade_a_risk_pct_max` (default `1.5`) — absolute maximum regardless of grade

**These percentages are proposed defaults, not proven optimal values.**

**Test requirement:** T-R100-1: Grade A assigned at score ≥ 85. T-R100-2: Grade B assigned at score 60–84. T-R100-3: Grade A allocates 1.5% risk. T-R100-4: Grade B allocates 1.0% risk.

---

### R101 — Opposing market structure detection
**Status:** ✅ APPROVED

**Rule:** Before opening a trade, the engine identifies the next meaningful opposing market structure on H1.

For **bullish setups**, identify:
1. The nearest confirmed H1 swing high above the entry price.
2. Buy-side liquidity above that swing high.
3. Any bearish H1 FVG between entry and the swing high.
4. The most conservative of these as the structural barrier.

For **bearish setups**, identify:
1. The nearest confirmed H1 swing low below the entry price.
2. Sell-side liquidity below that swing low.
3. Any bullish H1 FVG between entry and the swing low.
4. The most conservative of these as the structural barrier.

Rules:
- Do not use arbitrary pip distances as substitutes for market structure.
- Place TP preferably **before** the opposing zone (not inside it).
- If no valid opposing structure can be identified, set `tp1_structural = None` and fall back to minimum-RR-based TP only.
- The detection is deterministic, reproducible, and logged with the candle timestamps of the identified structure.

**Test requirement:** T-R101-1: Nearest swing high identified correctly. T-R101-2: TP placed before opposing zone when structure exists. T-R101-3: Returns None when no structure found.

---

### R102 — TP1 calculation (structural)
**Status:** ✅ APPROVED

**Rule:** TP1 is the first exit target.

Calculation order:
1. Identify the nearest opposing structural barrier (R101).
2. Place TP1 **2 ticks before** the structural barrier (conservative — avoid placing inside the zone).
3. Verify TP1 satisfies minimum 1:2 R:R against the setup SL.
4. If structural TP1 < minimum-RR TP, use the minimum-RR TP instead.
5. If minimum-RR TP is still not achievable (SL too wide for the available structure), **reject the setup** with reason `"TP1 below minimum 1:2 R:R"`.

**Configurable parameter:** `tp1_min_rr` (default `2.0`).

**Test requirement:** T-R102-1: TP1 placed before structural barrier. T-R102-2: TP1 satisfies 1:2 minimum. T-R102-3: Setup rejected when TP1 cannot be achieved.

---

### R103 — TP2 calculation (structural)
**Status:** ✅ APPROVED

**Rule:** TP2 is the second exit target, used only when two-position execution is active.

Calculation order:
1. Beyond TP1, identify the next meaningful opposing structural barrier (second swing high/low, second FVG, or major liquidity zone).
2. Place TP2 **2 ticks before** that second barrier.
3. Verify TP2 satisfies minimum 1:3 R:R.
4. TP2 must not be calculated by blindly extending TP1 by a fixed distance.
5. If TP2 cannot be reliably identified or does not meet 1:3 R:R, **TP2 = None** and two-position execution falls back to one-position.

**Configurable parameter:** `tp2_min_rr` (default `3.0`).

**Test requirement:** T-R103-1: TP2 requires identifiable second structure. T-R103-2: TP2 satisfies 1:3 minimum. T-R103-3: Falls back to one position when TP2 not available.

---

### R104 — Two-position activation conditions
**Status:** ✅ APPROVED

**Rule:** Two positions may be opened for a single setup only when ALL of the following are true simultaneously:

1. Existing strategy entry signal is valid (full sequence R19 complete).
2. Market Clarity Score ≥ 75 (R99).
3. TP1 qualifies at minimum 1:2 R:R (R102).
4. TP2 qualifies at minimum 1:3 R:R (R103).
5. TP2 distance ≥ 3 × ATR(14) from entry (market is "clear" — TF-7).
6. Total combined risk ≤ grade risk budget (R100).
7. Broker execution conditions are valid (spread, margin, symbol).
8. No duplicate setup exists for this symbol.
9. Daily limits and lockouts pass (R50, R54, R58).
10. `two_position_mode_enabled = True` in settings.

If ANY condition fails → fall back to one position (if MCS ≥ 60) or reject (if MCS < 60).

**Configurable parameter:** `two_position_mode_enabled` (default `True`), `tp2_min_atr_distance` (default `3.0`).

**Test requirement:** T-R104-1 through T-R104-10: One test per condition that confirms fallback to one position when that condition alone fails.

---

### R105 — Position A specification
**Status:** ✅ APPROVED

**Rule:**
- Entry: same strategy entry price as defined by R14.
- SL: same structural SL as defined by R35/R36.
- TP: TP1 (R102).
- Risk allocation: 50% of total setup risk budget (e.g. 0.5% when grade B budget is 1.0%).
- Volume: calculated using 50% risk allocation with full broker symbol specs (R45/R46).

---

### R106 — Position B specification
**Status:** ✅ APPROVED

**Rule:**
- Entry: same strategy entry price as Position A.
- SL: same structural SL as Position A.
- TP: TP2 (R103).
- Risk allocation: 50% of total setup risk budget.
- Volume: calculated using 50% risk allocation.
- Position B uses the same setup ID as Position A — they are one setup with two exits.

**Test requirement:** T-R106-1: Position A and B share setup_id. T-R106-2: Total risk ≤ grade budget.

---

### R107 — Total risk budget enforcement
**Status:** ✅ APPROVED

**Rule:** The combined monetary risk of Position A and Position B must never exceed the grade risk budget:

```
position_a_risk + position_b_risk ≤ equity × grade_risk_pct / 100
```

If rounding causes a fractional overage, reduce Position B volume, not Position A.

**Test requirement:** T-R107-1: Combined risk never exceeds grade budget. T-R107-2: Position B volume reduced when budget would be exceeded.

---

### R108 — Execution reconciliation for two positions
**Status:** ✅ APPROVED

**Rule:** Position A and Position B are submitted as independent orders with independent client order IDs (IMPL4). Each submission is independently confirmed.

If Position A fills but Position B fails:
1. Do NOT automatically retry Position B.
2. Reconcile actual broker positions.
3. Log partial execution with exact MT5 retcodes.
4. Position A remains open with its SL and TP confirmed.
5. Alert: `"PARTIAL EXECUTION: Position A filled, Position B failed — {reason}"`.
6. Apply configured recovery policy (default: leave Position A open, do not retry B).

**Configurable parameter:** `partial_execution_policy` (`"leave_a_open"` default; `"close_a_if_b_fails"` alternative).

**Test requirement:** T-R108-1: Position A left open when B fails (default policy). T-R108-2: Alert raised on partial execution. T-R108-3: No retry of B without explicit trigger.

---

### R109 — Break-even after TP1 hit (two-position mode)
**Status:** ✅ APPROVED

**Rule:** When Position A closes at TP1, the engine may optionally move Position B's SL to break-even (entry price ± configured offset).

Rules:
- This move is separate from the R89 break-even trigger (which fires at 50% of TP distance).
- The offset is configurable: `be_offset_after_tp1` (default `2 × tick_size` beyond entry, toward TP).
- The move requires broker confirmation (R91).
- Never widens Position B's original risk.

**Configurable parameter:** `move_b_to_be_after_tp1` (default `True`), `be_offset_after_tp1_ticks` (default `2`).

**Test requirement:** T-R109-1: Position B SL moves to entry + offset when A closes at TP1. T-R109-2: Move skipped when disabled. T-R109-3: SL never moves against Position B.

---

### R110 — Daily setup counter (two-position mode)
**Status:** ✅ APPROVED

**Rule:** One setup (regardless of how many positions it generates) counts as **one entry** toward the daily 5-trade limit (R50). Opening Position A and Position B from the same setup is counted as **one new entry**, not two.

The daily limit applies **per symbol independently** (TF-6 confirmed).

**Test requirement:** T-R110-1: Two positions from one setup count as one daily entry. T-R110-2: XAUUSD and BTCUSD daily limits are independent.

---

### R111–R130 — Backtesting modes
**Status:** ✅ APPROVED

Three backtesting modes are defined (Part 11 of the implementation spec):

| Mode | Description |
|---|---|
| MODE A | One position, TP at 1:2 |
| MODE B | Two positions: Position A TP=1:2, Position B TP=1:3 or structural TP2 |
| MODE C | One position with optional trailing stop after break-even |

Each mode must produce a report including: number of trades, win rate, average R, profit factor, net profit after costs, max drawdown, longest losing streak, TP1 hit rate, TP2 hit rate, expectancy, spread impact, commission impact, slippage impact, performance by session, performance by volatility regime.

No look-ahead bias, repainting, or unrealistic fill assumptions.

Separate in-sample, out-of-sample, and walk-forward evaluation.

---

*End of STRATEGY_SPEC.md v1.2*
