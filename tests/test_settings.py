from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from retail_pipeline.logging_config import configure_logging
from retail_pipeline.settings import (
    PROJECT_ROOT,
    ConfigurationError,
    api_port,
    dataset_csv_url,
    dataset_max_rows,
    load_project_environment,
    processed_dir,
    raw_dir,
    reports_dir,
)


def test_directory_settings_respect_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETAIL_PIPELINE_RAW_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("RETAIL_PIPELINE_PROCESSED_DIR", str(tmp_path / "processed"))
    monkeypatch.setenv("RETAIL_PIPELINE_REPORTS_DIR", str(tmp_path / "reports"))

    assert raw_dir() == (tmp_path / "raw").resolve()
    assert processed_dir() == (tmp_path / "processed").resolve()
    assert reports_dir() == (tmp_path / "reports").resolve()


def test_relative_directory_settings_are_resolved_from_project_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETAIL_PIPELINE_RAW_DIR", "build/configured-raw")

    assert raw_dir() == (PROJECT_ROOT / "build" / "configured-raw").resolve()


def test_project_environment_loads_only_retail_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "RETAIL_API_PORT=9123\nOPENAI_API_KEY=must-not-be-loaded\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("RETAIL_API_PORT", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    loaded = load_project_environment(env_file)

    assert loaded == frozenset({"RETAIL_API_PORT"})
    assert api_port() == 9123
    assert "OPENAI_API_KEY" not in os.environ


def test_project_environment_preserves_exported_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("RETAIL_API_PORT=9123\n", encoding="utf-8")
    monkeypatch.setenv("RETAIL_API_PORT", "9000")

    loaded = load_project_environment(env_file)

    assert loaded == frozenset()
    assert api_port() == 9000


@pytest.mark.parametrize("value", ["invalid", "0", "65536"])
def test_api_port_rejects_invalid_values(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETAIL_API_PORT", value)

    with pytest.raises(ConfigurationError, match="RETAIL_API_PORT"):
        api_port()


@pytest.mark.parametrize("value", ["invalid", "-1"])
def test_dataset_max_rows_rejects_invalid_values(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETAIL_DATASET_MAX_ROWS", value)

    with pytest.raises(ConfigurationError, match="RETAIL_DATASET_MAX_ROWS"):
        dataset_max_rows()


def test_dataset_url_rejects_blank_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETAIL_DATASET_CSV_URL", " ")

    with pytest.raises(ConfigurationError, match="RETAIL_DATASET_CSV_URL"):
        dataset_csv_url()


def test_configure_logging_uses_environment_level(monkeypatch: pytest.MonkeyPatch) -> None:
    configured: dict[str, object] = {}
    monkeypatch.setenv("RETAIL_LOG_LEVEL", "warning")
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: configured.update(kwargs))

    configure_logging()

    assert configured["level"] == logging.WARNING


def test_configure_logging_rejects_unknown_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETAIL_LOG_LEVEL", "verbose")

    with pytest.raises(ValueError, match="RETAIL_LOG_LEVEL"):
        configure_logging()
