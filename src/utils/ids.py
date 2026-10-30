"""Deterministic and random ID generation utilities."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime


def new_uuid() -> str:
    return str(uuid.uuid4())


def setup_id(symbol: str, direction: str, fvg_open_time: datetime) -> str:
    """Stable ID for a setup — same inputs always yield same ID."""
    raw = f"{symbol}|{direction}|{fvg_open_time.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def order_client_id(setup_id: str, attempt: int = 0) -> str:
    """Idempotent client order ID for a given setup attempt."""
    raw = f"{setup_id}|order|{attempt}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
