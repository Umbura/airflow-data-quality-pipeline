from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from retail_pipeline.api import app
from retail_pipeline.pipeline import run_pipeline


def test_api_exposes_health_reports_and_paginated_marts(tmp_path: Path, monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[1]
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    run_pipeline(project_root / "data" / "raw", processed_dir, reports_dir)
    monkeypatch.setenv("RETAIL_PIPELINE_PROCESSED_DIR", str(processed_dir))
    monkeypatch.setenv("RETAIL_PIPELINE_REPORTS_DIR", str(reports_dir))

    with TestClient(app) as client:
        health = client.get("/health")
        metrics = client.get("/metrics")
        mart = client.get("/marts/customer-revenue", params={"limit": 5, "offset": 2})

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert metrics.status_code == 200
    assert metrics.json()["status"] == "success"
    assert mart.status_code == 200
    assert mart.json()["limit"] == 5
    assert mart.json()["offset"] == 2
    assert len(mart.json()["items"]) == 5


def test_api_reports_degraded_state_when_outputs_are_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RETAIL_PIPELINE_PROCESSED_DIR", str(tmp_path / "processed"))
    monkeypatch.setenv("RETAIL_PIPELINE_REPORTS_DIR", str(tmp_path / "reports"))

    with TestClient(app) as client:
        health = client.get("/health")
        metrics = client.get("/metrics")
        unknown_mart = client.get("/marts/not-a-mart")

    assert health.status_code == 200
    assert health.json()["status"] == "degraded"
    assert metrics.status_code == 404
    assert unknown_mart.status_code == 404
