"""Retail data pipeline portfolio project."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("airflow-data-quality-pipeline")
except PackageNotFoundError:  # Source tree imported before package installation.
    __version__ = "0.0.0"
