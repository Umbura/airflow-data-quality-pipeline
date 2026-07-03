from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException

from retail_pipeline.settings import processed_dir, reports_dir

app = FastAPI(
    title="Retail Data Quality Pipeline API",
    version="0.1.0",
    description="Read-only API exposing outputs from the Airflow-ready retail data pipeline.",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Output not found: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_mart(name: str) -> list[dict[str, Any]]:
    path = processed_dir() / "marts" / f"{name}.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Mart not found: {name}")
    return pd.read_csv(path).to_dict(orient="records")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return _read_json(reports_dir() / "run_summary.json")


@app.get("/quality")
def quality() -> dict[str, Any]:
    return _read_json(reports_dir() / "quality_report.json")


@app.get("/marts/daily-revenue")
def daily_revenue() -> list[dict[str, Any]]:
    return _read_mart("daily_revenue")


@app.get("/marts/customer-revenue")
def customer_revenue() -> list[dict[str, Any]]:
    return _read_mart("customer_revenue")


@app.get("/marts/product-revenue")
def product_revenue() -> list[dict[str, Any]]:
    return _read_mart("product_revenue")


@app.get("/marts/country-revenue")
def country_revenue() -> list[dict[str, Any]]:
    return _read_mart("country_revenue")


def run() -> None:
    uvicorn.run("retail_pipeline.api:app", host="127.0.0.1", port=8000, reload=False)
