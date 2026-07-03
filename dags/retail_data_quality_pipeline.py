from __future__ import annotations

from datetime import datetime

try:
    from airflow.decorators import dag, task
except ModuleNotFoundError:  # Allows importing this file in environments without Airflow.
    dag = None
    task = None


if dag and task:

    @dag(
        dag_id="retail_data_quality_pipeline",
        description="Validate retail raw data, build DuckDB marts, and publish run reports.",
        start_date=datetime(2026, 7, 1),
        schedule="@daily",
        catchup=False,
        tags=["portfolio", "data-quality", "duckdb"],
    )
    def retail_data_quality_pipeline():
        @task
        def run_full_pipeline() -> dict:
            from dataclasses import asdict

            from retail_pipeline.pipeline import run_pipeline

            return asdict(run_pipeline())

        run_full_pipeline()

    retail_data_quality_pipeline()
