from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import retail_pipeline.cli as cli_module
from retail_pipeline.pipeline import PipelineRunSummary, QualitySummary


def test_cli_runs_pipeline_with_explicit_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    captured_arguments: dict[str, Path | None] = {}
    summary = PipelineRunSummary(
        run_id="run-1",
        status="success",
        started_at="2026-01-01T00:00:00.000Z",
        finished_at="2026-01-01T00:00:01.000Z",
        duration_seconds=1.0,
        failed_stage=None,
        raw_rows={"customers": 1, "orders": 1, "order_items": 1},
        quality=QualitySummary(total_checks=25, passed_checks=25, failed_checks=0),
        marts={},
        outputs={},
        error=None,
    )

    def fake_run_pipeline(
        raw_dir: Path | None = None,
        processed_dir: Path | None = None,
        reports_dir: Path | None = None,
    ) -> PipelineRunSummary:
        captured_arguments.update(
            raw_dir=raw_dir,
            processed_dir=processed_dir,
            reports_dir=reports_dir,
        )
        return summary

    monkeypatch.setattr(cli_module, "configure_logging", lambda: None)
    monkeypatch.setattr(cli_module, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "retail-pipeline",
            "--raw-dir",
            str(raw_dir),
            "--processed-dir",
            str(processed_dir),
            "--reports-dir",
            str(reports_dir),
        ],
    )

    cli_module.main()

    assert captured_arguments == {
        "raw_dir": raw_dir,
        "processed_dir": processed_dir,
        "reports_dir": reports_dir,
    }
    assert json.loads(capsys.readouterr().out)["run_id"] == "run-1"
