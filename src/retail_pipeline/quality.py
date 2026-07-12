from __future__ import annotations

from collections.abc import Collection
from dataclasses import asdict, dataclass
from typing import Any, Literal

import pandas as pd

QualitySeverity = Literal["critical", "warning"]

REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "customers": frozenset({"customer_id", "country", "segment", "first_invoice_date"}),
    "orders": frozenset({"order_id", "customer_id", "order_date", "status"}),
    "order_items": frozenset({"order_id", "product_id", "description", "quantity", "unit_price"}),
}
NOT_NULL_COLUMNS = {
    "customers": ("customer_id", "country", "segment"),
    "orders": ("order_id", "customer_id", "order_date", "status"),
    "order_items": ("order_id", "product_id", "description", "quantity", "unit_price"),
}
NOT_BLANK_COLUMNS = {
    "customers": ("customer_id", "country", "segment"),
    "orders": ("order_id", "customer_id", "status"),
    "order_items": ("order_id", "product_id", "description"),
}
UNIQUE_COLUMNS = (("customers", "customer_id"), ("orders", "order_id"))
ACCEPTED_VALUE_COLUMNS = (
    ("customers", "segment", frozenset({"domestic", "export"})),
    ("orders", "status", frozenset({"paid", "canceled"})),
)
POSITIVE_FINITE_COLUMNS = (("order_items", "quantity"), ("order_items", "unit_price"))
DATE_COLUMNS = (("customers", "first_invoice_date"), ("orders", "order_date"))


@dataclass(frozen=True)
class ForeignKeyConstraint:
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str


FOREIGN_KEYS = (
    ForeignKeyConstraint("orders", "customer_id", "customers", "customer_id"),
    ForeignKeyConstraint("order_items", "order_id", "orders", "order_id"),
)


@dataclass(frozen=True)
class QualityCheck:
    name: str
    passed: bool
    severity: QualitySeverity
    failed_rows: int
    details: dict[str, Any]


class QualityGateError(RuntimeError):
    def __init__(
        self,
        checks: list[QualityCheck],
        raw_rows: dict[str, int] | None = None,
    ) -> None:
        failed = [
            check.name for check in checks if not check.passed and check.severity == "critical"
        ]
        super().__init__(f"Critical data quality checks failed: {', '.join(failed)}")
        self.checks = checks
        self.raw_rows = raw_rows or {}


def _check_table_present(frame_name: str, frames: dict[str, pd.DataFrame]) -> QualityCheck:
    present = frame_name in frames
    return QualityCheck(
        name=f"{frame_name}.table_present",
        passed=present,
        severity="critical",
        failed_rows=0 if present else 1,
        details={"table": frame_name},
    )


def _check_not_empty(frame_name: str, frame: pd.DataFrame) -> QualityCheck:
    return QualityCheck(
        name=f"{frame_name}.not_empty",
        passed=not frame.empty,
        severity="critical",
        failed_rows=0 if not frame.empty else 1,
        details={"rows": len(frame)},
    )


def _check_required_columns(
    frame_name: str,
    frame: pd.DataFrame,
    required_columns: Collection[str],
) -> QualityCheck:
    missing = sorted(set(required_columns) - set(frame.columns))
    return QualityCheck(
        name=f"{frame_name}.required_columns",
        passed=not missing,
        severity="critical",
        failed_rows=0,
        details={"missing_columns": missing},
    )


def _check_not_null(
    frame_name: str,
    frame: pd.DataFrame,
    columns: tuple[str, ...],
) -> QualityCheck:
    failed_rows = int(frame[list(columns)].isna().any(axis=1).sum())
    return QualityCheck(
        name=f"{frame_name}.not_null",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"columns": list(columns)},
    )


def _check_not_blank(
    frame_name: str,
    frame: pd.DataFrame,
    columns: tuple[str, ...],
) -> QualityCheck:
    blank_cells = frame[list(columns)].apply(
        lambda series: series.astype("string").str.strip().eq("")
    )
    failed_rows = int(blank_cells.fillna(False).any(axis=1).sum())
    return QualityCheck(
        name=f"{frame_name}.not_blank",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"columns": list(columns)},
    )


def _check_unique(frame_name: str, frame: pd.DataFrame, column: str) -> QualityCheck:
    failed_rows = int(frame[column].duplicated(keep=False).sum())
    return QualityCheck(
        name=f"{frame_name}.{column}.unique",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"column": column},
    )


def _check_positive_finite(frame_name: str, frame: pd.DataFrame, column: str) -> QualityCheck:
    numeric_values = pd.to_numeric(frame[column], errors="coerce")
    invalid_mask = (
        numeric_values.isna()
        | numeric_values.isin([float("inf"), float("-inf")])
        | (numeric_values <= 0)
    )
    invalid_values = (
        frame.loc[invalid_mask, column]
        .astype("string")
        .dropna()
        .drop_duplicates()
        .head(20)
        .tolist()
    )
    failed_rows = int(invalid_mask.sum())
    return QualityCheck(
        name=f"{frame_name}.{column}.positive_finite",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"column": column, "invalid_values": invalid_values},
    )


def _check_values(
    frame_name: str,
    frame: pd.DataFrame,
    column: str,
    accepted: frozenset[str],
) -> QualityCheck:
    invalid_mask = frame[column].isna() | ~frame[column].isin(accepted)
    invalid_values = sorted(frame.loc[invalid_mask, column].dropna().unique().tolist())
    failed_rows = int(invalid_mask.sum())
    return QualityCheck(
        name=f"{frame_name}.{column}.accepted_values",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={
            "accepted_values": sorted(accepted),
            "invalid_values": invalid_values,
            "null_rows": int(frame[column].isna().sum()),
        },
    )


def _check_parseable_date(frame_name: str, frame: pd.DataFrame, column: str) -> QualityCheck:
    parsed = pd.to_datetime(frame[column], errors="coerce")
    invalid_mask = parsed.isna()
    invalid_values = (
        frame.loc[invalid_mask, column]
        .astype("string")
        .dropna()
        .drop_duplicates()
        .head(20)
        .tolist()
    )
    failed_rows = int(invalid_mask.sum())
    return QualityCheck(
        name=f"{frame_name}.{column}.parseable_date",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"column": column, "invalid_values": invalid_values},
    )


def _check_foreign_key(
    frames: dict[str, pd.DataFrame],
    constraint: ForeignKeyConstraint,
) -> QualityCheck:
    child = frames[constraint.child_table]
    parent = frames[constraint.parent_table]
    parent_values = set(parent[constraint.parent_column].dropna())
    missing_mask = child[constraint.child_column].isna() | ~child[constraint.child_column].isin(
        parent_values
    )
    missing_values = sorted(
        child.loc[missing_mask, constraint.child_column].dropna().unique().tolist()
    )
    failed_rows = int(missing_mask.sum())
    return QualityCheck(
        name=(
            f"{constraint.child_table}.{constraint.child_column}.fk_"
            f"{constraint.parent_table}.{constraint.parent_column}"
        ),
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={
            "missing_values": missing_values[:20],
            "null_rows": int(child[constraint.child_column].isna().sum()),
        },
    )


def _available_frame(
    frames: dict[str, pd.DataFrame],
    frame_name: str,
    columns: Collection[str],
) -> pd.DataFrame | None:
    frame = frames.get(frame_name)
    if frame is None or not set(columns).issubset(frame.columns):
        return None
    return frame


def _structural_checks(frames: dict[str, pd.DataFrame]) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    for frame_name, required_columns in REQUIRED_COLUMNS.items():
        checks.append(_check_table_present(frame_name, frames))
        frame = frames.get(frame_name)
        if frame is None:
            continue
        checks.extend(
            [
                _check_required_columns(frame_name, frame, required_columns),
                _check_not_empty(frame_name, frame),
            ]
        )
    return checks


def _completeness_checks(frames: dict[str, pd.DataFrame]) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    for frame_name, columns in NOT_NULL_COLUMNS.items():
        if (frame := _available_frame(frames, frame_name, columns)) is not None:
            checks.append(_check_not_null(frame_name, frame, columns))
    for frame_name, columns in NOT_BLANK_COLUMNS.items():
        if (frame := _available_frame(frames, frame_name, columns)) is not None:
            checks.append(_check_not_blank(frame_name, frame, columns))
    return checks


def _constraint_checks(frames: dict[str, pd.DataFrame]) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    for frame_name, column in UNIQUE_COLUMNS:
        if (frame := _available_frame(frames, frame_name, (column,))) is not None:
            checks.append(_check_unique(frame_name, frame, column))
    for frame_name, column, accepted in ACCEPTED_VALUE_COLUMNS:
        if (frame := _available_frame(frames, frame_name, (column,))) is not None:
            checks.append(_check_values(frame_name, frame, column, accepted))
    return checks


def _type_checks(frames: dict[str, pd.DataFrame]) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    for frame_name, column in POSITIVE_FINITE_COLUMNS:
        if (frame := _available_frame(frames, frame_name, (column,))) is not None:
            checks.append(_check_positive_finite(frame_name, frame, column))
    for frame_name, column in DATE_COLUMNS:
        if (frame := _available_frame(frames, frame_name, (column,))) is not None:
            checks.append(_check_parseable_date(frame_name, frame, column))
    return checks


def _content_checks(frames: dict[str, pd.DataFrame]) -> list[QualityCheck]:
    return [
        *_completeness_checks(frames),
        *_constraint_checks(frames),
        *_type_checks(frames),
    ]


def _referential_checks(frames: dict[str, pd.DataFrame]) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    for constraint in FOREIGN_KEYS:
        child = _available_frame(
            frames,
            constraint.child_table,
            (constraint.child_column,),
        )
        parent = _available_frame(
            frames,
            constraint.parent_table,
            (constraint.parent_column,),
        )
        if child is not None and parent is not None:
            checks.append(_check_foreign_key(frames, constraint))
    return checks


def validate_raw_frames(
    frames: dict[str, pd.DataFrame],
    *,
    fail_fast: bool = True,
) -> list[QualityCheck]:
    checks = [
        *_structural_checks(frames),
        *_content_checks(frames),
        *_referential_checks(frames),
    ]
    critical_failure = any(not check.passed and check.severity == "critical" for check in checks)
    if fail_fast and critical_failure:
        raw_rows = {name: len(frame) for name, frame in frames.items()}
        raise QualityGateError(checks, raw_rows)
    return checks


def checks_to_report(checks: list[QualityCheck]) -> dict[str, Any]:
    failed_checks = [check for check in checks if not check.passed]
    critical_failures = [check.name for check in failed_checks if check.severity == "critical"]
    return {
        "status": "failed" if critical_failures else "passed",
        "total_checks": len(checks),
        "passed_checks": sum(check.passed for check in checks),
        "failed_checks": len(failed_checks),
        "critical_failures": critical_failures,
        "checks": [asdict(check) for check in checks],
    }
