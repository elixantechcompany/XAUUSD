# Setup Guide

## Prerequisites

- Windows 10/11
- Python 3.11 or newer (download from python.org)
- MetaTrader 5 terminal installed and logged in to your Exness account
- Git (optional but recommended)

## Step 1 — Fix the Kiro Python extension error

The error `spawn pet.exe ENOENT` means the Kiro Python extension is broken.
**All install and run commands must be run in an external terminal, not inside Kiro.**

Open **Windows PowerShell** or **Command Prompt** (not the Kiro terminal).

## Step 2 — Install dependencies

```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"

# Option A: double-click install.bat in File Explorer

# Option B: run manually
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `Activate.ps1` is blocked:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Step 3 — Initialise the database

```powershell
python -c "from src.utils.database import init_db; init_db()"
```

This creates `data/db/fvg_trader.db` with all tables.

## Step 4 — Check MT5 connection

Make sure MetaTrader 5 is open and logged in, then:

```powershell
python main.py --check
```

Expected output:
```
[CHECK] Execution mode : paper
[CHECK] Symbols        : ['XAUUSD', 'BTCUSD']
[CHECK] MT5 connected  : login=XXXXXXXX server=Exness-...
[CHECK] Symbol XAUUSD  : tick_size=0.01 vol_min=0.01 spread=...
[CHECK] Symbol BTCUSD  : tick_size=0.01 vol_min=0.01 spread=...
[CHECK] Database initialised at data/db/fvg_trader.db
[OK] Check complete.
```

## Step 5 — Configure spread limits

Before the engine will place any orders, you must set spread limits from
real Exness data (R59/R60). Edit `src/config/settings.py` and update:

```python
max_spread_pips: dict[str, float | None] = {
    "XAUUSD": 5.0,   # replace with actual observed max spread
    "BTCUSD": 50.0,  # replace with actual observed max spread
}
```

Until these are set, the engine logs all setups but blocks orders.

## Step 6 — Run unit tests

```powershell
python -m pytest tests/unit/ -v --tb=short
```

All tests must pass before proceeding to paper trading.

## Step 7 — Start the engine (paper mode)

```powershell
python main.py
```

This starts:
- The evaluation loop (every 60 seconds, paper mode only)
- The FastAPI server at http://127.0.0.1:8000

API docs: http://127.0.0.1:8000/docs

## Step 8 — Create your API user

```powershell
python -c "
from src.utils.database import init_db, get_session_factory
from src.api.models import APIUser
from passlib.context import CryptContext
from datetime import datetime, timezone

init_db()
db = get_session_factory()()
ctx = CryptContext(schemes=['bcrypt'])
user = APIUser(
    username='admin',
    hashed_password=ctx.hash('your-password-here'),
    is_active=True,
    created_at=datetime.now(tz=timezone.utc),
)
db.add(user)
db.commit()
print('User created.')
"
```

Then get a token:
```powershell
curl -X POST http://127.0.0.1:8000/auth/token \
  -d "username=admin&password=your-password-here"
```

## Environment variables

Set these before starting the engine:

```powershell
$env:API_SECRET_KEY = "your-random-32-char-secret-here"
```

Never commit a real secret to Git.

## Live trading

Live trading is **permanently disabled** in this release (R88).
The `execution_mode` setting only accepts `"paper"` or `"demo"`.
Demo mode requires all unit tests to pass and explicit owner approval.

## Troubleshooting

| Problem | Fix |
|---|---|
| `pet.exe ENOENT` in Kiro | Run all commands in external PowerShell, not inside Kiro |
| `MetaTrader5 not installed` | `pip install MetaTrader5==5.0.4424` |
| MT5 not connected | Open MetaTrader 5, log in, then run `python main.py --check` |
| `Spread limit not configured` | Set `max_spread_pips` in settings.py from real Exness data |
| Tests fail with import errors | Run `pip install -r requirements.txt` again |
