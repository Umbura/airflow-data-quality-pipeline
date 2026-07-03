from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class QualityCheck:
    name: str
    passed: bool
    severity: str
    failed_rows: int
    details: dict[str, Any]


class QualityGateError(RuntimeError):
    def __init__(self, checks: list[QualityCheck]) -> None:
        failed = [check.name for check in checks if not check.passed and check.severity == "critical"]
        super().__init__(f"Critical data quality checks failed: {', '.join(failed)}")
        self.checks = checks


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
    failed_rows = int(frame[column].duplicated().sum())
    return QualityCheck(
        name=f"{frame_name}.{column}.unique",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"column": column},
    )


def _check_positive(frame_name: str, frame: pd.DataFrame, column: str) -> QualityCheck:
    failed_rows = int((frame[column] <= 0).sum())
    return QualityCheck(
        name=f"{frame_name}.{column}.positive",
        passed=failed_rows == 0,
        severity="critical",
        failed_rows=failed_rows,
        details={"column": column},
    )


def _check_values(frame_name: str, frame: pd.DataFrame, column: str, accepted: set[str]) -> QualityCheck:
    invalid_mask = ~frame[column].isin(accepted)
    invalid_values = sorted(frame.loc[invalid_mask, column].dropna().unique().tolist())
    return QualityCheck(
        name=f"{frame_name}.{column}.accepted_values",
        passed=not invalid_values,
        severity="critical",
        failed_rows=int(invalid_mask.sum()),
        details={"accepted_values": sorted(accepted), "invalid_values": invalid_values},
    )


def _check_foreign_key(
    child_name: str,
    child: pd.DataFrame,
    child_column: str,
    parent_name: str,
    parent: pd.DataFrame,
    parent_column: str,
) -> QualityCheck:
    missing_mask = ~child[child_column].isin(set(parent[parent_column]))
    missing_values = sorted(child.loc[missing_mask, child_column].dropna().unique().tolist())
    return QualityCheck(
        name=f"{child_name}.{child_column}.fk_{parent_name}.{parent_column}",
        passed=not missing_values,
        severity="critical",
        failed_rows=int(missing_mask.sum()),
        details={"missing_values": missing_values[:20]},
    )


def validate_raw_frames(frames: dict[str, pd.DataFrame], *, fail_fast: bool = True) -> list[QualityCheck]:
    customers = frames["customers"]
    orders = frames["orders"]
    items = frames["order_items"]

    checks = [
        _check_required_columns(
            "customers",
            customers,
            {"customer_id", "country", "segment", "first_invoice_date"},
        ),
        _check_required_columns("orders", orders, {"order_id", "customer_id", "order_date", "status"}),
        _check_required_columns(
            "order_items",
            items,
            {"order_id", "product_id", "description", "quantity", "unit_price"},
        ),
        _check_not_null("customers", customers, ["customer_id", "country", "segment"]),
        _check_not_null("orders", orders, ["order_id", "customer_id", "order_date", "status"]),
        _check_not_null(
            "order_items", items, ["order_id", "product_id", "description", "quantity", "unit_price"]
        ),
        _check_unique("customers", customers, "customer_id"),
        _check_unique("orders", orders, "order_id"),
        _check_values("orders", orders, "status", {"paid", "canceled"}),
        _check_values("customers", customers, "segment", {"domestic", "export"}),
        _check_positive("order_items", items, "quantity"),
        _check_positive("order_items", items, "unit_price"),
        _check_foreign_key("orders", orders, "customer_id", "customers", customers, "customer_id"),
        _check_foreign_key("order_items", items, "order_id", "orders", orders, "order_id"),
    ]

    if fail_fast and any(not check.passed and check.severity == "critical" for check in checks):
        raise QualityGateError(checks)
    return checks


def checks_to_report(checks: list[QualityCheck]) -> dict[str, Any]:
    return {
        "total_checks": len(checks),
        "passed_checks": sum(check.passed for check in checks),
        "failed_checks": sum(not check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
    }
