"""
Secure Credential Management via Windows Credential Manager (keyring).

Role:
- Securely stores and retrieves Exness MetaTrader 5 account credentials.
- Interacts directly with the Windows Credential Manager API via `keyring`.
- ZERO plaintext storage in git, config files, or SQLite.
- Provides environment variable fallbacks (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH)
  for headless environments or containerized testing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from src.utils.logging_config import get_logger

log = get_logger(__name__)

SERVICE_NAME = "exness_mt5_trading_desk"


@dataclass(frozen=True)
class BrokerCredentials:
    """Credentials required to authenticate with an Exness MT5 account."""
    account_id: int
    password: str
    server: str
    path: str | None = None


class CredentialManager:
    """
    Manages secure broker credential persistence via Windows Credential Manager.
    """

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name

    def store_credentials(
        self,
        account_id: int | str,
        password: str,
        server: str,
        path: str | None = None,
    ) -> bool:
        """
        Store account password and metadata securely in Windows Credential Manager.
        """
        try:
            import keyring
            acct_str = str(account_id)
            # Store primary secret in Windows Credential Manager
            keyring.set_password(self.service_name, f"{acct_str}_password", password)
            keyring.set_password(self.service_name, f"{acct_str}_server", server)
            if path:
                keyring.set_password(self.service_name, f"{acct_str}_path", path)
            keyring.set_password(self.service_name, "last_active_account", acct_str)
            log.info("credentials_stored_securely", account_id=acct_str, server=server)
            return True
        except Exception as exc:
            log.error("failed_to_store_credentials", error=str(exc))
            return False

    def get_credentials(self, account_id: int | str | None = None) -> BrokerCredentials | None:
        """
        Retrieve credentials from Windows Credential Manager or environment variables.
        """
        acct_str: str | None = str(account_id) if account_id is not None else None

        # 1. Try Windows Credential Manager (keyring)
        try:
            import keyring
            if acct_str is None:
                acct_str = keyring.get_password(self.service_name, "last_active_account")

            if acct_str:
                password = keyring.get_password(self.service_name, f"{acct_str}_password")
                server = keyring.get_password(self.service_name, f"{acct_str}_server")
                path = keyring.get_password(self.service_name, f"{acct_str}_path")

                if password and server:
                    return BrokerCredentials(
                        account_id=int(acct_str),
                        password=password,
                        server=server,
                        path=path,
                    )
        except Exception as exc:
            log.debug("keyring_read_failed_or_empty", error=str(exc))

        # 2. Fallback to Environment Variables
        env_login = os.environ.get("MT5_LOGIN")
        env_password = os.environ.get("MT5_PASSWORD")
        env_server = os.environ.get("MT5_SERVER", "Exness-MT5Trial12")
        env_path = os.environ.get("MT5_PATH")

        if env_login and env_password:
            try:
                return BrokerCredentials(
                    account_id=int(env_login),
                    password=env_password,
                    server=env_server,
                    path=env_path,
                )
            except ValueError:
                log.warning("invalid_mt5_login_env_value", login=env_login)

        return None

    def delete_credentials(self, account_id: int | str) -> bool:
        """Delete stored credentials from Windows Credential Manager."""
        try:
            import keyring
            acct_str = str(account_id)
            for suffix in ("_password", "_server", "_path"):
                try:
                    keyring.delete_password(self.service_name, f"{acct_str}{suffix}")
                except Exception:
                    pass
            log.info("credentials_deleted", account_id=acct_str)
            return True
        except Exception as exc:
            log.error("failed_to_delete_credentials", error=str(exc))
            return False

    def store_child_account(
        self,
        account_id: int | str,
        password: str,
        server: str,
        label: str = "",
        risk_multiplier: float = 1.0,
    ) -> bool:
        """Store credentials for a child copy-trading account."""
        try:
            import keyring
            acct_str = str(account_id)
            keyring.set_password(self.service_name, f"{acct_str}_child_password", password)
            keyring.set_password(self.service_name, f"{acct_str}_child_server", server)
            keyring.set_password(self.service_name, f"{acct_str}_child_label", label)
            keyring.set_password(self.service_name, f"{acct_str}_child_multiplier", str(risk_multiplier))

            # Maintain index list of child accounts
            existing_str = keyring.get_password(self.service_name, "child_accounts_index") or ""
            existing_list = [x.strip() for x in existing_str.split(",") if x.strip()]
            if acct_str not in existing_list:
                existing_list.append(acct_str)
                keyring.set_password(self.service_name, "child_accounts_index", ",".join(existing_list))

            log.info("child_credentials_stored", account_id=acct_str, label=label)
            return True
        except Exception as exc:
            log.error("failed_to_store_child_credentials", error=str(exc))
            return False

    def get_child_accounts(self) -> list[dict]:
        """Retrieve all registered child copy-trading accounts."""
        results: list[dict] = []
        try:
            import keyring
            index_str = keyring.get_password(self.service_name, "child_accounts_index") or ""
            acct_ids = [x.strip() for x in index_str.split(",") if x.strip()]

            for acct_str in acct_ids:
                password = keyring.get_password(self.service_name, f"{acct_str}_child_password")
                server = keyring.get_password(self.service_name, f"{acct_str}_child_server")
                label = keyring.get_password(self.service_name, f"{acct_str}_child_label") or f"Child #{acct_str}"
                mult_str = keyring.get_password(self.service_name, f"{acct_str}_child_multiplier") or "1.0"

                if password and server:
                    results.append({
                        "account_id": int(acct_str),
                        "password": password,
                        "server": server,
                        "label": label,
                        "risk_multiplier": float(mult_str),
                    })
        except Exception as exc:
            log.debug("failed_to_read_child_accounts", error=str(exc))
        return results

    def delete_child_account(self, account_id: int | str) -> bool:
        """Remove a child copy-trading account."""
        try:
            import keyring
            acct_str = str(account_id)
            for suffix in ("_child_password", "_child_server", "_child_label", "_child_multiplier"):
                try:
                    keyring.delete_password(self.service_name, f"{acct_str}{suffix}")
                except Exception:
                    pass

            index_str = keyring.get_password(self.service_name, "child_accounts_index") or ""
            acct_ids = [x.strip() for x in index_str.split(",") if x.strip() and x.strip() != acct_str]
            keyring.set_password(self.service_name, "child_accounts_index", ",".join(acct_ids))

            log.info("child_account_deleted", account_id=acct_str)
            return True
        except Exception as exc:
            log.error("failed_to_delete_child_account", error=str(exc))
            return False
