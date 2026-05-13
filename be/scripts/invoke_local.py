from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Lambda handler locally (full fetch pipeline).")
    parser.add_argument(
        "--batch-pr",
        action="store_true",
        help="Open one draft PR per run for every successfully generated article (sets GITHUB_BATCH_PR).",
    )
    args = parser.parse_args()

    load_dotenv()
    if args.batch_pr:
        os.environ["GITHUB_BATCH_PR"] = "1"
    from medical_news.handlers.orchestrator import handler

    summary = handler({}, None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
