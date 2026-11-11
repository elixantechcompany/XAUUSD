# Git Setup, Push, and Vercel Auto-Deploy
**Complete step-by-step guide**

---

## Prerequisites

- Git installed: https://git-scm.com/download/win
- GitHub account: https://github.com
- Vercel account: https://vercel.com
- Supabase project created with schema applied (see `docs/DEPLOY.md`)

---

## Step 1 — Open an external PowerShell

**Do not use the Kiro terminal.** Shell commands time out there due to a missing `pet.exe` extension file.

- Press **Windows key**
- Type `powershell`
- Press **Enter**
- A blue terminal window opens — use this for all commands below

---

## Step 2 — One-time git identity setup

Run these once per machine (replace with your real name and email):

```powershell
git config --global user.name "Hannington"
git config --global user.email "your-email@example.com"
```

---

## Step 3 — Initialise the repository and make the first commit

```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"

# Initialise git (only needed once)
git init
git branch -M main

# Stage everything (.gitignore protects secrets, .env, node_modules, .db files)
git add .

# Verify what will be committed — check no .env or passwords are listed
git status

# Create the first commit
git commit -m "feat: complete trading bot v1.2 — break-even, two-position execution, dashboard"
```

---

## Step 4 — Create a private GitHub repository

1. Go to **https://github.com/new**
2. Repository name: `xauusd-bot` (or any name)
3. Set visibility to **Private** — your trading logic and strategy must stay private
4. **Do NOT** tick "Add a README file" or "Add .gitignore" — you already have these
5. Click **Create repository**

GitHub will show you a page with commands. Copy the remote URL — it looks like:
```
https://github.com/YOUR_USERNAME/xauusd-bot.git
```

---

## Step 5 — Connect and push

```powershell
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/xauusd-bot.git
git push -u origin main
```

GitHub will ask for your username and password (or a Personal Access Token if you have 2FA enabled).

**To create a Personal Access Token (PAT):**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token"
3. Give it a name, set expiry, check "repo" scope
4. Copy the token and use it as the password when git asks

---

## Step 6 — Deploy frontend to Vercel with automatic deployments

1. Go to **https://vercel.com** and sign in
2. Click **Add New → Project**
3. Click **Import Git Repository**
4. Authorise Vercel to access your GitHub account
5. Select `xauusd-bot`
6. Set **Root Directory** to `frontend`
7. Vercel auto-detects Next.js — confirm the settings
8. **Before clicking Deploy**, add these environment variables:

| Name | Value | Where to find it |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://xxxx.supabase.co` | Supabase → Settings → API → Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJ...` | Supabase → Settings → API → anon/public key |
| `NEXT_PUBLIC_ENGINE_API_URL` | `http://127.0.0.1:8000` | Your local machine |

9. Click **Deploy**
10. Vercel deploys and gives you a URL like `https://xauusd-bot-xyz.vercel.app`

**Automatic deployments:** Every time you run `git push origin main`, Vercel automatically rebuilds and redeploys. No manual step needed.

---

## Step 7 — Configure Supabase authentication callback URL

After Vercel gives you your deployment URL:

1. Go to your Supabase project → **Authentication → URL Configuration**
2. Set **Site URL** to your Vercel URL: `https://xauusd-bot-xyz.vercel.app`
3. Add to **Redirect URLs**: `https://xauusd-bot-xyz.vercel.app/auth/callback`
4. Save

This is required for email confirmation links to work after sign-up.

---

## Step 8 — Set environment variables for the Python engine

On your laptop, set these permanently so the engine can connect to Supabase:

```powershell
# Set permanently for your Windows user account
[System.Environment]::SetEnvironmentVariable(
    "SUPABASE_URL",
    "https://your-project.supabase.co",
    "User"
)
[System.Environment]::SetEnvironmentVariable(
    "SUPABASE_SERVICE_ROLE_KEY",
    "your-service-role-key",
    "User"
)
[System.Environment]::SetEnvironmentVariable(
    "API_SECRET_KEY",
    "your-random-32-char-secret",
    "User"
)
```

The service role key is in Supabase → Settings → API → **service_role** (secret).
**Never commit this key to git or put it in Vercel environment variables.**

---

## Step 9 — Install Python dependencies and run

```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install all dependencies including supabase-py
pip install -r requirements.txt

# Check everything connects
python main.py --check

# Start the engine (MT5 must be open and logged in)
python main.py
```

The engine will:
- Send a heartbeat every 10 seconds (dashboard shows ONLINE immediately)
- Publish signals and evaluations to Supabase
- Poll for dashboard commands every 3 seconds

---

## Step 10 — Future updates (how to push code changes)

Every time you make changes:

```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"
git add .
git commit -m "description of your change"
git push origin main
```

Vercel automatically deploys the frontend within ~1 minute.
The Python engine needs to be restarted manually to pick up backend changes.

---

## What each key does

| Key | Where used | Contains |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend (Vercel) | Supabase project URL — safe for browser |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend (Vercel) | Supabase anon key — safe for browser, RLS enforces security |
| `SUPABASE_URL` | Python engine (laptop) | Same URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Python engine (laptop only) | Bypasses RLS — NEVER in browser or Vercel |
| `API_SECRET_KEY` | Python engine (laptop) | Signs JWTs for the local FastAPI — NEVER committed |

---

## Security checklist before first push

Run this before `git push` to verify no secrets are going into git:

```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"
git diff --cached --name-only
```

Verify you do NOT see any of these in the list:
- `.env`
- `.env.local`
- Any file containing `SUPABASE_SERVICE_ROLE_KEY`
- Any file containing `API_SECRET_KEY`
- `data/db/*.db` (contains trade history)
- `.venv/` (thousands of library files)
- `frontend/node_modules/`

If any of these appear, check your `.gitignore` and run `git rm --cached <filename>` before committing.
