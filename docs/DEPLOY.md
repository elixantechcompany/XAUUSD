# Deployment Guide

## What you need before starting

1. A **Supabase** account (free tier works) — supabase.com
2. A **GitHub** account — github.com
3. A **Vercel** account (free tier works) — vercel.com
4. The bot running on your **Windows laptop** (or VPS) with MetaTrader 5

---

## Step 1 — Create a GitHub repository

Open PowerShell on your laptop and run:

```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"

# One-time git setup (only if you haven't done this before)
git config --global user.name "Hannington"
git config --global user.email "your-email@example.com"

# Initialize and push
git init
git add .
git commit -m "Initial commit — trading bot + dashboard"

# Create repo on GitHub first at github.com/new, then:
git remote add origin https://github.com/YOUR_USERNAME/xauusd-bot.git
git branch -M main
git push -u origin main
```

From now on, every time you push to `main`, Vercel auto-deploys the frontend.

---

## Step 2 — Set up Supabase

1. Go to **supabase.com** → New project
2. Name it `xauusd-bot` → choose a strong database password → select the region closest to you
3. Wait for the project to be ready (about 1 minute)

### Run the schema

4. In Supabase dashboard → **SQL Editor** → click **New query**
5. Copy the entire contents of `docs/supabase_schema.sql` and paste it in
6. Click **Run** — you should see "Success. No rows returned."

### Get your keys

7. Go to **Settings → API**
8. Copy these values — you'll need them in the next steps:
   - `Project URL` → this is your `SUPABASE_URL`
   - `anon / public` key → this is your `SUPABASE_ANON_KEY`
   - `service_role / secret` key → this is your `SUPABASE_SERVICE_ROLE_KEY` (keep this secret!)

### Enable authentication

9. Go to **Authentication → Providers** → confirm Email is enabled
10. Go to **Authentication → Email Templates** — customise if you want

---

## Step 3 — Deploy the frontend to Vercel

1. Go to **vercel.com** → Add New → Project
2. Click **Import Git Repository** → select your `xauusd-bot` repo
3. Set the **Root Directory** to `frontend`
4. Vercel will auto-detect Next.js

### Add environment variables in Vercel

In the Vercel project settings → **Environment Variables**, add:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase anon key |
| `NEXT_PUBLIC_ENGINE_API_URL` | `http://127.0.0.1:8000` (your laptop's local API) |

5. Click **Deploy**

Your dashboard will be live at `https://your-project.vercel.app`

### Automatic deployments

Every `git push` to `main` now auto-deploys. That's it — GitHub + Vercel handle it.

```powershell
# How to deploy an update
git add .
git commit -m "Your change description"
git push origin main
# Vercel deploys automatically in ~1 minute
```

---

## Step 4 — Configure the bot to publish to Supabase

On your laptop, set these environment variables before running the bot:

```powershell
# PowerShell — set for current session
$env:SUPABASE_URL = "https://your-project.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key-here"

# To make them permanent (survives restarts):
[System.Environment]::SetEnvironmentVariable("SUPABASE_URL", "https://your-project.supabase.co", "User")
[System.Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "your-key-here", "User")
```

Also set the API secret:
```powershell
[System.Environment]::SetEnvironmentVariable("API_SECRET_KEY", "your-random-32-char-secret", "User")
```

Then install and run:
```powershell
cd "C:\Users\PwezaCore\Desktop\XAUUSD"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --check     # verify everything connects
python main.py             # start the engine
```

---

## Step 5 — Add your Exness account

1. Open your dashboard URL in the browser
2. Click **Sign up** to create your Supabase account
3. Confirm your email (check your inbox)
4. Go to **Accounts** in the navigation
5. Click **Add MT5 Account**
6. Enter:
   - Display label (e.g. "Exness Standard")
   - Your Exness MT5 login number
   - Your MT5 trading password (sent directly to the engine on your laptop, never stored in the cloud)
   - Your broker server (shown in your MT5 terminal login screen)
7. Click **Save account & send password to engine**

The engine stores your password in **Windows Credential Manager** — it never goes to Supabase.

---

## Step 6 — Verify everything works

Open the dashboard. You should see:

- ✅ **Running** status pill (green) — engine is sending heartbeats
- ✅ MT5 Connected
- ✅ PAPER mode
- Equity and balance loading

If the status shows **Offline**: make sure `python main.py` is running on your laptop and both `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set.

---

## Security checklist before going live

- [ ] `SUPABASE_SERVICE_ROLE_KEY` is NOT in the git repository
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is NOT in Vercel environment variables
- [ ] MT5 password is stored only in Windows Credential Manager on your laptop
- [ ] `API_SECRET_KEY` is a strong random string (not the default placeholder)
- [ ] Supabase RLS is enabled (it is — the schema sets it up)
- [ ] `.gitignore` includes `.env` and `*.env` (it does)

---

## Useful commands

```powershell
# Check bot status
python main.py --check

# Start bot + API
python main.py

# Start API only (no trading loop)
python main.py --mode api

# Run tests
python -m pytest tests/unit/ -v

# Push code update
git add .
git commit -m "Update"
git push origin main
```
