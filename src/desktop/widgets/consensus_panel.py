"""
Consensus Deliberation Panel — PySide6 Widget.

Displays the real-time voting, metrics, and rationales for all six analytical agents:
  - Agent 1: The Scout (Regime, session, swing levels)
  - Agent 2: The News Analyst (USD blackout countdown, data staleness)
  - Agent 3: The Chart Analyst (Part 3 strategy sequence, FVG, entry candle)
  - Agent 4: The Skeptic (VETO AUTHORITY: rollover window, spread/SL, wicks)
  - Agent 5: The Risk Manager (VETO AUTHORITY: 1% risk, lot size, daily limits)
  - Agent 6: The Execution Manager (Broker order status, attached SL/TP verification)

Plus Central Coordinator Verdict Badge (APPROVED / VETOED / PENDING).
"""
from __future__ import annotations

from typing import Any

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QtCore = None
    QtGui = None
    QtWidgets = None

from src.agents.coordinator import CoordinatorVerdict


class ConsensusPanelWidget:
    """Consensus deliberations panel showing 6 agent cards and coordinator verdict."""

    def __init__(self, parent=None):
        if PYQT_AVAILABLE:
            self.widget = QtWidgets.QWidget(parent)
            self._agent_cards: dict[str, dict[str, QtWidgets.QLabel]] = {}
            self._verdict_label: QtWidgets.QLabel | None = None
            self._decision_label: QtWidgets.QLabel | None = None
            self._init_ui()
        else:
            self.widget = None

    def get_widget(self):
        return self.widget

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Panel Header
        header = QtWidgets.QLabel("AGENT CONSENSUS DELIBERATION")
        header.setStyleSheet("font-weight: bold; font-size: 14px; color: #F1F5F9; letter-spacing: 1px;")
        layout.addWidget(header)

        # Verdict Banner
        self._verdict_container = QtWidgets.QFrame()
        self._verdict_container.setStyleSheet(
            "background-color: #151C2D; border: 1px solid #232C45; border-radius: 6px; padding: 10px;"
        )
        verdict_layout = QtWidgets.QHBoxLayout(self._verdict_container)
        
        v_title = QtWidgets.QLabel("COORDINATOR VERDICT:")
        v_title.setStyleSheet("font-weight: bold; color: #94A3B8;")
        verdict_layout.addWidget(v_title)

        self._verdict_label = QtWidgets.QLabel("AWAITING SETUP")
        self._verdict_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #F59E0B; background-color: #2D2312; padding: 4px 10px; border-radius: 4px;"
        )
        verdict_layout.addWidget(self._verdict_label)
        verdict_layout.addStretch()

        self._decision_label = QtWidgets.QLabel("ID: --")
        self._decision_label.setStyleSheet("color: #64748B; font-family: monospace;")
        verdict_layout.addWidget(self._decision_label)

        layout.addWidget(self._verdict_container)

        # Scroll Area for 6 Agent Cards
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        cards_widget = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)

        agent_configs = [
            ("The Scout", "Agent 1", "Session, Market Regimes & Swings"),
            ("The News Analyst", "Agent 2", "USD High-Impact Risk & Blackouts"),
            ("The Chart Analyst", "Agent 3", "Part 3 Strategy Engine"),
            ("The Skeptic", "Agent 4 (VETO)", "Independent Challenger"),
            ("The Risk Manager", "Agent 5 (VETO)", "1% Risk & Daily Safety Rules"),
            ("The Execution Manager", "Agent 6", "Pre-Attached SL/TP Broker Bridge"),
        ]

        for name, role, desc in agent_configs:
            card = self._create_agent_card(name, role, desc)
            self.cards_layout.addWidget(card)

        scroll.setWidget(cards_widget)
        layout.addWidget(scroll)

    def _create_agent_card(self, name: str, role: str, desc: str) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #101522; border: 1px solid #1E293B; border-radius: 6px; padding: 8px; }"
        )
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setSpacing(4)

        # Header row
        hdr_row = QtWidgets.QHBoxLayout()
        name_lbl = QtWidgets.QLabel(f"{name} <span style='color: #64748B;'>[{role}]</span>")
        name_lbl.setStyleSheet("font-weight: bold; color: #F8FAFC;")
        hdr_row.addWidget(name_lbl)
        hdr_row.addStretch()

        status_lbl = QtWidgets.QLabel("IDLE")
        status_lbl.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #94A3B8; background: #1E293B; padding: 2px 6px; border-radius: 3px;"
        )
        hdr_row.addWidget(status_lbl)
        card_layout.addLayout(hdr_row)

        desc_lbl = QtWidgets.QLabel(desc)
        desc_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        card_layout.addWidget(desc_lbl)

        # Rationale detail
        detail_lbl = QtWidgets.QLabel("No active deliberation.")
        detail_lbl.setWordWrap(True)
        detail_lbl.setStyleSheet("color: #CBD5E1; font-size: 11px; margin-top: 4px;")
        card_layout.addWidget(detail_lbl)

        self._agent_cards[name] = {
            "status": status_lbl,
            "detail": detail_lbl,
            "frame": card,
        }
        return card

    def update_consensus(self, verdict: CoordinatorVerdict, decisions: list[dict[str, Any]] | None = None):
        """Update display with consensus results."""
        if not PYQT_AVAILABLE or not self._verdict_label:
            return

        # Update verdict badge
        v_str = verdict.value
        self._verdict_label.setText(v_str)

        if verdict == CoordinatorVerdict.APPROVED:
            self._verdict_label.setStyleSheet(
                "font-weight: bold; font-size: 13px; color: #10B981; background-color: #064E3B; padding: 4px 10px; border-radius: 4px;"
            )
        elif "VETOED" in v_str:
            self._verdict_label.setStyleSheet(
                "font-weight: bold; font-size: 13px; color: #EF4444; background-color: #7F1D1D; padding: 4px 10px; border-radius: 4px;"
            )
        else:
            self._verdict_label.setStyleSheet(
                "font-weight: bold; font-size: 13px; color: #F59E0B; background-color: #2D2312; padding: 4px 10px; border-radius: 4px;"
            )

        if decisions:
            self._decision_label.setText(f"ID: {decisions[0].get('decision_id', '--')[:8]}")
            for d in decisions:
                agent = d.get("agent_name", "")
                for card_name, widgets in self._agent_cards.items():
                    if agent.lower() in card_name.lower():
                        voted = d.get("vote", "PASS")
                        widgets["status"].setText(voted)
                        if voted == "VETO":
                            widgets["status"].setStyleSheet(
                                "font-size: 11px; font-weight: bold; color: #EF4444; background: #7F1D1D; padding: 2px 6px; border-radius: 3px;"
                            )
                        elif voted in ("PASS", "APPROVE"):
                            widgets["status"].setStyleSheet(
                                "font-size: 11px; font-weight: bold; color: #10B981; background: #064E3B; padding: 2px 6px; border-radius: 3px;"
                            )
                        else:
                            widgets["status"].setStyleSheet(
                                "font-size: 11px; font-weight: bold; color: #F59E0B; background: #2D2312; padding: 2px 6px; border-radius: 3px;"
                            )

                        rationale = d.get("rationale", "")
                        widgets["detail"].setText(rationale)
