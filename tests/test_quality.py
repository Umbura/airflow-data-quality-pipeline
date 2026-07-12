from __future__ import annotations

import pandas as pd
import pytest

from retail_pipeline.quality import QualityGateError, validate_raw_frames


def test_validate_raw_frames_passes_for_valid_data() -> None:
    frames = {
        "customers": pd.DataFrame(
            [
                {
                    "customer_id": "C001",
                    "country": "United Kingdom",
                    "segment": "domestic",
                    "first_invoice_date": "2026-01-01",
                }
            ]
        ),
        "orders": pd.DataFrame(
            [{"order_id": "O1", "customer_id": "C001", "order_date": "2026-06-01", "status": "paid"}]
        ),
        "order_items": pd.DataFrame(
            [
                {
                    "order_id": "O1",
                    "product_id": "P1",
                    "description": "Data course",
                    "quantity": 1,
                    "unit_price": 100.0,
                }
            ]
        ),
    }

    checks = validate_raw_frames(frames)

    assert checks
    assert all(check.passed for check in checks)


def test_validate_raw_frames_blocks_orphan_order_item() -> None:
    frames = {
        "customers": pd.DataFrame(
            [
                {
                    "customer_id": "C001",
                    "country": "United Kingdom",
                    "segment": "domestic",
                    "first_invoice_date": "2026-01-01",
                }
            ]
        ),
        "orders": pd.DataFrame(
            [{"order_id": "O1", "customer_id": "C001", "order_date": "2026-06-01", "status": "paid"}]
        ),
        "order_items": pd.DataFrame(
            [
                {
                    "order_id": "O-missing",
                    "product_id": "P1",
                    "description": "Data course",
                    "quantity": 1,
                    "unit_price": 100.0,
                }
            ]
        ),
    }

    with pytest.raises(QualityGateError):
        validate_raw_frames(frames)


def test_validate_raw_frames_reports_missing_column_instead_of_key_error() -> None:
    frames = {
        "customers": pd.DataFrame(
            [{"customer_id": "C001", "country": "Brazil", "segment": "export"}]
        ),
        "orders": pd.DataFrame(
            [{"order_id": "O1", "customer_id": "C001", "order_date": "2026-06-01"}]
        ),
        "order_items": pd.DataFrame(
            [
                {
                    "order_id": "O1",
                    "product_id": "P1",
                    "description": "Course",
                    "quantity": 1,
                    "unit_price": 10.0,
                }
            ]
        ),
    }

    with pytest.raises(QualityGateError) as error:
        validate_raw_frames(frames)

    failed_names = {check.name for check in error.value.checks if not check.passed}
    assert "customers.required_columns" in failed_names
    assert "orders.required_columns" in failed_names


def test_validate_raw_frames_blocks_invalid_dates_and_numeric_values() -> None:
    frames = {
        "customers": pd.DataFrame(
            [
                {
                    "customer_id": "C001",
                    "country": "Brazil",
                    "segment": "export",
                    "first_invoice_date": "invalid-date",
                }
            ]
        ),
        "orders": pd.DataFrame(
            [
                {
                    "order_id": "O1",
                    "customer_id": "C001",
                    "order_date": "invalid-date",
                    "status": "paid",
                }
            ]
        ),
        "order_items": pd.DataFrame(
            [
                {
                    "order_id": "O1",
                    "product_id": "P1",
                    "description": "Course",
                    "quantity": "invalid",
                    "unit_price": 10.0,
                }
            ]
        ),
    }

    with pytest.raises(QualityGateError) as error:
        validate_raw_frames(frames)

    failed_names = {check.name for check in error.value.checks if not check.passed}
    assert "customers.first_invoice_date.parseable_date" in failed_names
    assert "orders.order_date.parseable_date" in failed_names
    assert "order_items.quantity.positive" in failed_names
