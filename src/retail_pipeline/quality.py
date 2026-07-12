from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "customers": {"customer_id", "country", "segment", "first_invoice_date"},
    "orders": {"order_id", "customer_id", "order_date", "status"},
    "order_items": {"order_id", "product_id", "description", "quantity", "unit_price"},
}


@dataclass(frozen=True)
class QualityCheck:
    name: str
    passed: bool
    severity: str
    failed_rows: int
    details: dict[str, Any]


class QualityGateError(RuntimeError):
    def __init__(
        self,
        checks: list[QualityCheck],
        raw_rows: dict[str, int] | None = None,
    ) -> None:
        failed = [check.name for check in checks if not check.passed and check.severity == "critical"]
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
        details={"rows": int(len(frame))},
    )


def _check_required_columns(
    frame_name: str,
    frame: pd.DataFrame,
    required_columns: set[str],
) -> QualityCheck:
    missing = sorted(required_columns - set(frame.columns))
    return QualityCheck(
        name=f"{frame_name}.required_columns",
        passed=not missing,
        severity="critical",
        failed_rows=0,
        details={"missing_columns": missing},
    )


def _check_not_null(frame_name: str, frame: pd.DataFrame, columns: list[str]) -> QualityCheck:
    failed_rows = int(frame[columns].isna().any(axis=1).sum())
    return QualityCheck(
        name=f"{frame_name}.not_null",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"columns": columns},
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


def _check_positive(frame_name: str, frame: pd.DataFrame, column: str) -> QualityCheck:
    numeric_values = pd.to_numeric(frame[column], errors="coerce")
    invalid_mask = numeric_values.isna() | (numeric_values <= 0)
    invalid_values = (
        frame.loc[invalid_mask, column].astype("string").dropna().drop_duplicates().head(20).tolist()
    )
    failed_rows = int(invalid_mask.sum())
    return QualityCheck(
        name=f"{frame_name}.{column}.positive",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"column": column, "invalid_values": invalid_values},
    )


def _check_values(frame_name: str, frame: pd.DataFrame, column: str, accepted: set[str]) -> QualityCheck:
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
        frame.loc[invalid_mask, column].astype("string").dropna().drop_duplicates().head(20).tolist()
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
    child_name: str,
    child: pd.DataFrame,
    child_column: str,
    parent_name: str,
    parent: pd.DataFrame,
    parent_column: str,
) -> QualityCheck:
    parent_values = set(parent[parent_column].dropna())
    missing_mask = child[child_column].isna() | ~child[child_column].isin(parent_values)
    missing_values = sorted(child.loc[missing_mask, child_column].dropna().unique().tolist())
    failed_rows = int(missing_mask.sum())
    return QualityCheck(
        name=f"{child_name}.{child_column}.fk_{parent_name}.{parent_column}",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={
            "missing_values": missing_values[:20],
            "null_rows": int(child[child_column].isna().sum()),
        },
    )


def validate_raw_frames(frames: dict[str, pd.DataFrame], *, fail_fast: bool = True) -> list[QualityCheck]:
    checks = [_check_table_present(name, frames) for name in REQUIRED_COLUMNS]

    for frame_name, required_columns in REQUIRED_COLUMNS.items():
        if frame_name not in frames:
            continue
        checks.extend(
            [
                _check_required_columns(frame_name, frames[frame_name], required_columns),
                _check_not_empty(frame_name, frames[frame_name]),
            ]
        )

    customers = frames.get("customers")
    orders = frames.get("orders")
    items = frames.get("order_items")

    if customers is not None:
        if {"customer_id", "country", "segment"}.issubset(customers.columns):
            checks.append(_check_not_null("customers", customers, ["customer_id", "country", "segment"]))
        if "customer_id" in customers:
            checks.append(_check_unique("customers", customers, "customer_id"))
        if "segment" in customers:
            checks.append(_check_values("customers", customers, "segment", {"domestic", "export"}))
        if "first_invoice_date" in customers:
            checks.append(_check_parseable_date("customers", customers, "first_invoice_date"))

    if orders is not None:
        if {"order_id", "customer_id", "order_date", "status"}.issubset(orders.columns):
            checks.append(
                _check_not_null("orders", orders, ["order_id", "customer_id", "order_date", "status"])
            )
        if "order_id" in orders:
            checks.append(_check_unique("orders", orders, "order_id"))
        if "status" in orders:
            checks.append(_check_values("orders", orders, "status", {"paid", "canceled"}))
        if "order_date" in orders:
            checks.append(_check_parseable_date("orders", orders, "order_date"))

    if items is not None:
        item_columns = {"order_id", "product_id", "description", "quantity", "unit_price"}
        if item_columns.issubset(items.columns):
            checks.append(_check_not_null("order_items", items, sorted(item_columns)))
        if "quantity" in items:
            checks.append(_check_positive("order_items", items, "quantity"))
        if "unit_price" in items:
            checks.append(_check_positive("order_items", items, "unit_price"))

    if (
        orders is not None
        and customers is not None
        and "customer_id" in orders
        and "customer_id" in customers
    ):
        checks.append(
            _check_foreign_key(
                "orders", orders, "customer_id", "customers", customers, "customer_id"
            )
        )
    if items is not None and orders is not None and "order_id" in items and "order_id" in orders:
        checks.append(
            _check_foreign_key("order_items", items, "order_id", "orders", orders, "order_id")
        )

    if fail_fast and any(not check.passed and check.severity == "critical" for check in checks):
        raw_rows = {name: int(len(frame)) for name, frame in frames.items()}
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
