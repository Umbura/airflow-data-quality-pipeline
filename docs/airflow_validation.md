# Airflow Validation

The Airflow runtime was validated in the project Docker image on 12 July 2026.

## Environment

| Item | Value |
| --- | --- |
| Airflow version | 2.11.2 |
| Python version | 3.12 |
| Executor for validation | Local DAG test process |
| Metadata database | SQLite in an isolated Docker volume |
| DAG | `retail_data_quality_pipeline` |
| Logical execution date | `2026-07-12` |

## Commands

```bash
docker compose --profile airflow build airflow
docker compose --profile airflow run --rm airflow airflow db migrate
docker compose --profile airflow run --rm airflow airflow dags list
docker compose --profile airflow run --rm airflow airflow tasks list retail_data_quality_pipeline --tree
docker compose --profile airflow run --rm airflow airflow dags test retail_data_quality_pipeline 2026-07-12
```

## Result

The DAG was imported without errors and the test run finished with status `success`.

| Task | Result |
| --- | --- |
| `validate_quality` | success |
| `build_analytics` | success |
| `publish_results` | success |

The validated run processed 1,039 customers, 1,979 orders, and 32,114 order items. All 25 quality checks passed and four analytical marts were published.
