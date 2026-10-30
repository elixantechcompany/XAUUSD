"""
Structured logging configuration using structlog.

Call configure_logging() once at application start.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog


def configure_logging(
    level: str = "INFO",
    log_dir: Path | None = None,
    app_name: str = "fvg_trader",
) -> None:
    """Configure structlog + stdlib logging."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / f"{app_name}.log", encoding="utf-8")
        fh.setLevel(numeric_level)
        handlers.append(fh)

    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        handlers=handlers,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if level == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
