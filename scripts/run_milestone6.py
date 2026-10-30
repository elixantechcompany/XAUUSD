"""
Milestone 6 CLI Runner — Backtesting Engine & Forward Demo Verification.

Executes:
1. Historical H1 Backtest for XAUUSD using Part3StrategyEngine.
2. Historical H1 Backtest for BTCUSD using Part3StrategyEngine.
3. Exness Demo Forward Verification (terminal connection, symbol resolution,
   live quote streaming, pre-flight order check, and liquidation test).
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logging_config import configure_logging, get_logger
configure_logging("WARNING")  # Keep terminal output clean of internal debug messages

from src.backtest.data_loader import HistoricalDataLoader
from src.backtest.part3_backtester import Part3Backtester
from src.execution.demo_verifier import DemoVerifier, DemoVerificationReport

log = get_logger(__name__)


def run_xauusd_backtest(bars_count: int = 500) -> None:
    print("\n" + "=" * 70)
    print(f"  STEP 1: RUNNING XAUUSD H1 BACKTEST ({bars_count} BARS)...")
    print("=" * 70)
    candles = HistoricalDataLoader.generate_synthetic_h1(
        symbol="XAUUSD",
        count=bars_count,
        seed=101,
    )
    backtester = Part3Backtester(
        symbol="XAUUSD",
        initial_balance=10_000.0,
        risk_pct_per_trade=1.0,
        min_rr=2.0,
        max_daily_trades=5,
    )
    report = backtester.run(candles)
    print(report.summary())
    return report


def run_btcusd_backtest(bars_count: int = 500) -> None:
    print("\n" + "=" * 70)
    print(f"  STEP 2: RUNNING BTCUSD H1 BACKTEST ({bars_count} BARS)...")
    print("=" * 70)
    candles = HistoricalDataLoader.generate_synthetic_h1(
        symbol="BTCUSD",
        count=bars_count,
        seed=202,
    )
    backtester = Part3Backtester(
        symbol="BTCUSD",
        initial_balance=10_000.0,
        risk_pct_per_trade=1.0,
        min_rr=2.0,
        max_daily_trades=5,
    )
    report = backtester.run(candles)
    print(report.summary())
    return report


def run_demo_verification(execute_trade: bool = False) -> None:
    print("\n" + "=" * 70)
    print("  STEP 3: CONNECTING TO EXNESS DEMO ACCOUNT & VERIFYING STREAMING...")
    print("=" * 70)
    verifier = DemoVerifier(symbols=["XAUUSD", "BTCUSD"])
    report = verifier.run_full_verification(execute_live_demo_trade=execute_trade)
    print(report.summary())

    if not report.terminal_connected:
        print("\n" + "-" * 70)
        print("  NOTICE: MetaTrader 5 Terminal is currently closed on Windows.")
        print("  To connect live to Exness:")
        print("  1. Launch 'MetaTrader 5' from your Windows Start Menu / Desktop.")
        print("  2. Log into your Exness Demo account (e.g. Server: Exness-MT5Trial12).")
        print("  3. Rerun: python scripts/run_milestone6.py --bars 300")
        print("-" * 70)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Milestone 6 Execution Runner")
    parser.add_argument("--bars", type=int, default=300, help="Number of H1 historical bars to backtest")
    parser.add_argument("--trade", action="store_true", help="Execute live 0.01 micro-lot test deal on demo if MT5 is connected")
    args = parser.parse_args()

    print("=" * 70)
    print("  LOCAL MULTI-AGENT AI TRADING DESK — MILESTONE 6 VERIFICATION")
    print("  Owner: Hannington | Broker: Exness | Platform: MetaTrader 5")
    print("=" * 70)

    try:
        run_xauusd_backtest(bars_count=args.bars)
        run_btcusd_backtest(bars_count=args.bars)
        run_demo_verification(execute_trade=args.trade)
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Milestone 6 execution failed: {exc}", file=sys.stderr)
        log.exception("milestone_6_execution_failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
