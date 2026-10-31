@echo off
TITLE Exness MT5 - Cloud Dashboard Live Bridge
color 0A
echo ================================================================
echo       EXNESS METATRADER 5 LIVE BRIDGE TO CLOUD DASHBOARD         
echo ================================================================
echo.
echo Connecting to local Exness MT5 terminal and broadcasting telemetry...
echo.

IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" connect_exness.py %*
) ELSE (
    python connect_exness.py %*
)

pause
