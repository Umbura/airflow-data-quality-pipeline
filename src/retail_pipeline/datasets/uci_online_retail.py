from __future__ import annotations

import argparse
import json
from typing import Any

import pandas as pd

from retail_pipeline.settings import raw_dir, reports_dir

UCI_SOURCE_PAGE = "https://archive.ics.uci.edu/dataset/352/online%2Bretail"
CSV_MIRROR_URL = (
    "https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/"
    "master/data/retail-data/all/online-retail-dataset.csv"
)


def _status_from_invoice(invoice_no: str, quantity: int) -> str:
    if invoice_no.upper().startswith("C") or quantity < 0:
        return "canceled"
    return "paid"


def _normalize_transactions(frame: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    source_rows = int(len(frame))
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

    normalized["customer_id"] = normalized["customer_id"].astype("string")
    normalized["order_id"] = normalized["order_id"].astype("string")
    normalized["product_id"] = normalized["product_id"].astype("string")
    normalized["description"] = normalized["description"].astype("string").str.strip()
    normalized["country"] = normalized["country"].astype("string").str.strip()
    normalized["quantity"] = pd.to_numeric(normalized["quantity"], errors="coerce")
    normalized["unit_price"] = pd.to_numeric(normalized["unit_price"], errors="coerce")
    normalized["order_date"] = pd.to_datetime(normalized["order_date"], errors="coerce")

    missing_customer = int(normalized["customer_id"].isna().sum())
    missing_description = int(normalized["description"].isna().sum())
    invalid_date = int(normalized["order_date"].isna().sum())
    invalid_price = int((normalized["unit_price"].isna() | (normalized["unit_price"] <= 0)).sum())
    invalid_quantity = int((normalized["quantity"].isna() | (normalized["quantity"] == 0)).sum())

    cleaned = normalized.dropna(
        subset=["order_id", "product_id", "customer_id", "description", "country", "order_date"]
    )
    cleaned = cleaned[(cleaned["unit_price"] > 0) & (cleaned["quantity"] != 0)].copy()
    cleaned["status"] = [
        _status_from_invoice(str(order_id), int(quantity))
        for order_id, quantity in zip(cleaned["order_id"], cleaned["quantity"], strict=True)
    ]
    cleaned["quantity"] = cleaned["quantity"].abs().astype(int)
    cleaned["unit_price"] = cleaned["unit_price"].round(2)
    cleaned["order_date"] = cleaned["order_date"].dt.date.astype(str)
    cleaned["customer_id"] = cleaned["customer_id"].str.replace(r"\.0$", "", regex=True)
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
        .agg(
            order_date=("order_date", "min"),
            status=("status", lambda statuses: "canceled" if "canceled" in set(statuses) else "paid"),
        )
        .sort_values("order_id")
    )
    items = cleaned[
        ["order_id", "product_id", "description", "quantity", "unit_price"]
    ].sort_values(["order_id", "product_id"])

    report = {
        "source": "UCI Online Retail",
        "source_rows": source_rows,
        "normalized_rows": int(len(cleaned)),
        "dropped_rows": int(source_rows - len(cleaned)),
        "drop_reasons_before_overlap": {
            "missing_customer_id": missing_customer,
            "missing_description": missing_description,
            "invalid_order_date": invalid_date,
            "non_positive_or_missing_unit_price": invalid_price,
            "zero_or_missing_quantity": invalid_quantity,
        },
        "output_rows": {
            "customers": int(len(customers)),
            "orders": int(len(orders)),
            "order_items": int(len(items)),
        },
    }
    return {"customers": customers, "orders": orders, "order_items": items}, report


def prepare_uci_sample(max_rows: int = 50_000) -> dict[str, Any]:
    rows_to_read = None if max_rows <= 0 else max_rows
    frame = pd.read_csv(CSV_MIRROR_URL, nrows=rows_to_read)
    frames, report = _normalize_transactions(frame)

    output_dir = raw_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, output_frame in frames.items():
        output_frame.to_csv(output_dir / f"{name}.csv", index=False)

    report["sample_rows_requested"] = rows_to_read or "all"
    report["source_url"] = UCI_SOURCE_PAGE
    report["csv_mirror_url"] = CSV_MIRROR_URL
    report["license"] = "CC BY 4.0"
    report["citation"] = (
        "Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. "
        "https://doi.org/10.24432/C5BW33"
    )

    report_path = reports_dir() / "dataset_preparation_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and prepare a UCI Online Retail sample.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=50_000,
        help="Rows to read from the source Excel file. Use 0 for the full dataset.",
    )
    args = parser.parse_args()
    report = prepare_uci_sample(max_rows=args.max_rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
