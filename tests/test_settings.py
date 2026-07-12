from __future__ import annotations

import logging
from pathlib import Path

import pytest

from retail_pipeline.logging_config import configure_logging
from retail_pipeline.settings import (
    ConfigurationError,
    api_port,
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


@pytest.mark.parametrize("value", ["invalid", "0", "65536"])
def test_api_port_rejects_invalid_values(
    value: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RETAIL_API_PORT", value)

    with pytest.raises(ConfigurationError, match="RETAIL_API_PORT"):
        api_port()


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
