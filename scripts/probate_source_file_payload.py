from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.probate_source_file_service import ProbateSourceFileService  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a no-send probate autopilot nightly-source-pull payload from a local CSV/JSON/JSONL file.")
    parser.add_argument("--business-id", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--source-file", action="append", required=True, help="Local CSV/JSON/JSONL export path. Repeat for a Harris+Montgomery source packet.")
    parser.add_argument("--county", choices=["harris", "montgomery"], default=None)
    parser.add_argument("--expected-county", action="append", choices=["harris", "montgomery"], default=None)
    parser.add_argument(
        "--run-kind",
        choices=["morning_catchup", "midday", "end_of_day", "daily_reconciliation", "weekly_reconciliation", "manual"],
        default="manual",
    )
    parser.add_argument("--idempotency-key", default=None)
    parser.add_argument("--window-start", default=None)
    parser.add_argument("--window-end", default=None)
    parser.add_argument("--output", default=None, help="Optional output JSON path. Defaults to stdout.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    expected_counties = args.expected_county or ["harris", "montgomery"]
    payload = ProbateSourceFileService().build_nightly_payload_from_files(
        business_id=args.business_id,
        environment=args.environment,
        source_files=args.source_file,
        county=args.county,  # type: ignore[arg-type]
        expected_counties=expected_counties,  # type: ignore[arg-type]
        run_kind=args.run_kind,  # type: ignore[arg-type]
        idempotency_key=args.idempotency_key,
        window_start=args.window_start,
        window_end=args.window_end,
    )
    body = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(body + "\n", encoding="utf-8")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
