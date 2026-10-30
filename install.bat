@echo off
REM ============================================================
REM  XAUUSD/BTCUSD FVG Trader — One-shot install script
REM  Run this in a normal Windows Command Prompt or PowerShell.
REM  Do NOT run from inside Kiro (the Python extension is broken).
REM ============================================================

echo [INSTALL] Checking Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found on PATH. Install Python 3.11+ and try again.
    pause
    exit /b 1
)

echo [INSTALL] Creating virtual environment...
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create venv.
    pause
    exit /b 1
)

echo [INSTALL] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo [INSTALL] Installing dependencies (this may take a few minutes)...
.venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Dependency installation failed. Check your internet connection.
    pause
    exit /b 1
)

echo [INSTALL] Initialising database...
.venv\Scripts\python.exe -c "from src.utils.database import init_db; init_db()"

echo [INSTALL] Running unit tests...
.venv\Scripts\python.exe -m pytest tests/unit/ -v --tb=short

echo.
echo [DONE] Installation complete.
echo.
echo To start the engine + API:
echo     .venv\Scripts\python.exe main.py
echo.
echo To check MT5 connection:
echo     .venv\Scripts\python.exe main.py --check
echo.
pause
