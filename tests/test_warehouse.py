from __future__ import annotations

from pathlib import Path

import pandas as pd

from retail_pipeline.warehouse import build_warehouse


def test_warehouse_separates_paid_and_canceled_orders(tmp_path: Path) -> None:
    frames = {
        "customers": pd.DataFrame(
            [
                {
                    "customer_id": "C001",
                    "country": "Brazil",
                    "segment": "export",
                    "first_invoice_date": "2026-01-01",
                }
            ]
        ),
        "orders": pd.DataFrame(
            [
                {
                    "order_id": "O1",
                    "customer_id": "C001",
                    "order_date": "2026-01-01",
                    "status": "paid",
                },
                {
                    "order_id": "O2",
                    "customer_id": "C001",
                    "order_date": "2026-01-01",
                    "status": "canceled",
                },
            ]
        ),
        "order_items": pd.DataFrame(
            [
                {
                    "order_id": "O1",
                    "product_id": "P1",
                    "description": "Course",
                    "quantity": 2,
                    "unit_price": 10.0,
                },
                {
                    "order_id": "O2",
                    "product_id": "P1",
                    "description": "Course",
                    "quantity": 1,
                    "unit_price": 10.0,
                },
            ]
        ),
    }

    marts = build_warehouse(frames, tmp_path / "warehouse.duckdb")
    daily = marts["daily_revenue"].iloc[0]
    product = marts["product_revenue"].iloc[0]

    assert daily["total_orders"] == 2
    assert daily["paid_orders"] == 1
    assert daily["canceled_orders"] == 1
    assert daily["gross_revenue"] == 20.0
    assert product["units_sold"] == 2
    assert product["units_canceled"] == 1
