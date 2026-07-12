from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Final, Literal

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from retail_pipeline import __version__
from retail_pipeline.settings import api_host, api_port, processed_dir, reports_dir

MARTS: Final = {
    "daily-revenue": "daily_revenue",
    "customer-revenue": "customer_revenue",
    "product-revenue": "product_revenue",
    "country-revenue": "country_revenue",
}

JsonScalar = str | int | float | bool | None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    pipeline_status: str | None
    artifacts_ready: bool
    run_id: str | None


class MartListResponse(BaseModel):
    marts: list[str]


class MartPage(BaseModel):
    mart: str
    total: int
    limit: int
    offset: int
    items: list[dict[str, JsonScalar]]


app = FastAPI(
    title="Retail Data Quality Pipeline API",
    version=__version__,
    description="Read-only API exposing outputs from the Airflow-ready retail data pipeline.",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Output not found: {path.name}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Output is not valid JSON: {path.name}",
        ) from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail=f"Output is not a JSON object: {path.name}")
    return payload


def _read_mart(public_name: str, file_stem: str, limit: int, offset: int) -> MartPage:
    path = processed_dir() / "marts" / f"{file_stem}.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Mart not found: {public_name}")
    frame = pd.read_csv(path)
    page = frame.iloc[offset : offset + limit].astype(object)
    page = page.where(pd.notna(page), None)
    return MartPage(
        mart=public_name,
        total=len(frame),
        limit=limit,
        offset=offset,
        items=page.to_dict(orient="records"),
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    summary_path = reports_dir() / "run_summary.json"
    expected_marts = [processed_dir() / "marts" / f"{name}.csv" for name in MARTS.values()]
    artifacts_ready = summary_path.exists() and all(path.exists() for path in expected_marts)
    pipeline_status = None
    run_id = None
    if summary_path.exists():
        summary = _read_json(summary_path)
        pipeline_status = summary.get("status")
        run_id = summary.get("run_id")
    return HealthResponse(
        status="ok" if artifacts_ready and pipeline_status == "success" else "degraded",
        pipeline_status=pipeline_status,
        artifacts_ready=artifacts_ready,
        run_id=run_id,
    )


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return _read_json(reports_dir() / "run_summary.json")


@app.get("/quality")
def quality() -> dict[str, Any]:
    return _read_json(reports_dir() / "quality_report.json")


@app.get("/marts", response_model=MartListResponse)
def list_marts() -> MartListResponse:
    return MartListResponse(marts=list(MARTS))


@app.get("/marts/{mart_name}", response_model=MartPage)
def read_mart(
    mart_name: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> MartPage:
    internal_name = MARTS.get(mart_name)
    if internal_name is None:
        raise HTTPException(status_code=404, detail=f"Unknown mart: {mart_name}")
    return _read_mart(mart_name, internal_name, limit, offset)


def run() -> None:
    uvicorn.run(
        "retail_pipeline.api:app",
        host=api_host(),
        port=api_port(),
        reload=False,
    )
