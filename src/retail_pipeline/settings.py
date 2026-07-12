from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_DATASET_CSV_URL = (
    "https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/"
    "master/data/retail-data/all/online-retail-dataset.csv"
)
DEFAULT_DATASET_MAX_ROWS = 50_000


class ConfigurationError(ValueError):
    """Raised when an environment-based setting is invalid."""


def load_project_environment(env_file: Path = PROJECT_ENV_FILE) -> frozenset[str]:
    """Load project-owned settings without importing unrelated secrets."""
    loaded: set[str] = set()
    for key, value in dotenv_values(env_file).items():
        if not key.startswith("RETAIL_") or value is None or key in os.environ:
            continue
        os.environ[key] = value
        loaded.add(key)
    return frozenset(loaded)


load_project_environment()


def _configured_path(variable: str, default: Path) -> Path:
    configured = os.getenv(variable)
    if not configured:
        return default.resolve()
    path = Path(configured)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def raw_dir() -> Path:
    return _configured_path("RETAIL_PIPELINE_RAW_DIR", DEFAULT_RAW_DIR)


def processed_dir() -> Path:
    return _configured_path("RETAIL_PIPELINE_PROCESSED_DIR", DEFAULT_PROCESSED_DIR)


def reports_dir() -> Path:
    return _configured_path("RETAIL_PIPELINE_REPORTS_DIR", DEFAULT_REPORTS_DIR)


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


def dataset_csv_url() -> str:
    url = os.getenv("RETAIL_DATASET_CSV_URL", DEFAULT_DATASET_CSV_URL).strip()
    if not url:
        raise ConfigurationError("RETAIL_DATASET_CSV_URL must not be empty")
    return url


def dataset_max_rows() -> int:
    raw_limit = os.getenv("RETAIL_DATASET_MAX_ROWS", str(DEFAULT_DATASET_MAX_ROWS))
    try:
        limit = int(raw_limit)
    except ValueError as error:
        raise ConfigurationError(
            f"RETAIL_DATASET_MAX_ROWS must be an integer: {raw_limit}"
        ) from error
    if limit < 0:
        raise ConfigurationError(
            f"RETAIL_DATASET_MAX_ROWS must be zero or a positive integer: {limit}"
        )
    return limit
