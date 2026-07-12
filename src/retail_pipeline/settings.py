from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


class ConfigurationError(ValueError):
    """Raised when an environment-based setting is invalid."""


def raw_dir() -> Path:
    return Path(os.getenv("RETAIL_PIPELINE_RAW_DIR", DEFAULT_RAW_DIR)).resolve()


def processed_dir() -> Path:
    return Path(os.getenv("RETAIL_PIPELINE_PROCESSED_DIR", DEFAULT_PROCESSED_DIR)).resolve()


def reports_dir() -> Path:
    return Path(os.getenv("RETAIL_PIPELINE_REPORTS_DIR", DEFAULT_REPORTS_DIR)).resolve()


def api_host() -> str:
    return os.getenv("RETAIL_API_HOST", "127.0.0.1")


def api_port() -> int:
    raw_port = os.getenv("RETAIL_API_PORT", "8000")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise ConfigurationError(f"RETAIL_API_PORT must be an integer: {raw_port}") from error
    if not 1 <= port <= 65_535:
        raise ConfigurationError(f"RETAIL_API_PORT must be between 1 and 65535: {port}")
    return port
