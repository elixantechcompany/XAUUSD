"""
Unit tests for FastAPI endpoints — Milestone 5 (Dashboard, Control, Consensus, Orders).
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import app, coordinator
from src.state.models import Order, Setup, SetupState, SetupDirection
from src.utils.database import get_db


@pytest.fixture
def client(db: Session):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_endpoint(client: TestClient):
    """Health check is public and returns 200 with live_trading_enabled=False."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["live_trading_enabled"] is False


def test_dashboard_root_serves_html(client: TestClient):
    """Root GET / serves the quantitative dark dashboard HTML."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "AI TRADING DESK" in res.text
    assert "EMERGENCY KILL SWITCH" in res.text
    assert "6-Agent Deliberations" in res.text


def test_coordinator_consensus_endpoint(client: TestClient):
    """GET /coordinator/consensus returns coordinator state and 6 analytical agents."""
    res = client.get("/coordinator/consensus")
    assert res.status_code == 200
    data = res.json()
    assert "verdict" in data
    assert "agents" in data
    agents = data["agents"]
    assert "scout" in agents
    assert "news_analyst" in agents
    assert "chart_analyst" in agents
    assert "skeptic" in agents
    assert "risk_manager" in agents
    assert "execution_manager" in agents


def test_emergency_kill_switch_endpoint(client: TestClient, db: Session):
    """POST /control/kill-switch triggers emergency liquidation and halts coordinator."""
    coordinator.kill_switch_active = False
    coordinator.kill_switch_reason = None

    res = client.post("/control/kill-switch", json={"reason": "Test unit kill switch trigger"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HALTED"
    assert data["action"] == "EMERGENCY_KILL_SWITCH_EXECUTED"
    assert coordinator.kill_switch_active is True
    assert "Test unit kill switch trigger" in coordinator.kill_switch_reason


def test_orders_endpoint(client: TestClient, db: Session):
    """GET /orders returns persisted orders."""
    now = datetime.now(timezone.utc)
    # Create parent setup
    setup = Setup(
        id="setup-test-api-01",
        symbol="XAUUSD",
        timeframe="H1",
        direction=SetupDirection.BULLISH,
        state=SetupState.ENTRY_CONFIRMED,
        fvg_low=2030.0,
        fvg_high=2035.0,
        created_at=now,
        updated_at=now,
    )
    db.add(setup)
    db.commit()

    order = Order(
        id="order-test-api-01",
        setup_id="setup-test-api-01",
        symbol="XAUUSD",
        direction="BUY",
        execution_mode="paper",
        requested_at=now,
        requested_volume=0.15,
        requested_entry=2035.5,
        requested_sl=2028.0,
        requested_tp=2050.5,
        filled_at=now,
        filled_price=2035.5,
        filled_volume=0.15,
        status="FILLED",
        broker_ticket=888123,
    )
    db.add(order)
    db.commit()

    res = client.get("/orders")
    assert res.status_code == 200
    orders = res.json()
    assert len(orders) >= 1
    found = next((o for o in orders if o["id"] == "order-test-api-01"), None)
    assert found is not None
    assert found["symbol"] == "XAUUSD"
    assert found["direction"] == "BUY"
    assert found["open_price"] == 2035.5
    assert found["stop_loss"] == 2028.0
    assert found["take_profit"] == 2050.5
    assert found["broker_ticket"] == 888123
