from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from retail_pipeline.settings import api_host, api_port, processed_dir, reports_dir

MARTS = {
    "daily-revenue": "daily_revenue",
    "customer-revenue": "customer_revenue",
    "product-revenue": "product_revenue",
    "country-revenue": "country_revenue",
}


class MartPage(BaseModel):
    mart: str
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]

app = FastAPI(
    title="Retail Data Quality Pipeline API",
    version="1.0.0",
    description="Read-only API exposing outputs from the Airflow-ready retail data pipeline.",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Output not found: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_mart(name: str, limit: int, offset: int) -> MartPage:
    path = processed_dir() / "marts" / f"{name}.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Mart not found: {name}")
    frame = pd.read_csv(path)
    page = frame.iloc[offset : offset + limit].astype(object)
    page = page.where(pd.notna(page), None)
    return MartPage(
        mart=name,
        total=int(len(frame)),
        limit=limit,
        offset=offset,
        items=page.to_dict(orient="records"),
    )


@app.get("/health")
def health() -> dict[str, Any]:
    summary_path = reports_dir() / "run_summary.json"
    expected_marts = [processed_dir() / "marts" / f"{name}.csv" for name in MARTS.values()]
    artifacts_ready = summary_path.exists() and all(path.exists() for path in expected_marts)
    pipeline_status = None
    run_id = None
    if summary_path.exists():
        summary = _read_json(summary_path)
        pipeline_status = summary.get("status")
        run_id = summary.get("run_id")
    return {
        "status": "ok" if artifacts_ready and pipeline_status == "success" else "degraded",
        "pipeline_status": pipeline_status,
        "artifacts_ready": artifacts_ready,
        "run_id": run_id,
    }


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return _read_json(reports_dir() / "run_summary.json")


@app.get("/quality")
def quality() -> dict[str, Any]:
    return _read_json(reports_dir() / "quality_report.json")


@app.get("/marts")
def list_marts() -> dict[str, list[str]]:
    return {"marts": list(MARTS)}


@app.get("/marts/{mart_name}", response_model=MartPage)
def read_mart(
    mart_name: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> MartPage:
    internal_name = MARTS.get(mart_name)
    if internal_name is None:
        raise HTTPException(status_code=404, detail=f"Unknown mart: {mart_name}")
    return _read_mart(internal_name, limit, offset)


def run() -> None:
    uvicorn.run(
        "retail_pipeline.api:app",
        host=api_host(),
        port=api_port(),
        reload=False,
    )
