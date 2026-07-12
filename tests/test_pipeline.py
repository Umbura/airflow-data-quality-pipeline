from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

import retail_pipeline.pipeline as pipeline_module
from retail_pipeline.pipeline import run_pipeline
from retail_pipeline.quality import QualityGateError


def test_run_pipeline_generates_reports_and_marts(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw"
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"

    summary = run_pipeline(raw_dir=raw_dir, processed_dir=processed_dir, reports_dir=reports_dir)

    assert summary.status == "success"
    assert summary.quality["failed_checks"] == 0
    assert (reports_dir / "quality_report.json").exists()
    assert (reports_dir / "run_summary.json").exists()
    assert (processed_dir / "marts" / "daily_revenue.csv").exists()
    assert (processed_dir / "marts" / "country_revenue.csv").exists()
    assert summary.marts["daily_revenue"]["rows"] >= 1
    assert summary.started_at.endswith("Z")
    assert summary.finished_at.endswith("Z")
    assert summary.failed_stage is None
    assert summary.error is None


def test_run_pipeline_is_idempotent(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = project_root / "data" / "raw"
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"

    first = run_pipeline(raw_dir, processed_dir, reports_dir)
    second = run_pipeline(raw_dir, processed_dir, reports_dir)

    assert first.raw_rows == second.raw_rows
    assert first.marts == second.marts
    assert first.run_id != second.run_id


def test_run_pipeline_persists_failure_report_before_blocking_outputs(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    shutil.copytree(project_root / "data" / "raw", raw_dir)

    orders_path = raw_dir / "orders.csv"
    orders = pd.read_csv(orders_path).drop(columns=["status"])
    orders.to_csv(orders_path, index=False)

    with pytest.raises(QualityGateError):
        run_pipeline(raw_dir, processed_dir, reports_dir)

    summary = json.loads((reports_dir / "run_summary.json").read_text(encoding="utf-8"))
    quality = json.loads((reports_dir / "quality_report.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["failed_stage"] == "quality"
    assert summary["error"]["type"] == "QualityGateError"
    assert quality["status"] == "failed"
    assert not (processed_dir / "warehouse.duckdb").exists()


def test_run_pipeline_reports_warehouse_failure(tmp_path: Path, monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[1]
    reports_dir = tmp_path / "reports"

    def fail_warehouse(*_args, **_kwargs):
        raise RuntimeError("warehouse unavailable")

    monkeypatch.setattr(pipeline_module, "run_warehouse_stage", fail_warehouse)

    with pytest.raises(RuntimeError, match="warehouse unavailable"):
        pipeline_module.run_pipeline(
            project_root / "data" / "raw",
            tmp_path / "processed",
            reports_dir,
        )

    summary = json.loads((reports_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["failed_stage"] == "warehouse"
    assert summary["quality"]["failed_checks"] == 0
    assert summary["error"]["type"] == "RuntimeError"
