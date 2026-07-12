from __future__ import annotations

from datetime import UTC, datetime, timedelta

try:
    from airflow.decorators import dag, task
except ModuleNotFoundError:  # Allows importing this file in environments without Airflow.
    dag = None
    task = None


if dag and task:

    @dag(
        dag_id="retail_data_quality_pipeline",
        description="Validate retail raw data, build DuckDB marts, and publish run reports.",
        start_date=datetime(2026, 7, 1, tzinfo=UTC),
        schedule="@daily",
        catchup=False,
        max_active_runs=1,
        default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
        tags=["portfolio", "data-quality", "duckdb"],
    )
    def retail_data_quality_pipeline():
        @task
        def validate_quality() -> dict:
            from retail_pipeline.pipeline import run_quality_stage

            return run_quality_stage()

        @task
        def build_analytics(_validation: dict) -> dict:
            from contextlib import suppress

            from retail_pipeline.pipeline import (
                PipelineFailure,
                publish_failure_summary,
                run_warehouse_stage,
            )

            try:
                return run_warehouse_stage()
            except Exception as error:
                with suppress(OSError):
                    publish_failure_summary(
                        PipelineFailure(
                            error=error,
                            stage="warehouse",
                            validation=_validation,
                        )
                    )
                raise

        @task
        def publish_results(validation: dict, warehouse: dict) -> dict:
            from contextlib import suppress
            from dataclasses import asdict

            from retail_pipeline.pipeline import (
                PipelineFailure,
                publish_failure_summary,
                publish_success_summary,
            )

            try:
                return asdict(publish_success_summary(validation, warehouse))
            except Exception as error:
                with suppress(OSError):
                    publish_failure_summary(
                        PipelineFailure(
                            error=error,
                            stage="publish_summary",
                            validation=validation,
                            warehouse=warehouse,
                        )
                    )
                raise

        validation = validate_quality()
        warehouse = build_analytics(validation)
        publish_results(validation, warehouse)

    retail_data_quality_pipeline()
