from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def valid_frames() -> dict[str, pd.DataFrame]:
    return {
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
                }
            ]
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
