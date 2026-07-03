# Airflow Data Quality Pipeline

Backend data pipeline for retail transaction ingestion, data quality validation, analytical mart generation, and read-only result serving.

The project normalizes a real public retail dataset, validates critical constraints before transformation, builds DuckDB analytical outputs, and exposes pipeline results through a FastAPI service. Airflow orchestration is represented by a DAG that calls the same pipeline code used by local execution and tests.

## Overview

The system separates dataset preparation, raw table loading, data quality validation, warehouse transformation, result reporting, and API access. The pipeline can be executed locally without starting Airflow, while the DAG remains available for orchestration in an Airflow runtime.

The default execution path does not require paid services, external databases, or cloud infrastructure.

## Implemented Scope

- UCI Online Retail sample preparation from a reproducible CSV mirror.
- Normalized raw tables for customers, orders, and order items.
- Critical data quality gates before warehouse generation.
- DuckDB warehouse build.
- Analytical marts for daily revenue, customer revenue, product revenue, and country revenue.
- JSON reports for dataset preparation, quality validation, and pipeline run summary.
- FastAPI service exposing health, metrics, quality, and mart endpoints.
- Airflow DAG definition using the same pipeline function.
- Unit tests for quality checks and pipeline execution.
- Ruff lint configuration.

## Execution Flow

```text
UCI Online Retail CSV
  -> retail-prepare-uci
      -> normalized raw CSV tables
          -> customers.csv
          -> orders.csv
          -> order_items.csv
      -> dataset preparation report
  -> retail-pipeline
      -> raw frame loading
      -> quality gates
      -> DuckDB warehouse
      -> analytical marts
      -> quality and run reports
  -> retail-api
      -> read-only access to generated outputs
```

## Dataset

The sample data is derived from the UCI Machine Learning Repository Online Retail dataset.

- Source dataset: https://archive.ics.uci.edu/dataset/352/online%2Bretail
- Citation: `Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33`
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- CSV mirror used for reproducible preparation: https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv

Attribution details are documented in `DATA_LICENSE.md`.

## Data Quality Model

The pipeline blocks warehouse generation when critical quality checks fail.

Implemented checks:

- required raw columns;
- non-null required fields;
- unique customer and order keys;
- accepted order status values;
- accepted customer segment values;
- positive quantity and unit price;
- order-to-customer referential integrity;
- order-item-to-order referential integrity.

The quality gate is intentionally strict. Failed critical checks raise an exception before marts are generated.

## API

Start the local API:

```bash
uv sync --extra dev
uv run retail-pipeline
uv run retail-api
```

Open:

```text
http://127.0.0.1:8000/docs
```

Endpoints:

- `GET /health`
- `GET /metrics`
- `GET /quality`
- `GET /marts/daily-revenue`
- `GET /marts/customer-revenue`
- `GET /marts/product-revenue`
- `GET /marts/country-revenue`

## Airflow

The DAG is defined in:

```text
dags/retail_data_quality_pipeline.py
```

The DAG calls `retail_pipeline.pipeline.run_pipeline()`, the same function used by local execution and tests.

Install Airflow only when an Airflow runtime is required:

```bash
uv sync --extra airflow
```

The validated local path does not require Airflow installation.

## Local Commands

Install dependencies:

```bash
uv sync --extra dev
```

Prepare a 50,000-row sample:

```bash
uv run retail-prepare-uci --max-rows 50000
```

Process the full mirrored CSV:

```bash
uv run retail-prepare-uci --max-rows 0
```

Run the pipeline:

```bash
uv run retail-pipeline
```

Run tests and lint:

```bash
uv run pytest -q
uv run ruff check .
```

Start the API:

```bash
uv run retail-api
```

## Current Results

Latest generated sample:

| Metric | Result |
| --- | ---: |
| Source rows read | 50,000 |
| Normalized transaction rows | 32,114 |
| Dropped rows during preparation | 17,886 |
| Customers | 1,039 |
| Orders | 1,979 |
| Order items | 32,114 |
| Data quality checks | 14 |
| Failed quality checks | 0 |
| Analytical marts | 4 |

Generated artifacts:

- `reports/dataset_preparation_report.json`
- `reports/quality_report.json`
- `reports/run_summary.json`
- `data/processed/marts/daily_revenue.csv`
- `data/processed/marts/customer_revenue.csv`
- `data/processed/marts/product_revenue.csv`
- `data/processed/marts/country_revenue.csv`

A concise output summary is available in `docs/results_snapshot.md`.

## Validation Results

Latest validation:

| Check | Result |
| --- | ---: |
| Dataset preparation | passed |
| Pipeline execution | passed |
| Unit tests | 3 passed |
| Lint | passed |

The validation path uses local execution and does not require Airflow, cloud credentials, or paid APIs.

## Repository Layout

```text
dags/                   Airflow DAG definition
data/external/          ignored external downloads
data/raw/               normalized raw CSV tables
data/processed/marts/   generated analytical marts
docs/                   result snapshots and supporting notes
reports/                generated JSON reports
src/retail_pipeline/    pipeline, quality checks, warehouse, API, dataset preparation
tests/                  unit tests and pipeline tests
```

## Roadmap

### Phase 1: Backend Pipeline MVP

Status: implemented.

- Dataset preparation command.
- Raw table normalization.
- Data quality gate.
- DuckDB warehouse generation.
- Analytical marts.
- JSON reports.
- FastAPI read-only API.
- Tests and linting.

### Phase 2: Airflow Runtime Validation

- Run the DAG in a local Airflow instance.
- Document DAG execution output.
- Add screenshots or logs from the Airflow UI.

### Phase 3: Data Engineering Extensions

- Add dbt models for transformation lineage.
- Add Great Expectations or equivalent expectation suites.
- Add CI validation for tests and lint.
- Add Docker Compose for reproducible local services.

### Phase 4: Production Hardening

- Replace local DuckDB artifact with a managed warehouse target.
- Add incremental loading.
- Add API authentication for exposed environments.
- Add structured pipeline observability.

## References

- UCI Online Retail dataset: https://archive.ics.uci.edu/dataset/352/online%2Bretail
- Dataset DOI: https://doi.org/10.24432/C5BW33
- Databricks CSV mirror: https://raw.githubusercontent.com/databricks/Spark-The-Definitive-Guide/master/data/retail-data/all/online-retail-dataset.csv
- Apache Airflow: https://airflow.apache.org/
- DuckDB: https://duckdb.org/
- FastAPI: https://fastapi.tiangolo.com/

License and dataset attribution are documented in `LICENSE` and `DATA_LICENSE.md`.
