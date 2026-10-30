"""
Unit tests for Windows Credential Manager integration (keyring).
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch

from src.utils.credentials import CredentialManager, BrokerCredentials


class TestCredentialManager:
    def test_store_and_retrieve_mock_keyring(self):
        vault: dict[tuple[str, str], str] = {}

        def mock_set(service, username, password):
            vault[(service, username)] = password

        def mock_get(service, username):
            return vault.get((service, username))

        def mock_del(service, username):
            vault.pop((service, username), None)

        with patch("keyring.set_password", side_effect=mock_set), \
             patch("keyring.get_password", side_effect=mock_get), \
             patch("keyring.delete_password", side_effect=mock_del):

            mgr = CredentialManager(service_name="test_service")
            ok = mgr.store_credentials(
                account_id=12345678,
                password="SecretPassword123!",
                server="Exness-MT5Trial12",
                path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
            )
            assert ok is True

            creds = mgr.get_credentials()
            assert creds is not None
            assert creds.account_id == 12345678
            assert creds.password == "SecretPassword123!"
            assert creds.server == "Exness-MT5Trial12"
            assert creds.path == r"C:\Program Files\MetaTrader 5\terminal64.exe"

            # Delete
            del_ok = mgr.delete_credentials(12345678)
            assert del_ok is True

    def test_fallback_to_environment_variables(self, monkeypatch):
        monkeypatch.setenv("MT5_LOGIN", "88889999")
        monkeypatch.setenv("MT5_PASSWORD", "EnvSecretPass!")
        monkeypatch.setenv("MT5_SERVER", "Exness-Real10")
        monkeypatch.setenv("MT5_PATH", r"C:\MT5\terminal64.exe")

        with patch("keyring.get_password", return_value=None):
            mgr = CredentialManager(service_name="test_empty_vault")
            creds = mgr.get_credentials()
            assert creds is not None
            assert creds.account_id == 88889999
            assert creds.password == "EnvSecretPass!"
            assert creds.server == "Exness-Real10"
            assert creds.path == r"C:\MT5\terminal64.exe"
