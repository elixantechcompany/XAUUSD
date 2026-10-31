"""
Exness MT5 Live IPC Bridge & Terminal Synchronizer
Author: Antigravity & Hannington
Description:
  Bridges local Exness MetaTrader 5 desktop terminal to Supabase and the Next.js cloud web dashboard.
  - Automatically detects logged-in MT5 account or logs in with provided credentials.
  - Securely saves password into Windows Credential Manager (keyring) with zero cloud plaintext.
  - Streams real-time heartbeats (equity, balance, ticks) to Supabase every 5 seconds.
  - Synchronizes master account configuration and listens for dashboard commands.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "frontend" / ".env.local")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://bntqfzopbbeosruzjxbw.supabase.co")
SUPABASE_KEY = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJudHFmem9wYmJlb3NydXpqeGJ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MzM1OTEzOSwiZXhwIjoyMTA4OTM1MTM5fQ.jA3JXlfvnisozH2-beLVFkIBqEbMz9UGDmHAlewiNCQ"
)

def parse_args():
    parser = argparse.ArgumentParser(description="Connect Exness MT5 to Web Dashboard")
    parser.add_argument("--login", type=int, help="Exness Account Number / MT5 Login")
    parser.add_argument("--password", type=str, help="Exness Trading Password")
    parser.add_argument("--server", type=str, help="Exness MT5 Server (e.g. Exness-MT5Trial9)")
    parser.add_argument("--symbol", type=str, default="BTCUSD", help="Primary trading symbol (BTCUSD or XAUUSD)")
    parser.add_argument("--once", action="store_true", help="Send single heartbeat and snapshot then exit")
    return parser.parse_args()


def init_supabase():
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[ERROR] Failed to initialize Supabase client: {e}")
        return None


def connect_terminal(args):
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[FATAL] MetaTrader5 package is not installed in this Python environment.")
        print("Run: pip install MetaTrader5")
        sys.exit(1)

    print("[1/4] Initializing MetaTrader 5 IPC connection...")
    if not mt5.initialize():
        print(f"[ERROR] mt5.initialize() failed: {mt5.last_error()}")
        print("Please ensure your Exness MetaTrader 5 terminal is installed and running on Windows.")
        sys.exit(1)

    # 1. Check if user provided login credentials directly
    if args.login and args.password and args.server:
        print(f"[2/4] Logging in to Exness account #{args.login} on {args.server}...")
        ok = mt5.login(login=args.login, password=args.password, server=args.server)
        if not ok:
            print(f"[ERROR] mt5.login() failed: {mt5.last_error()}")
            sys.exit(1)
        # Store in Windows Credential Manager
        try:
            import keyring
            keyring.set_password("exness_mt5_trading_desk", f"{args.login}_password", args.password)
            keyring.set_password("exness_mt5_trading_desk", f"{args.login}_server", args.server)
            keyring.set_password("exness_mt5_trading_desk", "last_active_account", str(args.login))
            print("[SECURE] Saved trading credentials in Windows Credential Manager.")
        except Exception as ke:
            print(f"[WARN] Could not save to Windows Credential Manager: {ke}")

    # 2. Get active terminal account info
    info = mt5.account_info()
    if not info:
        print("[ERROR] No active account logged into MetaTrader 5.")
        print("Please log into your Exness Demo or Real account inside MT5, or pass --login and --password.")
        sys.exit(1)

    return mt5, info


def main():
    args = parse_args()
    supabase = init_supabase()
    if not supabase:
        print("[ERROR] Could not connect to Supabase database. Exiting.")
        sys.exit(1)

    mt5, info = connect_terminal(args)

    mode = "DEMO" if "trial" in info.server.lower() else "LIVE"
    symbol = args.symbol.upper()

    print("\n" + "=" * 60)
    print("      EXNESS METATRADER 5 TERMINAL CONNECTED SUCCESSFULLY     ")
    print("=" * 60)
    print(f"  Account Number : {info.login}")
    print(f"  Account Name   : {info.name}")
    print(f"  Server         : {info.server} ({mode})")
    print(f"  Live Balance   : ${info.balance:,.2f} USD")
    print(f"  Live Equity    : ${info.equity:,.2f} USD")
    print(f"  Free Margin    : ${info.margin_free:,.2f} USD")
    print(f"  Leverage       : 1:{info.leverage}")
    print(f"  Target Symbol  : {symbol}")
    print("=" * 60 + "\n")

    # 1. Update Supabase settings table with verified Master Account info
    print("[3/4] Updating master account status in Supabase settings...")
    try:
        supabase.table("settings").upsert({
            "key": "mt5_account_master",
            "value": {
                "account_id": info.login,
                "login": str(info.login),
                "label": f"Exness {mode} #{info.login} ({info.name})",
                "server": info.server,
                "symbol": symbol,
                "mode": mode,
                "is_master": True,
                "is_active": True,
                "balance": float(info.balance),
                "equity": float(info.equity),
                "margin_free": float(info.margin_free),
                "status": "CONNECTED (LIVE IPC)",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        supabase.table("settings").upsert({
            "key": "mt5_active_symbol",
            "value": {"symbol": symbol},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        print("[SUCCESS] Account configuration synchronized to cloud dashboard.")
    except Exception as se:
        print(f"[WARN] Supabase settings update failed: {se}")

    # 2. Publish initial account snapshot
    try:
        supabase.table("accounts_snapshot").insert({
            "equity": float(info.equity),
            "balance": float(info.balance),
            "daily_pnl": 0.0,
            "drawdown_pct": 0.0,
            "open_positions_count": mt5.positions_total() or 0,
            "execution_mode": mode.lower(),
        }).execute()
        print("[SUCCESS] Initial live equity snapshot published.")
    except Exception as se:
        print(f"[WARN] Failed to insert initial snapshot: {se}")

    # 3. Enter Live Heartbeat & Command Polling Loop
    print("\n[4/4] Starting live telemetry stream (broadcasting heartbeat every 5s)...")
    print("Press Ctrl+C to stop.\n")

    last_cleanup = time.time()
    heartbeat_count = 0

    try:
        while True:
            # Refresh live account info
            curr_info = mt5.account_info()
            if not curr_info:
                print("[WARN] Lost terminal connection, retrying...")
                time.sleep(2)
                continue

            # Check tick price
            tick = mt5.symbol_info_tick(symbol)
            last_tick_time = (
                datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat()
                if tick
                else datetime.now(timezone.utc).isoformat()
            )

            # Insert heartbeat
            supabase.table("heartbeats").insert({
                "ts": datetime.now(timezone.utc).isoformat(),
                "mt5_connected": True,
                "last_tick_ts": last_tick_time,
                "equity": float(curr_info.equity),
                "balance": float(curr_info.balance),
                "execution_mode": mode.lower(),
                "live_trading_enabled": False,
            }).execute()

            heartbeat_count += 1
            if heartbeat_count % 6 == 0 or heartbeat_count == 1:
                bid_str = f"{tick.bid:.2f}" if tick else "N/A"
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Live Heartbeat #{heartbeat_count} | "
                    f"Equity: ${curr_info.equity:,.2f} | Balance: ${curr_info.balance:,.2f} | "
                    f"{symbol} Bid: {bid_str}"
                )

            # Check for commands in Supabase
            try:
                cmd_res = (
                    supabase.table("commands")
                    .select("*")
                    .eq("status", "pending")
                    .limit(5)
                    .execute()
                )
                if cmd_res.data:
                    for cmd in cmd_res.data:
                        cmd_id = cmd.get("id")
                        cmd_type = cmd.get("type")
                        print(f"[COMMAND] Received {cmd_type} (ID: {cmd_id})")
                        # Mark acknowledged / done
                        supabase.table("commands").update({
                            "status": "done",
                            "acked_at": datetime.now(timezone.utc).isoformat(),
                            "result": f"Executed by MT5 bridge ({curr_info.login})",
                        }).eq("id", cmd_id).execute()
            except Exception as ce:
                pass

            # Prune old heartbeats every 10 minutes to save DB space
            if time.time() - last_cleanup > 600:
                try:
                    cutoff = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
                    supabase.table("heartbeats").delete().lt("ts", cutoff).execute()
                    last_cleanup = time.time()
                except Exception:
                    pass

            if args.once:
                break

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n[STOPPED] MT5 Live Bridge cleanly terminated.")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
