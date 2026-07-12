from __future__ import annotations

from pathlib import Path

import pandas as pd

from retail_pipeline.io import load_raw_frames
from retail_pipeline.quality import validate_raw_frames


def test_load_raw_frames_preserves_identifier_types(tmp_path: Path) -> None:
    pd.DataFrame(
        [
            {
                "customer_id": "12345",
                "country": "United Kingdom",
                "segment": "domestic",
                "first_invoice_date": "2010-12-01",
            }
        ]
    ).to_csv(tmp_path / "customers.csv", index=False)
    pd.DataFrame(
        [
            {
                "order_id": "10001",
                "customer_id": "12345",
                "order_date": "2010-12-01",
                "status": "paid",
            }
        ]
    ).to_csv(tmp_path / "orders.csv", index=False)
    pd.DataFrame(
        [
            {
                "order_id": "10001",
                "product_id": "P1",
                "description": "Product",
                "quantity": 1,
                "unit_price": 0.001,
            }
        ]
    ).to_csv(tmp_path / "order_items.csv", index=False)

    frames = load_raw_frames(tmp_path)
    checks = validate_raw_frames(frames)

    assert frames["orders"].iloc[0]["order_id"] == "10001"
    assert frames["order_items"].iloc[0]["order_id"] == "10001"
    assert str(frames["orders"]["order_id"].dtype) == "string"
    assert str(frames["order_items"]["order_id"].dtype) == "string"
    assert all(check.passed for check in checks)
