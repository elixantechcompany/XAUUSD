"""
Unit tests for Multi-Account Trade Copier API endpoints.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import app, copier_engine
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


def test_copier_accounts_list(client: TestClient):
    """GET /copier/accounts returns master account and registered children."""
    res = client.get("/copier/accounts")
    assert res.status_code == 200
    data = res.json()
    assert "master" in data
    assert "children" in data
    assert "terminal_online" in data
    assert isinstance(data["children"], list)


def test_register_and_delete_child_account(client: TestClient):
    """POST /copier/accounts registers child, then DELETE unregisters it."""
    fake_keyring = {}

    def mock_set(service, key, value):
        fake_keyring[f"{service}:{key}"] = value

    def mock_get(service, key):
        return fake_keyring.get(f"{service}:{key}")

    def mock_del(service, key):
        fake_keyring.pop(f"{service}:{key}", None)

    with patch("keyring.set_password", side_effect=mock_set), \
         patch("keyring.get_password", side_effect=mock_get), \
         patch("keyring.delete_password", side_effect=mock_del):

        payload = {
            "account_id": 99887766,
            "password": "TestChildPassword123!",
            "server": "Exness-MT5Real10",
            "label": "Test Real Account",
            "risk_pct": 1.0,
            "risk_multiplier": 1.5,
            "is_active": True,
            "max_slippage_pips": 3.0,
        }
        res = client.post("/copier/accounts", json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        assert 99887766 in copier_engine.child_accounts

        # Toggle active
        toggle_res = client.post("/copier/accounts/99887766/toggle")
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False

        # Delete account
        del_res = client.delete("/copier/accounts/99887766")
        assert del_res.status_code == 200
        assert 99887766 not in copier_engine.child_accounts


def test_copier_trades_endpoint(client: TestClient):
    """GET /copier/trades returns audit records."""
    res = client.get("/copier/trades")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_copier_kill_switch_endpoint(client: TestClient):
    """POST /copier/kill-switch liquidates positions and halts engine."""
    with patch.object(copier_engine, "close_all_accounts_positions", return_value={"master": 0}):
        res = client.post("/copier/kill-switch")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HALTED"
        assert data["action"] == "GLOBAL_KILL_SWITCH_EXECUTED"
