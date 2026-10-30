"""
Execution Engine Backends (Paper and MetaTrader 5) and Demo Verifier.
"""
from src.execution.paper_executor import PaperExecutor, PaperPosition, PaperLedger
from src.execution.mt5_executor import MT5Executor, MT5Position
from src.execution.demo_verifier import DemoVerifier, DemoVerificationReport

__all__ = [
    "PaperExecutor",
    "PaperPosition",
    "PaperLedger",
    "MT5Executor",
    "MT5Position",
    "DemoVerifier",
    "DemoVerificationReport",
]
