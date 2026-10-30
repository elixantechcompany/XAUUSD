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
    """Start the engine evaluation loop (APScheduler, one tick per H1 close)."""
    from src.config.settings import get_settings
    from src.utils.logging_config import configure_logging
    from src.utils.database import init_db, get_session_factory
    from src.data.market_data_adapter import MT5DataAdapter
    from src.execution.paper_executor import PaperExecutor
    from src.engine.trading_engine import TradingEngine

    s = get_settings()
    configure_logging(level=s.log_level, log_dir=s.log_dir)
    init_db(s.db_path)

    adapter = MT5DataAdapter()
    if not adapter.connect():
        print("[ERROR] Could not connect to MT5. Is MetaTrader 5 running?")
        sys.exit(1)

    executor = PaperExecutor()
    engine = TradingEngine(
        settings=s,
        market_data=adapter,
        db_session_factory=get_session_factory(),
        executor=executor,
    )

    results = engine.initialise_symbols()
    for sym, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"[ENGINE] Symbol {sym}: {status}")

    # ── Scheduler: evaluate each symbol every minute (H1 bar closes on the hour)
    # In production this should be triggered by candle-close detection, not a timer.
    # For initial testing, polling every 60 seconds is acceptable.
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="UTC")

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

    scheduler.add_job(evaluate_all, "interval", minutes=1, id="evaluate_all")
    print("[ENGINE] Scheduler started — evaluating every 60s (paper mode)")
    print("[ENGINE] Press Ctrl+C to stop")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        pass
    finally:
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
