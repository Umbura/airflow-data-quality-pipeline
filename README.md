# Airflow Data Quality Pipeline

Backend-first data engineering portfolio project using a real retail transactions dataset, an Airflow-ready DAG, DuckDB analytical marts, data quality gates, and a FastAPI results API.

The goal is to show a reproducible data pipeline rather than a dashboard-only project.

## What This Project Demonstrates

- Python packaging with `pyproject.toml` and `uv`.
- Raw data normalization from a real public dataset.
- Critical data quality checks before transformation.
- DuckDB warehouse and analytical marts.
- Airflow DAG definition using the same pipeline code.
- FastAPI read-only API for downstream consumption.
- Automated tests and linting.
- GitHub-ready documentation and partial generated results.

## Dataset

This project uses a normalized sample derived from the **UCI Online Retail** dataset.

- Source: [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online%2Bretail)
- Citation: `Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33`
- License: CC BY 4.0
- CSV mirror used for reproducible download: [Databricks Spark The Definitive Guide retail CSV](https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv)

See [DATA_LICENSE.md](DATA_LICENSE.md) for attribution details.

## Architecture

```text
UCI Online Retail CSV
    -> normalized raw tables
       - customers.csv
       - orders.csv
       - order_items.csv
    -> data quality gates
    -> DuckDB warehouse
    -> analytical marts
       - daily_revenue.csv
       - customer_revenue.csv
       - product_revenue.csv
       - country_revenue.csv
    -> JSON reports
    -> FastAPI read-only API
```

Airflow orchestration is defined in `dags/retail_data_quality_pipeline.py`. For this first portfolio version, the same logic can be run locally without starting Airflow.

## Tech Stack

- Python 3.11+
- uv
- Pandas
- DuckDB
- FastAPI
- Pytest
- Ruff
- Airflow DAG definition

## Quickstart

```bash
uv sync --extra dev
uv run retail-prepare-uci --max-rows 50000
uv run retail-pipeline
uv run pytest
uv run retail-api
```

Use `--max-rows 0` to process the full mirrored CSV.

## API Endpoints

After `uv run retail-api`, open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/metrics`
- `http://127.0.0.1:8000/quality`
- `http://127.0.0.1:8000/marts/daily-revenue`
- `http://127.0.0.1:8000/marts/customer-revenue`
- `http://127.0.0.1:8000/marts/product-revenue`
- `http://127.0.0.1:8000/marts/country-revenue`

## Current Partial Results

The included sample run uses the first 50,000 source rows from the Online Retail dataset.

Preparation summary:

- 50,000 source rows read.
- 32,114 normalized transaction rows.
- 17,886 rows dropped during cleaning, mostly missing customer IDs.
- 1,039 customers.
- 1,979 orders.
- 32,114 order items.

Pipeline summary:

- 14 data quality checks.
- 14 passed.
- 0 failed.
- 4 analytical marts generated.

Generated artifacts:

- `reports/dataset_preparation_report.json`
- `reports/quality_report.json`
- `reports/run_summary.json`
- `data/processed/marts/daily_revenue.csv`
- `data/processed/marts/customer_revenue.csv`
- `data/processed/marts/product_revenue.csv`
- `data/processed/marts/country_revenue.csv`

See [docs/results_snapshot.md](docs/results_snapshot.md) for a concise result snapshot.

## Data Quality Gates

The pipeline blocks critical issues before building marts:

- missing required columns;
- null required fields;
- duplicated customer or order keys;
- invalid order status;
- invalid customer segment;
- non-positive quantity or price;
- orphan orders without customer;
- orphan order items without order.

## Airflow

The DAG is in:

```text
dags/retail_data_quality_pipeline.py
```

To run with Airflow later, install the optional dependency and point Airflow to the `dags` folder:

```bash
uv sync --extra airflow
```

The full Airflow runtime is optional for this first version because it is heavier than the backend proof of value. The DAG calls `retail_pipeline.pipeline.run_pipeline()`, the same function used by local execution and tests.

## Validation

Latest local validation:

```text
uv run retail-prepare-uci --max-rows 50000 -> success
uv run retail-pipeline -> success
uv run pytest -> 3 passed
uv run ruff check . -> All checks passed
```

## Portfolio Talking Point

> Built an Airflow-ready retail data pipeline using a real public transaction dataset, with normalization, quality gates, DuckDB analytical marts, JSON run reports and a FastAPI API for downstream consumption. The pipeline validates raw inputs, blocks critical data issues and produces reproducible outputs with automated tests.

## License and Code Reuse

This repository uses original implementation code. External repositories and datasets were used only as references or public data sources with attribution; no third-party source code was copied into this project.
