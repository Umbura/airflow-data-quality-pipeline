from __future__ import annotations

import pandas as pd
import pytest

from retail_pipeline.quality import QualityGateError, validate_raw_frames


def _failed_names(error: QualityGateError) -> set[str]:
    return {check.name for check in error.checks if not check.passed}


def test_validate_raw_frames_passes_for_valid_data(
    valid_frames: dict[str, pd.DataFrame],
) -> None:
    checks = validate_raw_frames(valid_frames)

    assert len(checks) == 25
    assert all(check.passed for check in checks)


def test_validate_raw_frames_blocks_orphan_order_item(
    valid_frames: dict[str, pd.DataFrame],
) -> None:
    valid_frames["order_items"].loc[0, "order_id"] = "O-missing"

    with pytest.raises(QualityGateError) as error:
        validate_raw_frames(valid_frames)

    assert "order_items.order_id.fk_orders.order_id" in _failed_names(error.value)


def test_validate_raw_frames_reports_missing_columns_instead_of_key_error(
    valid_frames: dict[str, pd.DataFrame],
) -> None:
    valid_frames["customers"] = valid_frames["customers"].drop(columns=["first_invoice_date"])
    valid_frames["orders"] = valid_frames["orders"].drop(columns=["status"])

    with pytest.raises(QualityGateError) as error:
        validate_raw_frames(valid_frames)

    failed_names = _failed_names(error.value)
    assert "customers.required_columns" in failed_names
    assert "orders.required_columns" in failed_names


def test_validate_raw_frames_reports_missing_table(
    valid_frames: dict[str, pd.DataFrame],
) -> None:
    del valid_frames["order_items"]

    with pytest.raises(QualityGateError) as error:
        validate_raw_frames(valid_frames)

    assert "order_items.table_present" in _failed_names(error.value)


def test_validate_raw_frames_blocks_invalid_dates_and_numeric_values(
    valid_frames: dict[str, pd.DataFrame],
) -> None:
    valid_frames["customers"].loc[0, "first_invoice_date"] = "invalid-date"
    valid_frames["orders"].loc[0, "order_date"] = "invalid-date"
    valid_frames["order_items"]["quantity"] = pd.Series(["invalid"], dtype="object")

    with pytest.raises(QualityGateError) as error:
        validate_raw_frames(valid_frames)

    failed_names = _failed_names(error.value)
    assert "customers.first_invoice_date.parseable_date" in failed_names
    assert "orders.order_date.parseable_date" in failed_names
    assert "order_items.quantity.positive_finite" in failed_names


def test_validate_raw_frames_blocks_blank_and_infinite_values(
    valid_frames: dict[str, pd.DataFrame],
) -> None:
    valid_frames["customers"].loc[0, "country"] = "   "
    valid_frames["order_items"].loc[0, "unit_price"] = float("inf")

    with pytest.raises(QualityGateError) as error:
        validate_raw_frames(valid_frames)

    failed_names = _failed_names(error.value)
    assert "customers.not_blank" in failed_names
    assert "order_items.unit_price.positive_finite" in failed_names
