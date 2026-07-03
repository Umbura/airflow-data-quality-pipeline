from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from retail_pipeline.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the retail data pipeline locally.")
    parser.add_argument("--raw-dir", type=Path, default=None)
    parser.add_argument("--processed-dir", type=Path, default=None)
    parser.add_argument("--reports-dir", type=Path, default=None)
    args = parser.parse_args()

    summary = run_pipeline(
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        reports_dir=args.reports_dir,
    )
    print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
