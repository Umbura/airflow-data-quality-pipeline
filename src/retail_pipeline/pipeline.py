from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from retail_pipeline.io import load_raw_frames
from retail_pipeline.quality import checks_to_report, validate_raw_frames
from retail_pipeline.settings import processed_dir as default_processed_dir
from retail_pipeline.settings import raw_dir as default_raw_dir
from retail_pipeline.settings import reports_dir as default_reports_dir
from retail_pipeline.warehouse import build_warehouse


@dataclass(frozen=True)
class PipelineRunSummary:
    run_id: str
    status: str
    raw_rows: dict[str, int]
    quality: dict[str, int]
    marts: dict[str, dict[str, Any]]
    outputs: dict[str, str]


def _mart_summary(frame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
    }


def run_pipeline(
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> PipelineRunSummary:
    raw_path = raw_dir or default_raw_dir()
    processed_path = processed_dir or default_processed_dir()
    reports_path = reports_dir or default_reports_dir()
    marts_path = processed_path / "marts"
    db_path = processed_path / "warehouse.duckdb"

    processed_path.mkdir(parents=True, exist_ok=True)
    marts_path.mkdir(parents=True, exist_ok=True)
    reports_path.mkdir(parents=True, exist_ok=True)

    frames = load_raw_frames(raw_path)
    checks = validate_raw_frames(frames)
    quality_report = checks_to_report(checks)
    (reports_path / "quality_report.json").write_text(
        json.dumps(quality_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    marts = build_warehouse(frames, db_path)
    outputs = {
        "warehouse": str(db_path),
        "quality_report": str(reports_path / "quality_report.json"),
    }
    for mart_name, frame in marts.items():
        csv_path = marts_path / f"{mart_name}.csv"
        frame.to_csv(csv_path, index=False)
        outputs[mart_name] = str(csv_path)

    summary = PipelineRunSummary(
        run_id=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        status="success",
        raw_rows={name: int(len(frame)) for name, frame in frames.items()},
        quality={
            "total_checks": int(quality_report["total_checks"]),
            "passed_checks": int(quality_report["passed_checks"]),
            "failed_checks": int(quality_report["failed_checks"]),
        },
        marts={name: _mart_summary(frame) for name, frame in marts.items()},
        outputs=outputs,
    )
    (reports_path / "run_summary.json").write_text(
        json.dumps(asdict(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary
