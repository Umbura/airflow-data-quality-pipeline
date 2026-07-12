from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

import pandas as pd

from retail_pipeline.io import load_raw_frames, write_csv, write_json
from retail_pipeline.quality import QualityGateError, checks_to_report, validate_raw_frames
from retail_pipeline.settings import PROJECT_ROOT
from retail_pipeline.settings import processed_dir as default_processed_dir
from retail_pipeline.settings import raw_dir as default_raw_dir
from retail_pipeline.settings import reports_dir as default_reports_dir
from retail_pipeline.warehouse import build_warehouse

logger = logging.getLogger(__name__)

PipelineStage = Literal["quality", "warehouse", "publish_summary"]
PipelineStatus = Literal["success", "failed"]


class QualitySummary(TypedDict):
    total_checks: int
    passed_checks: int
    failed_checks: int


class MartSummary(TypedDict):
    rows: int
    columns: list[str]


class ValidationResult(TypedDict):
    run_id: str
    started_at: str
    raw_rows: dict[str, int]
    quality: QualitySummary
    outputs: dict[str, str]


class WarehouseResult(TypedDict):
    marts: dict[str, MartSummary]
    outputs: dict[str, str]


@dataclass(frozen=True)
class PipelineRunSummary:
    run_id: str
    status: PipelineStatus
    started_at: str
    finished_at: str
    duration_seconds: float
    failed_stage: PipelineStage | None
    raw_rows: dict[str, int]
    quality: QualitySummary
    marts: dict[str, MartSummary]
    outputs: dict[str, str]
    error: dict[str, str] | None


@dataclass(frozen=True)
class RunMetadata:
    run_id: str
    started_at: str


@dataclass(frozen=True)
class PipelineFailure:
    error: Exception
    stage: PipelineStage
    run: RunMetadata | None = None
    validation: ValidationResult | None = None
    warehouse: WarehouseResult | None = None


def _mart_summary(frame: pd.DataFrame) -> MartSummary:
    return {"rows": len(frame), "columns": frame.columns.tolist()}


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


def _quality_summary(report: dict[str, Any]) -> QualitySummary:
    return {
        "total_checks": int(report["total_checks"]),
        "passed_checks": int(report["passed_checks"]),
        "failed_checks": int(report["failed_checks"]),
    }


def _failure_metadata(failure: PipelineFailure, finished: datetime) -> RunMetadata:
    if failure.run is not None:
        return failure.run
    if failure.validation is not None:
        return RunMetadata(
            run_id=failure.validation["run_id"],
            started_at=failure.validation["started_at"],
        )
    return RunMetadata(run_id=_run_id(finished), started_at=_isoformat(finished))


def publish_failure_summary(
    failure: PipelineFailure,
    reports_dir: Path | None = None,
) -> PipelineRunSummary:
    reports_path = reports_dir or default_reports_dir()
    finished = datetime.now(UTC)
    metadata = _failure_metadata(failure, finished)
    started = datetime.fromisoformat(metadata.started_at.replace("Z", "+00:00"))

    if isinstance(failure.error, QualityGateError):
        raw_rows = failure.error.raw_rows
        quality = _quality_summary(checks_to_report(failure.error.checks))
    elif failure.validation is not None:
        raw_rows = failure.validation["raw_rows"]
        quality = failure.validation["quality"]
    else:
        raw_rows = {}
        quality = QualitySummary(total_checks=0, passed_checks=0, failed_checks=0)

    outputs: dict[str, str] = {}
    if failure.validation is not None:
        outputs.update(failure.validation["outputs"])
    if failure.warehouse is not None:
        outputs.update(failure.warehouse["outputs"])
    if isinstance(failure.error, QualityGateError) and "quality_report" not in outputs:
        outputs["quality_report"] = _display_path(reports_path / "quality_report.json")

    summary = PipelineRunSummary(
        run_id=metadata.run_id,
        status="failed",
        started_at=metadata.started_at,
        finished_at=_isoformat(finished),
        duration_seconds=round((finished - started).total_seconds(), 3),
        failed_stage=failure.stage,
        raw_rows=raw_rows,
        quality=quality,
        marts=failure.warehouse["marts"] if failure.warehouse is not None else {},
        outputs=outputs,
        error={"type": type(failure.error).__name__, "message": str(failure.error)},
    )
    write_json(reports_path / "run_summary.json", asdict(summary))
    return summary


def run_quality_stage(
    raw_dir: Path | None = None,
    reports_dir: Path | None = None,
    *,
    run_id: str | None = None,
    started_at: str | None = None,
) -> ValidationResult:
    raw_path = raw_dir or default_raw_dir()
    reports_path = reports_dir or default_reports_dir()
    quality_path = reports_path / "quality_report.json"
    stage_started = datetime.now(UTC)
    metadata = RunMetadata(
        run_id=run_id or _run_id(stage_started),
        started_at=started_at or _isoformat(stage_started),
    )

    logger.info("Quality stage started: raw_dir=%s", raw_path)
    frames = load_raw_frames(raw_path)
    raw_rows = {name: len(frame) for name, frame in frames.items()}
    checks = validate_raw_frames(frames, fail_fast=False)
    quality_report = checks_to_report(checks)
    quality_report.update(
        {
            "run_id": metadata.run_id,
            "generated_at": _isoformat(datetime.now(UTC)),
            "raw_rows": raw_rows,
        }
    )
    write_json(quality_path, quality_report)

    validation = ValidationResult(
        run_id=metadata.run_id,
        started_at=metadata.started_at,
        raw_rows=raw_rows,
        quality=_quality_summary(quality_report),
        outputs={"quality_report": _display_path(quality_path)},
    )
    if quality_report["status"] == "failed":
        error = QualityGateError(checks, raw_rows)
        logger.error("Quality stage failed: failed_checks=%s", quality_report["failed_checks"])
        with suppress(OSError):
            publish_failure_summary(
                PipelineFailure(error=error, stage="quality", run=metadata, validation=validation),
                reports_path,
            )
        raise error

    logger.info(
        "Quality stage completed: rows=%s checks=%s",
        sum(raw_rows.values()),
        quality_report["total_checks"],
    )
    return validation


def run_warehouse_stage(
    raw_dir: Path | None = None,
    processed_dir: Path | None = None,
) -> WarehouseResult:
    raw_path = raw_dir or default_raw_dir()
    processed_path = processed_dir or default_processed_dir()
    marts_path = processed_path / "marts"
    db_path = processed_path / "warehouse.duckdb"

    logger.info("Warehouse stage started: processed_dir=%s", processed_path)
    processed_path.mkdir(parents=True, exist_ok=True)
    marts_path.mkdir(parents=True, exist_ok=True)

    frames = load_raw_frames(raw_path)
    marts = build_warehouse(frames, db_path)
    outputs = {"warehouse": _display_path(db_path)}
    for mart_name, frame in marts.items():
        csv_path = marts_path / f"{mart_name}.csv"
        write_csv(csv_path, frame)
        outputs[mart_name] = _display_path(csv_path)

    logger.info("Warehouse stage completed: marts=%s", len(marts))
    return WarehouseResult(
        marts={name: _mart_summary(frame) for name, frame in marts.items()},
        outputs=outputs,
    )


def publish_success_summary(
    validation: ValidationResult,
    warehouse: WarehouseResult,
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
    logger.info("Run summary published: run_id=%s status=success", summary.run_id)
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
    metadata = RunMetadata(run_id=_run_id(started), started_at=_isoformat(started))
    stage: PipelineStage = "quality"
    validation: ValidationResult | None = None
    warehouse: WarehouseResult | None = None

    logger.info("Pipeline run started: run_id=%s", metadata.run_id)
    try:
        validation = run_quality_stage(
            raw_path,
            reports_path,
            run_id=metadata.run_id,
            started_at=metadata.started_at,
        )
        stage = "warehouse"
        warehouse = run_warehouse_stage(raw_path, processed_path)
        stage = "publish_summary"
        return publish_success_summary(validation, warehouse, reports_path)
    except Exception as error:
        logger.exception("Pipeline run failed: run_id=%s stage=%s", metadata.run_id, stage)
        with suppress(OSError):
            publish_failure_summary(
                PipelineFailure(
                    error=error,
                    stage=stage,
                    run=metadata,
                    validation=validation,
                    warehouse=warehouse,
                ),
                reports_path,
            )
        raise
