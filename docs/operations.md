# Operations

## Local Runtime

Requirements:

- Python 3.12;
- uv;
- network access only when the source dataset is prepared again.

Install and validate:

```bash
uv sync --frozen --extra dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q --cov --cov-report=term-missing
uv run retail-pipeline
```

Start the API:

```bash
uv run retail-api
```

API documentation is available at `http://127.0.0.1:8000/docs`.

Command-line logging defaults to `INFO`. Set `RETAIL_LOG_LEVEL` to `DEBUG`, `WARNING`, `ERROR`, or `CRITICAL` when another level is required.

## Docker Runtime

Build the image, execute the pipeline, and start the API:

```bash
docker compose up --build api
```

The `pipeline` service must complete successfully before the API starts. Generated files are persisted in the local `data/processed` and `reports` directories.

If port 8000 is already in use, select another host port without changing the container port:

```powershell
$env:RETAIL_API_HOST_PORT = "8001"
docker compose up --build api
```

Run only the pipeline:

```bash
docker compose run --rm pipeline
```

## Airflow Runtime

Start the optional Airflow profile:

```bash
docker compose --profile airflow up --build airflow
```

The Airflow interface is available at `http://127.0.0.1:8080`. The `airflow standalone` command prints the local administrator credentials during startup.

The DAG contains three tasks:

1. `validate_quality`
2. `build_analytics`
3. `publish_results`

Validate the DAG without starting the scheduler and web server:

```bash
docker compose --profile airflow run --rm airflow airflow db migrate
docker compose --profile airflow run --rm airflow airflow dags test retail_data_quality_pipeline 2026-07-12
```

## Generated Artifacts

| Path | Purpose |
| --- | --- |
| `reports/dataset_preparation_report.json` | Source normalization metrics and attribution. |
| `reports/quality_report.json` | Individual quality checks and critical failures. |
| `reports/run_summary.json` | Run status, duration, stage, outputs, and error details. |
| `data/processed/warehouse.duckdb` | Local analytical warehouse. |
| `data/processed/marts/*.csv` | Portable analytical marts. |

## Failure Recovery

For a quality failure, inspect `quality_report.json` and correct the raw input before rerunning. The run summary identifies the failed stage and exception type.

For missing source files, prepare the sample again:

```bash
uv run retail-prepare-uci --max-rows 50000
```

For a clean Airflow metadata database, stop the services and remove the Compose-managed volumes:

```bash
docker compose --profile airflow down --volumes
```

This operation removes Airflow metadata and local credentials. It does not remove the project data directories.
