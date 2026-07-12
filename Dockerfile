# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS runtime

ARG UV_VERSION=0.9.11

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --create-home appuser \
    && pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /app

COPY --chown=appuser:appuser pyproject.toml uv.lock README.md LICENSE DATA_LICENSE.md ./
COPY --chown=appuser:appuser src ./src

RUN uv sync --frozen --no-dev

COPY --chown=appuser:appuser data ./data
COPY --chown=appuser:appuser reports ./reports
COPY --chown=appuser:appuser dags ./dags

USER appuser

EXPOSE 8000

CMD ["retail-api"]


FROM runtime AS airflow

USER root

RUN uv sync --frozen --no-dev --extra airflow \
    && mkdir -p /app/airflow_home \
    && chown -R appuser:appuser /app/airflow_home

USER appuser

ENV AIRFLOW_HOME=/app/airflow_home

EXPOSE 8080

CMD ["airflow", "standalone"]
