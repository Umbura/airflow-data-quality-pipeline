from __future__ import annotations

import logging
import os

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    level_name = os.getenv("RETAIL_LOG_LEVEL", "INFO").upper()
    level = logging.getLevelNamesMapping().get(level_name)
    if level is None:
        raise ValueError(f"Invalid RETAIL_LOG_LEVEL: {level_name}")
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
