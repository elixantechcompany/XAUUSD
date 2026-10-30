"""
Main Desktop Application Window — PySide6 quantitative interface.

Integrates:
  - StrategyChartWidget (Candlesticks, Swings, FVGs, Entry/SL/TP levels)
  - ConsensusPanelWidget (6-Agent deliberations & Central Coordinator verdict)
  - Orders & Strategy Setups Table
  - Prominent Emergency Kill Switch with modal double-confirmation
  - Real-time System Status Bar (<50 MB RAM monitor)
"""
from __future__ import annotations

import sys
from typing import Sequence, Any

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QtCore = None
    QtGui = None
    QtWidgets = None

from src.agents.coordinator import CentralCoordinator, CoordinatorVerdict
from src.desktop.widgets.candlestick_chart import StrategyChartWidget
from src.desktop.widgets.consensus_panel import ConsensusPanelWidget
from src.desktop.widgets.kill_switch_dialog import KillSwitchConfirmationDialog
from src.desktop.widgets.system_status_bar import SystemStatusBarWidget
from src.data.candle import Candle
from src.strategy.strategy_core import FVG, Swing
from src.utils.logging_config import get_logger

log = get_logger(__name__)


class MainWindow:
    """Quantitative Desktop Main Window combining Chart, Deliberations, and Controls."""

    def __init__(self, coordinator: CentralCoordinator | None = None):
        self.coordinator = coordinator or CentralCoordinator()
        self.current_symbol = "XAUUSD"
        self.chart_widget = StrategyChartWidget()
        self.consensus_panel = ConsensusPanelWidget()
        self.status_bar = SystemStatusBarWidget()

        if PYQT_AVAILABLE and QtWidgets and QtWidgets.QApplication.instance():
            self.app_window = QtWidgets.QMainWindow()
            self._init_ui()
        else:
            self.app_window = None

    def get_window(self):
        return self.app_window

    def show(self):
        if self.app_window:
            self.app_window.show()

    def _init_ui(self):
        self.app_window.setWindowTitle("AI TRADING DESK // LOCAL MULTI-AGENT QUANT (4GB RAM OPTIMIZED)")
        self.app_window.resize(1280, 800)
        self.app_window.setStyleSheet("""
            QMainWindow {
                background-color: #080C14;
                color: #F8FAFC;
            }
            QToolBar {
                background-color: #0D1321;
                border-bottom: 1px solid #1E293B;
                padding: 6px;
                spacing: 12px;
            }
            QComboBox {
                background-color: #151C2D;
                border: 1px solid #232C45;
                border-radius: 4px;
                color: #F8FAFC;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton#killBtn {
                background-color: #DC2626;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton#killBtn:hover {
                background-color: #B91C1C;
            }
            QTabWidget::pane {
                border: 1px solid #1E293B;
                background-color: #0B0F19;
            }
            QTabBar::tab {
                background-color: #101522;
                color: #94A3B8;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #151C2D;
                color: #F8FAFC;
                border-bottom: 2px solid #06B6D4;
            }
            QTableWidget {
                background-color: #0B0F19;
                alternate-background-color: #101522;
                border: none;
                color: #CBD5E1;
                gridline-color: #1E293B;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #151C2D;
                color: #94A3B8;
                font-weight: bold;
                padding: 6px;
                border: none;
            }
        """)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QtWidgets.QToolBar("Controls")
        toolbar.setMovable(False)
        self.app_window.addToolBar(toolbar)

        # Brand Label
        brand = QtWidgets.QLabel("QUANT AI DESK")
        brand.setStyleSheet("font-weight: bold; font-size: 14px; color: #06B6D4; padding-right: 8px;")
        toolbar.addWidget(brand)

        # Symbol Selector
        self.symbol_combo = QtWidgets.QComboBox()
        self.symbol_combo.addItems(["XAUUSD", "BTCUSD"])
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)
        toolbar.addWidget(self.symbol_combo)

        # Timeframe Badge
        tf_badge = QtWidgets.QLabel("TIMEFRAME: H1")
        tf_badge.setStyleSheet("color: #94A3B8; font-weight: bold; padding: 0 10px;")
        toolbar.addWidget(tf_badge)

        # Execution Mode Badge
        self.mode_badge = QtWidgets.QLabel("MODE: PAPER (SAFE)")
        self.mode_badge.setStyleSheet(
            "color: #10B981; font-weight: bold; background: #064E3B; padding: 4px 8px; border-radius: 4px;"
        )
        toolbar.addWidget(self.mode_badge)

        # Spacer
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Emergency Kill Switch Button
        kill_btn = QtWidgets.QPushButton("⚠️ EMERGENCY KILL SWITCH")
        kill_btn.setObjectName("killBtn")
        kill_btn.clicked.connect(self._on_kill_switch_clicked)
        toolbar.addWidget(kill_btn)

        # ── Central Splitter ──────────────────────────────────────────────────
        central_widget = QtWidgets.QWidget()
        self.app_window.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        v_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        # Top Splitter: Chart (Left) + Consensus Panel (Right)
        h_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        # Chart
        if self.chart_widget.get_widget():
            h_splitter.addWidget(self.chart_widget.get_widget())

        # Consensus Deliberation Panel
        if self.consensus_panel.get_widget():
            h_splitter.addWidget(self.consensus_panel.get_widget())

        h_splitter.setStretchFactor(0, 3)
        h_splitter.setStretchFactor(1, 2)
        v_splitter.addWidget(h_splitter)

        # Bottom Area: Tabbed data tables
        tabs = QtWidgets.QTabWidget()

        # Tab 1: Setups
        self.setups_table = self._create_data_table([
            "ID", "Symbol", "Direction", "State", "FVG Low", "FVG High", "Trigger", "SL", "TP", "R:R", "Updated"
        ])
        tabs.addTab(self.setups_table, "Active Strategy Setups (Part 3)")

        # Tab 2: Orders & Fills
        self.orders_table = self._create_data_table([
            "Ticket", "Symbol", "Direction", "Volume", "Open Price", "Stop Loss", "Take Profit", "Status", "Placed At"
        ])
        tabs.addTab(self.orders_table, "Broker Orders & Journal")

        v_splitter.addWidget(tabs)
        v_splitter.setStretchFactor(0, 3)
        v_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(v_splitter)

        # ── Status Bar ────────────────────────────────────────────────────────
        if self.status_bar.get_widget():
            self.app_window.setStatusBar(self.status_bar.get_widget())

    def _create_data_table(self, headers: list[str]) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        return table

    def _on_symbol_changed(self, symbol: str):
        self.current_symbol = symbol
        log.info("desktop_symbol_selected", symbol=symbol)

    def _on_kill_switch_clicked(self):
        confirmed = KillSwitchConfirmationDialog.confirm(self.app_window)
        if confirmed:
            log.warn("desktop_emergency_kill_switch_confirmed")
            self.coordinator.trigger_kill_switch("Activated via Desktop GUI Kill Switch Button")
            if hasattr(self, "status_bar"):
                self.status_bar.set_mt5_status(connected=False, mode="HALTED")
            QtWidgets.QMessageBox.critical(
                self.app_window,
                "KILL SWITCH EXECUTED",
                "Emergency Kill Switch is ACTIVE.\nAll pending setups canceled and broker positions liquidated.",
            )

    def update_market_view(
        self,
        candles: Sequence[Candle],
        swings: Sequence[Any],
        fvgs: Sequence[Any],
        trade_levels: dict[str, float] | None = None,
    ):
        """Update chart visualization with new market data."""
        self.chart_widget.plot_candles(candles)
        self.chart_widget.set_swings(swings)
        self.chart_widget.set_fvgs(fvgs)
        if trade_levels:
            self.chart_widget.set_trade_levels(
                entry=trade_levels.get("entry"),
                sl=trade_levels.get("sl"),
                tp=trade_levels.get("tp"),
                sweep_extreme=trade_levels.get("sweep_extreme"),
            )

    def update_consensus_view(self, verdict: CoordinatorVerdict, decisions: list[dict] | None = None):
        """Update consensus deliberation cards."""
        self.consensus_panel.update_consensus(verdict, decisions)


def run_desktop_app():
    """Launch the PySide6 desktop application."""
    if not PYQT_AVAILABLE:
        print("PySide6 is not installed. Install PySide6 to run the desktop application.")
        return

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
