from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Final

import pandas as pd

from retail_pipeline.io import write_csv, write_json
from retail_pipeline.logging_config import configure_logging
from retail_pipeline.settings import raw_dir, reports_dir

logger = logging.getLogger(__name__)

UCI_SOURCE_PAGE: Final = "https://archive.ics.uci.edu/dataset/352/online%2Bretail"
CSV_MIRROR_URL: Final = (
    "https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/"
    "master/data/retail-data/all/online-retail-dataset.csv"
)
SOURCE_COLUMNS: Final = frozenset(
    {
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "InvoiceDate",
        "UnitPrice",
        "CustomerID",
        "Country",
    }
)
TEXT_COLUMNS: Final = (
    "order_id",
    "product_id",
    "description",
    "customer_id",
    "country",
)


class SourceSchemaError(ValueError):
    def __init__(self, missing_columns: list[str]) -> None:
        self.missing_columns = missing_columns
        super().__init__(
            f"Source dataset is missing required columns: {', '.join(missing_columns)}"
        )


def _validate_source_schema(frame: pd.DataFrame) -> None:
    missing_columns = sorted(SOURCE_COLUMNS - set(frame.columns))
    if missing_columns:
        raise SourceSchemaError(missing_columns)


def _status_from_invoice(invoice_no: str, quantity: int) -> str:
    if invoice_no.upper().startswith("C") or quantity < 0:
        return "canceled"
    return "paid"


def _aggregate_status(statuses: pd.Series) -> str:
    return "canceled" if statuses.eq("canceled").any() else "paid"


def _non_blank(series: pd.Series) -> pd.Series:
    return series.notna() & series.ne("")


def _finite(series: pd.Series) -> pd.Series:
    return series.notna() & ~series.isin([float("inf"), float("-inf")])


def _normalize_transactions(
    frame: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    _validate_source_schema(frame)
    source_rows = len(frame)
    normalized = frame.rename(
        columns={
            "InvoiceNo": "order_id",
            "StockCode": "product_id",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "order_date",
            "UnitPrice": "unit_price",
            "CustomerID": "customer_id",
            "Country": "country",
        }
    ).copy()

    for column in TEXT_COLUMNS:
        normalized[column] = normalized[column].astype("string").str.strip()
    normalized["customer_id"] = normalized["customer_id"].str.replace(r"\.0$", "", regex=True)
    normalized["quantity"] = pd.to_numeric(normalized["quantity"], errors="coerce")
    normalized["unit_price"] = pd.to_numeric(normalized["unit_price"], errors="coerce")
    normalized["order_date"] = pd.to_datetime(normalized["order_date"], errors="coerce")

    valid_text = {column: _non_blank(normalized[column]) for column in TEXT_COLUMNS}
    finite_quantity = _finite(normalized["quantity"])
    whole_quantity = normalized["quantity"].where(finite_quantity).mod(1).eq(0).fillna(False)
    valid_quantity = finite_quantity & normalized["quantity"].ne(0) & whole_quantity
    valid_price = _finite(normalized["unit_price"]) & normalized["unit_price"].gt(0)
    valid_date = normalized["order_date"].notna()

    valid_row = valid_date & valid_quantity & valid_price
    for column_validity in valid_text.values():
        valid_row &= column_validity
    cleaned = normalized.loc[valid_row].copy()

    cleaned["status"] = [
        _status_from_invoice(str(order_id), int(quantity))
        for order_id, quantity in zip(cleaned["order_id"], cleaned["quantity"], strict=True)
    ]
    cleaned["quantity"] = cleaned["quantity"].abs().astype(int)
    cleaned["unit_price"] = cleaned["unit_price"].round(2)
    cleaned["order_date"] = cleaned["order_date"].dt.date.astype(str)
    cleaned["segment"] = cleaned["country"].map(
        lambda country: "domestic" if country == "United Kingdom" else "export"
    )

    customers = (
        cleaned.sort_values(["customer_id", "order_date"])
        .groupby("customer_id", as_index=False)
        .agg(
            country=("country", "first"),
            segment=("segment", "first"),
            first_invoice_date=("order_date", "min"),
        )
        .sort_values("customer_id")
    )
    orders = (
        cleaned.groupby(["order_id", "customer_id"], as_index=False)
        .agg(order_date=("order_date", "min"), status=("status", _aggregate_status))
        .sort_values("order_id")
    )
    items = cleaned[
        ["order_id", "product_id", "description", "quantity", "unit_price"]
    ].sort_values(["order_id", "product_id"])

    report = {
        "source": "UCI Online Retail",
        "source_rows": source_rows,
        "normalized_rows": len(cleaned),
        "dropped_rows": source_rows - len(cleaned),
        "drop_reasons_before_overlap": {
            "missing_or_blank_order_id": int((~valid_text["order_id"]).sum()),
            "missing_or_blank_product_id": int((~valid_text["product_id"]).sum()),
            "missing_or_blank_customer_id": int((~valid_text["customer_id"]).sum()),
            "missing_or_blank_description": int((~valid_text["description"]).sum()),
            "missing_or_blank_country": int((~valid_text["country"]).sum()),
            "invalid_order_date": int((~valid_date).sum()),
            "invalid_unit_price": int((~valid_price).sum()),
            "invalid_quantity": int((~valid_quantity).sum()),
        },
        "output_rows": {
            "customers": len(customers),
            "orders": len(orders),
            "order_items": len(items),
        },
    }
    return {"customers": customers, "orders": orders, "order_items": items}, report


def prepare_uci_sample(
    max_rows: int = 50_000,
    *,
    raw_output_dir: Path | None = None,
    report_output_dir: Path | None = None,
) -> dict[str, Any]:
    if max_rows < 0:
        raise ValueError("max_rows must be zero or a positive integer")

    rows_to_read = None if max_rows == 0 else max_rows
    logger.info("Downloading UCI Online Retail data", extra={"max_rows": rows_to_read})
    frame = pd.read_csv(CSV_MIRROR_URL, nrows=rows_to_read)
    frames, report = _normalize_transactions(frame)

    output_dir = raw_output_dir or raw_dir()
    for name, output_frame in frames.items():
        write_csv(output_dir / f"{name}.csv", output_frame)

    report.update(
        {
            "sample_rows_requested": rows_to_read if rows_to_read is not None else "all",
            "source_url": UCI_SOURCE_PAGE,
            "csv_mirror_url": CSV_MIRROR_URL,
            "license": "CC BY 4.0",
            "citation": (
                "Chen, D. (2015). Online Retail [Dataset]. "
                "UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33"
            ),
        }
    )

    report_path = (report_output_dir or reports_dir()) / "dataset_preparation_report.json"
    write_json(report_path, report)
    logger.info(
        "Dataset preparation completed",
        extra={"normalized_rows": report["normalized_rows"], "report": str(report_path)},
    )
    return report


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Download and prepare a UCI Online Retail sample.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=50_000,
        help="Rows to read from the source CSV. Use 0 for the full dataset.",
    )
    args = parser.parse_args()
    if args.max_rows < 0:
        parser.error("--max-rows must be zero or a positive integer")
    report = prepare_uci_sample(max_rows=args.max_rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
