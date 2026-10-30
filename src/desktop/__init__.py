"""
Desktop Application Package — PySide6 & pyqtgraph quantitative GUI.
"""
from src.desktop.main_window import MainWindow, run_desktop_app
from src.desktop.widgets.candlestick_chart import StrategyChartWidget
from src.desktop.widgets.consensus_panel import ConsensusPanelWidget
from src.desktop.widgets.kill_switch_dialog import KillSwitchConfirmationDialog
from src.desktop.widgets.system_status_bar import SystemStatusBarWidget

__all__ = [
    "MainWindow",
    "run_desktop_app",
    "StrategyChartWidget",
    "ConsensusPanelWidget",
    "KillSwitchConfirmationDialog",
    "SystemStatusBarWidget",
]
