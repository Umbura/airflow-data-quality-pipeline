from __future__ import annotations

from pathlib import Path

from retail_pipeline.pipeline import run_pipeline


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
