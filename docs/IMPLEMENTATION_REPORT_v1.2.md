# Implementation Report — v1.2
**Date:** 2026-10-17
**Spec version:** STRATEGY_SPEC.md v1.2
**Status:** Phase complete — unit tests written, no live trading enabled

---

## Audit findings (preserved from Phase 0)

All existing components confirmed intact:
- `src/strategy/strategy_core.py` — FVG detection, swing detection, liquidity sweep, reference candle, gap exit, entry trigger, SL/TP calculators, break-even/trailing
- `src/state/state_machine.py` — 12-stage state machine, all transitions persisted
- `src/risk/engine.py` — position sizing, daily limits, lockouts
- `src/execution/paper_executor.py` — paper mode isolation (no MT5 import)

No existing strategy logic was changed or removed.

---

## New files created

| File | Purpose |
|---|---|
| `src/strategy/market_clarity.py` | Market Clarity Engine — scores 0–100, R97–R100 |
| `src/strategy/structural_tp.py` | Structural TP1/TP2 detection from market structure, R101–R103 |
| `src/execution/two_position_executor.py` | Two-position planner and sizer, R104–R110 |
| `tests/unit/test_market_clarity.py` | 20 tests for R97–R100 |
| `tests/unit/test_structural_tp.py` | 12 tests for R101–R103 |
| `tests/unit/test_two_position_executor.py` | 18 tests for R104–R110 |

---

## Files modified

| File | Change |
|---|---|
| `STRATEGY_SPEC.md` | v1.1 → v1.2, rules R97–R130 added |
| `src/config/settings.py` | 20 new configuration parameters added |
| `src/state/models.py` | `Setup` ORM: clarity_score, grade, tp1/tp2_structural, h4_trend fields; SPEC_VERSION → 1.2 |
| `src/strategy/strategy_core.py` | SPEC_VERSION → 1.2 |

---

## Architecture of the new system

```
H4 candles ──► H4 Trend Detector (R97)
                        │ BULLISH/BEARISH/NEUTRAL
                        ▼
H1 candles ──► FVG + Sweep + RefCandle (existing, R5–R25)
                        │ setup confirmed
                        ▼
M15 candles ──► Entry Trigger (R98) — M15 candle close
                        │ trigger fired
                        ▼
             Market Clarity Engine (R99)
             ┌─────────────────────────────┐
             │ MCS-1: FVG valid       20pt │
             │ MCS-2: Sweep confirmed 20pt │
             │ MCS-3: Structure break 20pt │
             │ MCS-4: Distance to opp 15pt │
             │ MCS-5: Displacement    10pt │
             │ MCS-6: H4 alignment    10pt │
             │ MCS-7: Spread/vol       5pt │
             └────────────── total 0–100 ──┘
                        │ score ≥ 60
                        ▼
             Setup Grade (R100)
             │ A (85–100): 1.5% risk
             │ B (60–84):  1.0% risk
             │ C/rejected: 0%
                        │
                        ▼
             Structural TP Detection (R101–R103)
             │ TP1 from nearest swing/FVG barrier ≥ 1:2 RR
             │ TP2 from next barrier ≥ 1:3 RR AND ≥ 3×ATR distance
                        │
                        ▼
             Two-Position Planner (R104–R107)
             │ score ≥ 75 AND TP2 valid → 2 positions
             │ score 60–74 OR TP2 invalid → 1 position
             │ score < 60 → reject
             │
             ├── Position A: 50% budget, TP=TP1
             └── Position B: 50% budget, TP=TP2
                        │
                        ▼
             Execution (paper/demo)
             + Daily counter: one setup = one daily entry (R110)
             + Break-even after TP1 hit (R109)
```

---

## Configuration parameters (all in `StrategySettings` or `RiskSettings`)

| Parameter | Default | Rule | Configurable |
|---|---|---|---|
| `h4_trend_filter_enabled` | `True` | R97 | Yes |
| `entry_timeframe` | `"M15"` | R98 | Yes |
| `clarity_reject_below` | `60` | R99 | Yes |
| `clarity_two_positions` | `75` | R99 | Yes |
| `grade_a_min_score` | `85` | R100 | Yes |
| `grade_a_risk_pct` | `1.5%` | R100 | Yes |
| `grade_b_risk_pct` | `1.0%` | R100 | Yes |
| `tp1_min_rr` | `2.0` | R102 | Yes |
| `tp2_min_rr` | `3.0` | R103 | Yes |
| `tp2_min_atr_distance` | `3.0×ATR` | R104/TF-7 | Yes |
| `two_position_mode_enabled` | `True` | R104 | Yes |
| `move_b_to_be_after_tp1` | `True` | R109 | Yes |
| `max_open_per_symbol` | `2` | R104 | Yes |

**All defaults are proposed initial values. None are claimed to be profitable or optimal.**

---

## Known open items

1. **M15 candle fetching** — `MT5DataAdapter.get_candles()` supports any timeframe string including `"M15"`. The engine loop currently runs every 60 seconds; for M15 precision it should be triggered every 15 minutes or on new candle close. The scheduler interval in `main.py` needs to be reduced to `minutes=15` when `entry_timeframe="M15"`.

2. **Engine wiring** — `MarketClarityEngine`, `StructuralTPDetector`, and `TwoPositionPlanner` are built but not yet called from `trading_engine.py`. Integration into the engine evaluation loop is the next task.

3. **Dashboard** — The new fields (`clarity_score`, `grade`, `tp1_structural`, `tp2_structural`, `h4_trend`, `positions_permitted`) are stored in the ORM and will appear in the `/setups/{id}` API response. The frontend signal card needs updating to show these fields.

4. **Backtest modes A/B/C** — The backtest runner (`src/backtest/runner.py`) needs to be extended with the three modes defined in R111–R130.

---

## Tests

Run with:
```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"
.\.venv\Scripts\Activate.ps1
python -m pytest tests/unit/test_market_clarity.py tests/unit/test_structural_tp.py tests/unit/test_two_position_executor.py -v
```

All tests use synthetic data. No MT5 connection required.

---

## Safety guarantees maintained

- Live trading: still permanently disabled
- Paper executor: still structurally isolated from MT5 order functions
- Daily 5-trade limit: enforced per symbol; two positions = one daily entry (R110)
- Total risk: never exceeds grade budget (R107)
- No existing strategy logic removed or silently changed
