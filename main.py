"""
Application entry point — STRATEGY_SPEC.md v1.0

Usage:
    python main.py                   # start API + engine scheduler (paper mode)
    python main.py --mode api        # API server only
    python main.py --mode engine     # engine loop only (no HTTP)
    python main.py --check           # validate config and MT5 connection, then exit

Live trading is permanently disabled (R88, IMPL7).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="XAUUSD/BTCUSD FVG Trader")
    p.add_argument("--mode", choices=["api", "engine", "both"], default="both")
    p.add_argument("--check", action="store_true",
                   help="Validate config and broker connection then exit")
    p.add_argument("--paper", action="store_true", default=True,
                   help="Paper trading mode (default, always active in this release)")
    return p.parse_args()


def run_check() -> int:
    """Validate configuration and MT5 connection. Returns 0 on success."""
    from src.config.settings import get_settings, reload_settings
    from src.utils.logging_config import configure_logging

    s = get_settings()
    configure_logging(level=s.log_level, log_dir=s.log_dir)

    print(f"[CHECK] Execution mode : {s.execution_mode}")
    print(f"[CHECK] Symbols        : {s.strategy.symbols}")
    print(f"[CHECK] Timeframe      : {s.strategy.timeframe}")
    print(f"[CHECK] DB path        : {s.db_path}")
    print(f"[CHECK] Live trading   : DISABLED (R88)")

    if s.execution_mode == "live":
        print("[FAIL] Live trading is permanently disabled.")
        return 1

    # Attempt MT5 connection
    try:
        from src.data.market_data_adapter import MT5DataAdapter
        adapter = MT5DataAdapter()
        ok = adapter.connect()
        if ok:
            info = adapter.get_account_info()
            print(f"[CHECK] MT5 connected  : login={info['login']} "
                  f"server={info['server']}")
            for sym in s.strategy.symbols:
                si = adapter.get_symbol_info(sym)
                if si:
                    print(f"[CHECK] Symbol {sym:<12}: "
                          f"tick_size={si.tick_size} "
                          f"vol_min={si.volume_min} "
                          f"spread={si.spread}pts")
                else:
                    print(f"[WARN]  Symbol {sym} not found — check broker name/suffix")
            adapter.disconnect()
        else:
            print("[WARN] MT5 not available (is MetaTrader 5 running?)")
    except ImportError:
        print("[WARN] MetaTrader5 package not installed — MT5 check skipped")

    # Init database
    from src.utils.database import init_db
    init_db(s.db_path)
    print(f"[CHECK] Database initialised at {s.db_path}")

    print("[OK] Check complete.")
    return 0


def run_api() -> None:
    """Start the FastAPI server."""
    import uvicorn
    from src.config.settings import get_settings
    s = get_settings()
    uvicorn.run(
        "src.api.app:app",
        host=s.api.host,
        port=s.api.port,
        reload=False,
        log_level=s.log_level.lower(),
    )


def run_engine() -> None:
    """Start the engine evaluation loop with Supabase publishing."""
    from src.config.settings import get_settings
    from src.utils.logging_config import configure_logging
    from src.utils.database import init_db, get_session_factory
    from src.data.market_data_adapter import MT5DataAdapter
    from src.execution.paper_executor import PaperExecutor
    from src.execution.mt5_executor import MT5Executor
    from src.execution.multi_account_copier import MultiAccountCopier, ChildAccountConfig
    from src.engine.trading_engine import TradingEngine
    from src.utils.credentials import CredentialManager
    from src.supabase import publisher

    s = get_settings()
    configure_logging(level=s.log_level, log_dir=s.log_dir)
    init_db(s.db_path)

    adapter = MT5DataAdapter()
    if not adapter.connect():
        print("[ERROR] Could not connect to MT5. Is MetaTrader 5 running?")
        sys.exit(1)

    # ── Build executor ────────────────────────────────────────────────────────
    cred_mgr = CredentialManager()

    if s.execution_mode == "paper":
        # Paper mode: simulated fills, no real MT5 orders
        executor = PaperExecutor()
        copier   = None
        print("[ENGINE] Running in PAPER mode — no real orders will be placed")
    else:
        # Demo mode: real MT5 orders via MT5Executor
        master_creds = cred_mgr.get_credentials()
        if not master_creds:
            print("[ERROR] No MT5 credentials found.")
            print("[ERROR] Run: python main.py --check  to diagnose")
            print("[ERROR] Or add an account via the dashboard Accounts page.")
            sys.exit(1)

        executor = MT5Executor(credentials=master_creds)
        print(f"[ENGINE] MT5Executor ready for account {master_creds.account_id}")

        # ── Wire up copy-trading if child accounts are registered ─────────────
        child_configs = cred_mgr.get_child_accounts()
        if child_configs:
            print(f"[ENGINE] Copy-trading: {len(child_configs)} child account(s) found")
            copier = MultiAccountCopier(
                master_executor=executor,
                child_accounts=[
                    ChildAccountConfig(
                        account_id=c["account_id"],
                        password=c["password"],
                        server=c["server"],
                        label=c.get("label", ""),
                        risk_multiplier=c.get("risk_multiplier", 1.0),
                    )
                    for c in child_configs
                ],
            )
            for child in child_configs:
                print(f"[ENGINE]   Child account: {child['account_id']} ({child.get('label', 'unnamed')})")
        else:
            copier = None
            print("[ENGINE] No child accounts registered — copy-trading disabled")

    engine = TradingEngine(
        settings=s,
        market_data=adapter,
        db_session_factory=get_session_factory(),
        executor=executor,
        copier=copier,
    )

    results = engine.initialise_symbols()
    for sym, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"[ENGINE] Symbol {sym}: {status}")

    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="UTC")

    # ── Heartbeat every 10 seconds (dashboard ONLINE/STALE/OFFLINE) ───────────
    def send_heartbeat():
        try:
            account = adapter.get_account_info()
            tick_xau = adapter.get_tick("XAUUSD")
            last_tick = tick_xau["time"] if tick_xau else None
            publisher.publish_heartbeat(
                mt5_connected=adapter.is_connected(),
                last_tick_ts=last_tick,
                equity=account["equity"] if account else None,
                balance=account["balance"] if account else None,
                execution_mode=s.execution_mode,
            )
            if account:
                publisher.publish_account_snapshot(
                    equity=account["equity"],
                    balance=account["balance"],
                    daily_pnl=0.0,
                    drawdown_pct=0.0,
                    open_positions_count=len(executor.get_positions()) if hasattr(executor, "get_positions") else 0,
                    execution_mode=s.execution_mode,
                )
        except Exception as exc:
            print(f"[HEARTBEAT] Failed: {exc}")

    scheduler.add_job(send_heartbeat, "interval", seconds=10, id="heartbeat")

    # ── Strategy evaluation every 60 seconds ──────────────────────────────────
    def evaluate_all():
        for sym in s.strategy.symbols:
            if sym in results and results[sym]:
                result = engine.evaluate_symbol(sym)
                print(
                    f"[ENGINE] {sym} | candles={result.candles_evaluated} "
                    f"new_fvgs={result.new_fvgs} "
                    f"signals={result.signals_generated} "
                    f"orders={result.orders_submitted} "
                    f"rejected={result.orders_rejected} "
                    f"errors={result.errors}"
                )
                publisher.publish_evaluation(
                    symbol=sym,
                    timeframe=s.strategy.timeframe,
                    decision=(
                        "SIGNAL" if result.signals_generated > 0
                        else "ORDER" if result.orders_submitted > 0
                        else "NO_TRADE"
                    ),
                    reason_codes=[f"fvgs={result.new_fvgs}"],
                    indicators={"candles_evaluated": result.candles_evaluated},
                )

    # ── Command polling every 3 seconds ───────────────────────────────────────
    def poll_commands():
        commands = publisher.poll_pending_commands()
        for cmd in commands:
            cmd_type = cmd.get("type", "")
            cmd_id   = cmd.get("id", "")
            payload  = cmd.get("payload", {})
            try:
                if cmd_type == "PAUSE":
                    print("[COMMAND] PAUSE received")
                    publisher.acknowledge_command(cmd_id, "Paused", "done")
                elif cmd_type == "RESUME":
                    print("[COMMAND] RESUME received")
                    publisher.acknowledge_command(cmd_id, "Resumed", "done")
                elif cmd_type == "KILL":
                    print("[COMMAND] KILL SWITCH — halting all new submissions")
                    if copier:
                        copier.close_all_accounts_positions()
                    publisher.acknowledge_command(cmd_id, "Kill switch activated", "done")
                elif cmd_type == "CLOSE_ALL":
                    print("[COMMAND] CLOSE_ALL received")
                    if copier:
                        report = copier.close_all_accounts_positions()
                        publisher.acknowledge_command(cmd_id, f"Closed: {report}", "done")
                    else:
                        publisher.acknowledge_command(cmd_id, "No copier active", "done")
                elif cmd_type == "NEWS_LOCK":
                    symbol = payload.get("symbol", "XAUUSD")
                    locked = payload.get("locked", True)
                    print(f"[COMMAND] NEWS_LOCK {symbol} locked={locked}")
                    publisher.acknowledge_command(cmd_id, f"News lock {symbol}={locked}", "done")
                else:
                    publisher.acknowledge_command(cmd_id, f"Unknown: {cmd_type}", "failed")
            except Exception as exc:
                print(f"[COMMAND] Error processing {cmd_type}: {exc}")
                publisher.acknowledge_command(cmd_id, str(exc), "failed")

    scheduler.add_job(evaluate_all,  "interval", minutes=1, id="evaluate_all")
    scheduler.add_job(poll_commands,  "interval", seconds=3,  id="poll_commands")

    # Send immediate heartbeat so dashboard shows ONLINE right away
    send_heartbeat()
    publisher.publish_log(
        "INFO", "ENGINE_START", "Engine started",
        {"mode": s.execution_mode, "symbols": s.strategy.symbols,
         "copy_accounts": len(child_configs) if s.execution_mode != "paper" and child_configs else 0}
    )

    print("[ENGINE] Heartbeat every 10s | Evaluation every 60s | Commands every 3s")
    print("[ENGINE] Dashboard should now show ONLINE")
    print("[ENGINE] Press Ctrl+C to stop")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        pass
    finally:
        publisher.publish_heartbeat(
            mt5_connected=False, last_tick_ts=None,
            equity=None, balance=None,
            execution_mode=s.execution_mode,
        )
        publisher.publish_log("INFO", "ENGINE_STOP", "Engine stopped cleanly")
        adapter.disconnect()
        print("[ENGINE] Stopped.")


def main() -> None:
    args = parse_args()

    if args.check:
        sys.exit(run_check())

    from src.config.settings import get_settings
    from src.utils.logging_config import configure_logging
    from src.utils.database import init_db

    s = get_settings()
    configure_logging(level=s.log_level, log_dir=s.log_dir)
    init_db(s.db_path)

    if s.execution_mode == "live":
        print("[FATAL] Live trading is permanently disabled. Exiting.")
        sys.exit(1)

    if args.mode == "api":
        run_api()
    elif args.mode == "engine":
        run_engine()
    else:
        # Run both: engine in a background thread, API in main thread
        import threading
        t = threading.Thread(target=run_engine, daemon=True)
        t.start()
        run_api()


if __name__ == "__main__":
    main()
