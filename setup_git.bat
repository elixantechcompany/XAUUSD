@echo off
REM ============================================================
REM  Git init + first push + Vercel auto-deploy setup
REM  Run this in an EXTERNAL PowerShell or Command Prompt.
REM  Do NOT run from inside Kiro (shell commands time out there).
REM ============================================================

echo [GIT] Checking git is installed...
git --version
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] git not found. Install from https://git-scm.com/ and re-run.
    pause
    exit /b 1
)

cd /d "c:\Users\PwezaCore\Desktop\XAUUSD"

REM ── One-time git identity setup (only needed once per machine) ──────────────
REM Uncomment and fill these in if you haven't set them before:
REM git config --global user.name "Hannington"
REM git config --global user.email "your-email@example.com"

REM ── Init repo if not already done ──────────────────────────────────────────
if not exist ".git" (
    echo [GIT] Initialising git repository...
    git init
    git branch -M main
) else (
    echo [GIT] Git repository already exists.
)

REM ── Stage all files (respects .gitignore) ───────────────────────────────────
echo [GIT] Staging files...
git add .

REM ── Show what will be committed ─────────────────────────────────────────────
echo [GIT] Files staged for commit:
git status --short

REM ── Commit ──────────────────────────────────────────────────────────────────
echo [GIT] Creating commit...
git commit -m "feat: complete trading bot — strategy v1.2, break-even, two-position execution, dashboard"

REM ── Push to GitHub ──────────────────────────────────────────────────────────
echo.
echo [GIT] Next steps:
echo.
echo   1. Create a new repo at https://github.com/new
echo      Name it: xauusd-bot  (or any name you like)
echo      Make it PRIVATE (it contains trading logic)
echo      Do NOT initialise with README or .gitignore
echo.
echo   2. Then run these two commands (replace YOUR_USERNAME):
echo.
echo      git remote add origin https://github.com/YOUR_USERNAME/xauusd-bot.git
echo      git push -u origin main
echo.
echo   3. Once pushed, go to https://vercel.com
echo      Import that repo, set Root Directory to "frontend"
echo      Add environment variables (see DEPLOY.md)
echo      Vercel will auto-deploy on every future push.
echo.
echo [DONE] Git commit created. Follow the steps above to push.
pause
