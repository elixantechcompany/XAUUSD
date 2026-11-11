@echo off
title ELIXAN QUANT - 24/7 Immortal Exness MT5 Trading Engine
color 0A
cd /d "%~dp0"

echo =====================================================================
echo   ELIXAN QUANT AI - 24/7 AUTONOMOUS EXNESS MT5 TRADING ENGINE
echo   - Early Breakeven @ 0.50R (Zero-Loss Protection on Winners)
echo   - Profit Harvester @ 35%% Pullback from Peak
echo   - Multi-Account Fast Copier ^& Real-Time Dashboard Telemetry
echo   - Auto-Restart Watchdog Active (Press Ctrl+C to Stop)
echo =====================================================================

:watchdog_loop
echo [%TIME%] Starting Exness MT5 Live Bridge Engine...
.\.venv\Scripts\python.exe connect_exness.py %*
echo [%TIME%] Engine process exited. Restarting in 3 seconds (Press Ctrl+C to cancel)...
timeout /t 3
goto watchdog_loop
