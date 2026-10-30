"""
Candlestick and Technical Strategy Chart Widget — PySide6 & pyqtgraph.

Renders:
  - OHLC candlesticks (Green #10B981 for bullish, Red #EF4444 for bearish)
  - Confirmed Swing Highs and Swing Lows
  - Fair Value Gap (FVG) semi-transparent boxes (bullish green, bearish red)
  - Liquidity sweep markers and sweep extreme wick levels
  - First candle entering FVG (frozen range)
  - Entry, Stop Loss (red dashed), Take Profit (green dashed) horizontal lines
"""
from __future__ import annotations

from typing import Sequence, Any
import numpy as np

try:
    import pyqtgraph as pg
    from PySide6 import QtCore, QtGui, QtWidgets
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    pg = None
    QtCore = None
    QtGui = None
    QtWidgets = None

from src.data.candle import Candle
from src.strategy.strategy_core import FVG, Swing


if PYQT_AVAILABLE:
    class CandlestickItem(pg.GraphicsObject):
        """Custom pyqtgraph GraphicsItem for rendering fast OHLC candles."""

        def __init__(self, data: Sequence[dict]):
            """
            data: list of dicts with keys:
              't': float/int (index or timestamp)
              'open': float, 'high': float, 'low': float, 'close': float
            """
            super().__init__()
            self.data = data
            self.picture = QtGui.QPicture()
            self._generate_picture()

        def _generate_picture(self):
            p = QtGui.QPainter(self.picture)
            w = 0.35  # candle half-width

            bull_brush = QtGui.QBrush(QtGui.QColor(16, 185, 129))     # #10B981
            bull_pen = QtGui.QPen(QtGui.QColor(16, 185, 129), 1.0)
            bear_brush = QtGui.QBrush(QtGui.QColor(239, 68, 68))      # #EF4444
            bear_pen = QtGui.QPen(QtGui.QColor(239, 68, 68), 1.0)

            for d in self.data:
                t = d["t"]
                op = d["open"]
                hi = d["high"]
                lo = d["low"]
                cl = d["close"]

                if cl >= op:
                    p.setPen(bull_pen)
                    p.setBrush(bull_brush)
                    # Wick
                    p.drawLine(QtCore.QPointF(t, lo), QtCore.QPointF(t, hi))
                    # Body
                    p.drawRect(QtCore.QRectF(t - w, op, w * 2, max(cl - op, 0.0001)))
                else:
                    p.setPen(bear_pen)
                    p.setBrush(bear_brush)
                    # Wick
                    p.drawLine(QtCore.QPointF(t, lo), QtCore.QPointF(t, hi))
                    # Body
                    p.drawRect(QtCore.QRectF(t - w, cl, w * 2, max(op - cl, 0.0001)))

            p.end()

        def paint(self, p, *args):
            p.drawPicture(0, 0, self.picture)

        def boundingRect(self):
            return QtCore.QRectF(self.picture.boundingRect())


class StrategyChartWidget:
    """
    Wrapper providing candlestick, swing, FVG, and order visualization.
    Gracefully degrades or exposes mockable interface if Qt is not installed.
    """

    def __init__(self, parent=None):
        self.candles: list[Candle] = []
        self.swings: list[Any] = []
        self.fvgs: list[Any] = []
        self.levels: dict[str, float] = {}

        if PYQT_AVAILABLE:
            self.plot_widget = pg.PlotWidget(parent=parent)
            self._init_ui()
        else:
            self.plot_widget = None

    def _init_ui(self):
        self.plot_widget.setBackground("#0B0F19")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.setLabel("left", "Price", color="#94A3B8")
        self.plot_widget.setLabel("bottom", "Candle Bar Index (H1)", color="#94A3B8")

    def get_widget(self):
        return self.plot_widget

    def plot_candles(self, candles: Sequence[Candle]):
        """Render OHLC candles."""
        self.candles = list(candles)
        if not PYQT_AVAILABLE or not self.plot_widget:
            return

        self.plot_widget.clear()

        candle_data = [
            {
                "t": idx,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
            }
            for idx, c in enumerate(candles)
        ]
        item = CandlestickItem(candle_data)
        self.plot_widget.addItem(item)

        # Plot swings
        self._plot_swings()
        # Plot FVGs
        self._plot_fvgs()
        # Plot levels
        self._plot_trade_levels()

    def set_swings(self, swings: Sequence[Any]):
        self.swings = list(swings)
        if PYQT_AVAILABLE and self.plot_widget:
            self._plot_swings()

    def set_fvgs(self, fvgs: Sequence[Any]):
        self.fvgs = list(fvgs)
        if PYQT_AVAILABLE and self.plot_widget:
            self._plot_fvgs()

    def set_trade_levels(self, entry: float | None, sl: float | None, tp: float | None, sweep_extreme: float | None = None):
        self.levels = {
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "sweep_extreme": sweep_extreme,
        }
        if PYQT_AVAILABLE and self.plot_widget:
            self._plot_trade_levels()

    def _plot_swings(self):
        if not PYQT_AVAILABLE or not self.plot_widget:
            return

        time_to_idx = {c.time: idx for idx, c in enumerate(self.candles)}

        for sw in self.swings:
            sw_time = getattr(sw, "time", getattr(sw.candle, "time", None) if hasattr(sw, "candle") else None)
            sw_price = getattr(sw, "level", getattr(sw, "price", 0.0))
            sw_dir = getattr(sw, "direction", getattr(sw, "point_type", "HIGH"))
            if hasattr(sw_dir, "value"):
                sw_dir = sw_dir.value
            is_high = str(sw_dir).upper() in ("HIGH", "SWING_HIGH")

            idx = time_to_idx.get(sw_time)
            if idx is None:
                continue

            if is_high:
                # Swing High: Red downward marker
                arrow = pg.ArrowItem(
                    pos=(idx, sw_price),
                    angle=90,
                    brush=pg.mkBrush("#EF4444"),
                    pen=pg.mkPen("#EF4444"),
                    headLen=12,
                    tipAngle=35,
                )
                self.plot_widget.addItem(arrow)
                text = pg.TextItem(f"SH {sw_price:.2f}", color="#EF4444", anchor=(0.5, 1.5))
                text.setPos(idx, sw_price)
                self.plot_widget.addItem(text)
            else:
                # Swing Low: Green upward marker
                arrow = pg.ArrowItem(
                    pos=(idx, sw_price),
                    angle=-90,
                    brush=pg.mkBrush("#10B981"),
                    pen=pg.mkPen("#10B981"),
                    headLen=12,
                    tipAngle=35,
                )
                self.plot_widget.addItem(arrow)
                text = pg.TextItem(f"SL {sw_price:.2f}", color="#10B981", anchor=(0.5, -0.5))
                text.setPos(idx, sw_price)
                self.plot_widget.addItem(text)

    def _plot_fvgs(self):
        if not PYQT_AVAILABLE or not self.plot_widget:
            return

        time_to_idx = {c.time: idx for idx, c in enumerate(self.candles)}

        for fvg in self.fvgs:
            c1_time = getattr(fvg, "c1_time", None)
            c3_time = getattr(fvg, "c3_time", None)
            fvg_low = getattr(fvg, "fvg_low", getattr(fvg, "low", 0.0))
            fvg_high = getattr(fvg, "fvg_high", getattr(fvg, "high", 0.0))
            fvg_dir = getattr(fvg, "direction", "BULLISH")
            if hasattr(fvg_dir, "value"):
                fvg_dir = fvg_dir.value
            is_bull = str(fvg_dir).upper() == "BULLISH"

            c1_idx = time_to_idx.get(c1_time, 0)
            c3_idx = time_to_idx.get(c3_time, len(self.candles) - 1)
            end_idx = min(len(self.candles) - 1, c3_idx + 8)

            color = QtGui.QColor(16, 185, 129, 60) if is_bull else QtGui.QColor(239, 68, 68, 60)
            border = pg.mkPen("#10B981" if is_bull else "#EF4444", width=1.0)

            # Draw rectangular FVG region
            rect = QtWidgets.QGraphicsRectItem(c1_idx, min(fvg_low, fvg_high), max(1, end_idx - c1_idx), abs(fvg_high - fvg_low))
            rect.setBrush(QtGui.QBrush(color))
            rect.setPen(border)
            self.plot_widget.addItem(rect)

    def _plot_trade_levels(self):
        if not PYQT_AVAILABLE or not self.plot_widget:
            return

        # Entry level (Cyan dashed)
        if self.levels.get("entry"):
            line = pg.InfiniteLine(
                pos=self.levels["entry"],
                angle=0,
                pen=pg.mkPen("#06B6D4", width=1.5, style=QtCore.Qt.PenStyle.DashLine),
                label="ENTRY {value:.2f}",
                labelOpts={"position": 0.85, "color": "#06B6D4"},
            )
            self.plot_widget.addItem(line)

        # Stop Loss level (Red dashed)
        if self.levels.get("sl"):
            line = pg.InfiniteLine(
                pos=self.levels["sl"],
                angle=0,
                pen=pg.mkPen("#EF4444", width=1.5, style=QtCore.Qt.PenStyle.DashLine),
                label="SL {value:.2f}",
                labelOpts={"position": 0.85, "color": "#EF4444"},
            )
            self.plot_widget.addItem(line)

        # Take Profit level (Green dashed)
        if self.levels.get("tp"):
            line = pg.InfiniteLine(
                pos=self.levels["tp"],
                angle=0,
                pen=pg.mkPen("#10B981", width=1.5, style=QtCore.Qt.PenStyle.DashLine),
                label="TP {value:.2f}",
                labelOpts={"position": 0.85, "color": "#10B981"},
            )
            self.plot_widget.addItem(line)
