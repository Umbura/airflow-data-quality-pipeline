from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import retail_pipeline.datasets.uci_online_retail as dataset_module
from retail_pipeline.datasets.uci_online_retail import (
    CSV_MIRROR_URL,
    SourceSchemaError,
    _normalize_transactions,
    prepare_uci_sample,
)


def _source_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "InvoiceNo": " 10001 ",
                "StockCode": " P1 ",
                "Description": " Product ",
                "Quantity": 2,
                "InvoiceDate": "2010-12-01 08:26:00",
                "UnitPrice": 3.5,
                "CustomerID": "12345.0",
                "Country": " United Kingdom ",
            },
            {
                "InvoiceNo": "C10002",
                "StockCode": "P2",
                "Description": "Returned product",
                "Quantity": -1,
                "InvoiceDate": "2010-12-02 09:00:00",
                "UnitPrice": 2.0,
                "CustomerID": "12345.0",
                "Country": "United Kingdom",
            },
            {
                "InvoiceNo": "10003",
                "StockCode": "P3",
                "Description": "Missing customer",
                "Quantity": 1,
                "InvoiceDate": "2010-12-03 09:00:00",
                "UnitPrice": 1.0,
                "CustomerID": pd.NA,
                "Country": "United Kingdom",
            },
            {
                "InvoiceNo": "10004",
                "StockCode": "P4",
                "Description": "   ",
                "Quantity": 1,
                "InvoiceDate": "2010-12-04 09:00:00",
                "UnitPrice": 1.0,
                "CustomerID": "12345.0",
                "Country": "United Kingdom",
            },
            {
                "InvoiceNo": "10005",
                "StockCode": "P5",
                "Description": "Infinite price",
                "Quantity": 1,
                "InvoiceDate": "2010-12-05 09:00:00",
                "UnitPrice": float("inf"),
                "CustomerID": "12345.0",
                "Country": "United Kingdom",
            },
            {
                "InvoiceNo": "10006",
                "StockCode": "P6",
                "Description": "Fractional quantity",
                "Quantity": 1.5,
                "InvoiceDate": "2010-12-06 09:00:00",
                "UnitPrice": 1.0,
                "CustomerID": "12345.0",
                "Country": "United Kingdom",
            },
            {
                "InvoiceNo": "10007",
                "StockCode": "P7",
                "Description": "Missing country",
                "Quantity": 1,
                "InvoiceDate": "2010-12-07 09:00:00",
                "UnitPrice": 1.0,
                "CustomerID": "12345.0",
                "Country": " ",
            },
        ]
    )


def test_normalize_transactions_cleans_and_classifies_source_rows() -> None:
    frames, report = _normalize_transactions(_source_frame())

    customers = frames["customers"]
    orders = frames["orders"].set_index("order_id")
    items = frames["order_items"]
    reasons = report["drop_reasons_before_overlap"]

    assert report["source_rows"] == 7
    assert report["normalized_rows"] == 2
    assert report["dropped_rows"] == 5
    assert report["output_rows"] == {"customers": 1, "orders": 2, "order_items": 2}
    assert customers.iloc[0]["customer_id"] == "12345"
    assert customers.iloc[0]["country"] == "United Kingdom"
    assert orders.loc["10001", "status"] == "paid"
    assert orders.loc["C10002", "status"] == "canceled"
    assert set(items["quantity"]) == {1, 2}
    assert reasons["missing_or_blank_customer_id"] == 1
    assert reasons["missing_or_blank_description"] == 1
    assert reasons["missing_or_blank_country"] == 1
    assert reasons["invalid_unit_price"] == 1
    assert reasons["invalid_quantity"] == 1


def test_normalize_transactions_reports_missing_source_columns() -> None:
    with pytest.raises(SourceSchemaError) as error:
        _normalize_transactions(pd.DataFrame({"InvoiceNo": ["10001"]}))

    assert "CustomerID" in error.value.missing_columns
    assert "UnitPrice" in error.value.missing_columns


def test_normalize_transactions_preserves_positive_sub_cent_prices() -> None:
    source = _source_frame().iloc[[0]].copy()
    source.loc[:, "UnitPrice"] = 0.001

    frames, report = _normalize_transactions(source)

    assert report["normalized_rows"] == 1
    assert frames["order_items"].iloc[0]["unit_price"] == pytest.approx(0.001)


def test_prepare_uci_sample_writes_normalized_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_frame()
    calls: list[tuple[str, int | None]] = []

    def fake_read_csv(url: str, *, nrows: int | None = None) -> pd.DataFrame:
        calls.append((url, nrows))
        return source.head(nrows).copy() if nrows is not None else source.copy()

    monkeypatch.setattr(dataset_module.pd, "read_csv", fake_read_csv)
    raw_dir = tmp_path / "raw"
    reports_dir = tmp_path / "reports"

    report = prepare_uci_sample(
        max_rows=2,
        source_url=CSV_MIRROR_URL,
        raw_output_dir=raw_dir,
        report_output_dir=reports_dir,
    )

    persisted_report = json.loads(
        (reports_dir / "dataset_preparation_report.json").read_text(encoding="utf-8")
    )
    assert calls == [(CSV_MIRROR_URL, 2)]
    assert report == persisted_report
    assert (raw_dir / "customers.csv").exists()
    assert (raw_dir / "orders.csv").exists()
    assert (raw_dir / "order_items.csv").exists()


def test_prepare_uci_sample_rejects_negative_row_limit() -> None:
    with pytest.raises(ValueError, match="max_rows"):
        prepare_uci_sample(max_rows=-1)


def test_prepare_uci_sample_uses_environment_dataset_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_frame()
    calls: list[tuple[str, int | None]] = []

    def fake_read_csv(url: str, *, nrows: int | None = None) -> pd.DataFrame:
        calls.append((url, nrows))
        return source.copy()

    monkeypatch.setenv("RETAIL_DATASET_CSV_URL", "https://data.example/retail.csv")
    monkeypatch.setenv("RETAIL_DATASET_MAX_ROWS", "0")
    monkeypatch.setattr(dataset_module.pd, "read_csv", fake_read_csv)

    report = prepare_uci_sample(
        raw_output_dir=tmp_path / "raw",
        report_output_dir=tmp_path / "reports",
    )

    assert calls == [("https://data.example/retail.csv", None)]
    assert report["rows_requested"] == "all"
    assert report["dataset_scope"] == "full"
