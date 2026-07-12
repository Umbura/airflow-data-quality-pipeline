from __future__ import annotations

from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from retail_pipeline.io import load_raw_frames, write_csv, write_json
from retail_pipeline.quality import (
    QualityGateError,
    checks_to_report,
    validate_raw_frames,
)
from retail_pipeline.settings import PROJECT_ROOT
from retail_pipeline.settings import processed_dir as default_processed_dir
from retail_pipeline.settings import raw_dir as default_raw_dir
from retail_pipeline.settings import reports_dir as default_reports_dir
from retail_pipeline.warehouse import build_warehouse


@dataclass(frozen=True)
class PipelineRunSummary:
    run_id: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    failed_stage: str | None
    raw_rows: dict[str, int]
    quality: dict[str, int]
    marts: dict[str, dict[str, Any]]
    outputs: dict[str, str]
    error: dict[str, str] | None


def _mart_summary(frame) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "columns": list(frame.columns),
    }


def _isoformat(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _run_id(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S%fZ")


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def _quality_summary(report: dict[str, Any]) -> dict[str, int]:
    return {
        "total_checks": int(report["total_checks"]),
        "passed_checks": int(report["passed_checks"]),
        "failed_checks": int(report["failed_checks"]),
    }


def publish_failure_summary(
    error: Exception,
    failed_stage: str,
    *,
    reports_dir: Path | None = None,
    run_id: str | None = None,
    started_at: str | None = None,
    validation: dict[str, Any] | None = None,
    warehouse: dict[str, Any] | None = None,
) -> PipelineRunSummary:
    reports_path = reports_dir or default_reports_dir()
    validation = validation or {}
    warehouse = warehouse or {}
    finished = datetime.now(UTC)
    summary_started_at = started_at or validation.get("started_at") or _isoformat(finished)
    started = datetime.fromisoformat(summary_started_at.replace("Z", "+00:00"))

    if isinstance(error, QualityGateError):
        raw_rows = error.raw_rows
        quality = _quality_summary(checks_to_report(error.checks))
    else:
        raw_rows = validation.get("raw_rows", {})
        quality = validation.get(
            "quality", {"total_checks": 0, "passed_checks": 0, "failed_checks": 0}
        )

    outputs = {
        **validation.get("outputs", {}),
        **warehouse.get("outputs", {}),
    }
    if isinstance(error, QualityGateError) and "quality_report" not in outputs:
        outputs["quality_report"] = _display_path(reports_path / "quality_report.json")

    summary = PipelineRunSummary(
        run_id=run_id or validation.get("run_id") or _run_id(started),
        status="failed",
        started_at=summary_started_at,
        finished_at=_isoformat(finished),
        duration_seconds=round((finished - started).total_seconds(), 3),
        failed_stage=failed_stage,
        raw_rows=raw_rows,
        quality=quality,
        marts=warehouse.get("marts", {}),
        outputs=outputs,
        error={"type": type(error).__name__, "message": str(error)},
    )
    write_json(reports_path / "run_summary.json", asdict(summary))
    return summary


def run_quality_stage(
    raw_dir: Path | None = None,
    reports_dir: Path | None = None,
    *,
    run_id: str | None = None,
    started_at: str | None = None,
) -> dict[str, Any]:
    raw_path = raw_dir or default_raw_dir()
    reports_path = reports_dir or default_reports_dir()
    quality_path = reports_path / "quality_report.json"
    stage_started = datetime.now(UTC)

    frames = load_raw_frames(raw_path)
    raw_rows = {name: int(len(frame)) for name, frame in frames.items()}
    checks = validate_raw_frames(frames, fail_fast=False)
    quality_report = checks_to_report(checks)
    quality_report.update(
        {
            "run_id": run_id or _run_id(stage_started),
            "generated_at": _isoformat(datetime.now(UTC)),
            "raw_rows": raw_rows,
        }
    )
    write_json(quality_path, quality_report)

    validation = {
        "run_id": quality_report["run_id"],
        "started_at": started_at or _isoformat(stage_started),
        "raw_rows": raw_rows,
        "quality": _quality_summary(quality_report),
        "outputs": {"quality_report": _display_path(quality_path)},
    }
    if quality_report["status"] == "failed":
        error = QualityGateError(checks, raw_rows)
        with suppress(OSError):
            publish_failure_summary(
                error,
                "quality",
                reports_dir=reports_path,
                validation=validation,
            )
        raise error

    return validation


def run_warehouse_stage(
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
) -> dict[str, Any]:
    raw_path = raw_dir or default_raw_dir()
    processed_path = processed_dir or default_processed_dir()
    marts_path = processed_path / "marts"
    db_path = processed_path / "warehouse.duckdb"

    processed_path.mkdir(parents=True, exist_ok=True)
    marts_path.mkdir(parents=True, exist_ok=True)

    frames = load_raw_frames(raw_path)
    marts = build_warehouse(frames, db_path)
    outputs = {"warehouse": _display_path(db_path)}
    for mart_name, frame in marts.items():
        csv_path = marts_path / f"{mart_name}.csv"
        write_csv(csv_path, frame)
        outputs[mart_name] = _display_path(csv_path)

    return {
        "marts": {name: _mart_summary(frame) for name, frame in marts.items()},
        "outputs": outputs,
    }


def publish_success_summary(
    validation: dict[str, Any],
    warehouse: dict[str, Any],
    reports_dir: Path | None = None,
) -> PipelineRunSummary:
    reports_path = reports_dir or default_reports_dir()
    finished_at = datetime.now(UTC)
    started_at = datetime.fromisoformat(validation["started_at"].replace("Z", "+00:00"))
    summary = PipelineRunSummary(
        run_id=validation["run_id"],
        status="success",
        started_at=validation["started_at"],
        finished_at=_isoformat(finished_at),
        duration_seconds=round((finished_at - started_at).total_seconds(), 3),
        failed_stage=None,
        raw_rows=validation["raw_rows"],
        quality=validation["quality"],
        marts=warehouse["marts"],
        outputs={**validation["outputs"], **warehouse["outputs"]},
        error=None,
    )
    write_json(reports_path / "run_summary.json", asdict(summary))
    return summary


def run_pipeline(
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> PipelineRunSummary:
    raw_path = raw_dir or default_raw_dir()
    processed_path = processed_dir or default_processed_dir()
    reports_path = reports_dir or default_reports_dir()
    reports_path.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC)
    pipeline_run_id = _run_id(started)
    stage = "quality"
    validation: dict[str, Any] = {}
    warehouse: dict[str, Any] = {}

    try:
        validation = run_quality_stage(
            raw_path,
            reports_path,
            run_id=pipeline_run_id,
            started_at=_isoformat(started),
        )
        stage = "warehouse"
        warehouse = run_warehouse_stage(raw_path, processed_path)
        stage = "publish_summary"
        return publish_success_summary(validation, warehouse, reports_path)
    except Exception as exc:
        with suppress(OSError):
            publish_failure_summary(
                exc,
                stage,
                reports_dir=reports_path,
                run_id=pipeline_run_id,
                started_at=_isoformat(started),
                validation=validation,
                warehouse=warehouse,
            )
        raise
