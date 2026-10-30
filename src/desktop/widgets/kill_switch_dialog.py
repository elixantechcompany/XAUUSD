"""
Emergency Kill Switch Dialog — PySide6.

Enforces modal safety verification before executing emergency liquidation
of all broker positions and canceling pending strategy setups.
"""
from __future__ import annotations

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QtCore = None
    QtGui = None
    QtWidgets = None


class KillSwitchConfirmationDialog:
    """Modal double-confirmation dialog for Emergency Kill Switch."""

    @staticmethod
    def confirm(parent=None) -> bool:
        """
        Show emergency kill switch confirmation.
        Returns True if explicitly confirmed, False otherwise.
        """
        if not PYQT_AVAILABLE or not QtWidgets:
            return True

        dialog = QtWidgets.QDialog(parent)
        dialog.setWindowTitle("EMERGENCY KILL SWITCH ACTIVATION")
        dialog.setModal(True)
        dialog.resize(480, 260)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0B0F19;
                color: #F8FAFC;
                border: 2px solid #EF4444;
                border-radius: 8px;
            }
            QLabel {
                color: #F1F5F9;
            }
            QLineEdit {
                background-color: #101522;
                border: 1px solid #EF4444;
                border-radius: 4px;
                color: #F8FAFC;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QPushButton#killBtn {
                background-color: #DC2626;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton#killBtn:hover {
                background-color: #B91C1C;
            }
            QPushButton#cancelBtn {
                background-color: #1E293B;
                color: #94A3B8;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton#cancelBtn:hover {
                background-color: #334155;
                color: white;
            }
        """)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Warning Header
        warn_hdr = QtWidgets.QLabel("⚠️ EMERGENCY KILL SWITCH WARNING")
        warn_hdr.setStyleSheet("font-size: 16px; font-weight: bold; color: #EF4444;")
        layout.addWidget(warn_hdr)

        msg = QtWidgets.QLabel(
            "Activating the Emergency Kill Switch will:\n"
            "  1. Liquidate ALL open positions across all symbols immediately.\n"
            "  2. Invalidate and cancel all active strategy setups.\n"
            "  3. Lock the execution coordinator to prevent new orders.\n\n"
            "Type 'CONFIRM' below to execute liquidation:"
        )
        msg.setStyleSheet("color: #CBD5E1; line-height: 1.4;")
        layout.addWidget(msg)

        input_box = QtWidgets.QLineEdit()
        input_box.setPlaceholderText("TYPE CONFIRM HERE")
        layout.addWidget(input_box)

        # Buttons
        btn_box = QtWidgets.QHBoxLayout()
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(cancel_btn)

        kill_btn = QtWidgets.QPushButton("LIQUIDATE ALL POSITIONS")
        kill_btn.setObjectName("killBtn")
        kill_btn.setEnabled(False)

        def on_text_changed(text: str):
            kill_btn.setEnabled(text.strip().upper() == "CONFIRM")

        input_box.textChanged.connect(on_text_changed)
        kill_btn.clicked.connect(dialog.accept)
        btn_box.addWidget(kill_btn)

        layout.addLayout(btn_box)

        result = dialog.exec()
        return result == QtWidgets.QDialog.DialogCode.Accepted
