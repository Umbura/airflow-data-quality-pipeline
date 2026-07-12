from __future__ import annotations

import json
from pathlib import Path
from typing import Final
from uuid import uuid4

import pandas as pd

RAW_FILES: Final = {
    "customers": "customers.csv",
    "orders": "orders.csv",
    "order_items": "order_items.csv",
}
RAW_DTYPES: Final = {
    "customers": {
        "customer_id": "string",
        "country": "string",
        "segment": "string",
        "first_invoice_date": "string",
    },
    "orders": {
        "order_id": "string",
        "customer_id": "string",
        "order_date": "string",
        "status": "string",
    },
    "order_items": {
        "order_id": "string",
        "product_id": "string",
        "description": "string",
        "quantity": "Int64",
        "unit_price": "Float64",
    },
}


class RawInputNotFoundError(FileNotFoundError):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"Missing raw input: {path}")


def load_raw_frames(raw_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name, filename in RAW_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            raise RawInputNotFoundError(path)
        frames[name] = pd.read_csv(path, dtype=RAW_DTYPES[name])
    return frames


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.{uuid4().hex}.tmp")


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _temporary_path(path)
    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = _temporary_path(path)
    try:
        frame.to_csv(temporary_path, index=False)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
