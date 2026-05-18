from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.ares_chief_of_staff_service import AresChiefOfStaffService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the read-only Ares Chief of Staff lead digest.")
    parser.add_argument("--business-id", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--artifact-root", default=None)
    parser.add_argument("--idempotency-key", default=None)
    parser.add_argument("--send-slack", action="store_true", help="Post the digest to the configured Chief of Staff Slack route.")
    parser.add_argument("--dry-run", action="store_true", help="Build and print the digest without artifact writes or Slack delivery.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from app.services.nightly_lead_machine_service import nightly_lead_machine_service

    service = AresChiefOfStaffService(lead_machine_service=nightly_lead_machine_service)
    result = service.run_digest(
        business_id=args.business_id,
        environment=args.environment,
        limit=args.limit,
        artifact_root=args.artifact_root,
        send_slack=bool(args.send_slack and not args.dry_run),
        idempotency_key=args.idempotency_key,
        write_artifacts=not args.dry_run,
    )
    payload = result.model_dump(mode="json")
    if args.dry_run and args.send_slack:
        payload["slack_notification"] = {"status": "dry_run_skipped"}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(service.render_markdown(result.brief))
        if result.artifacts:
            print("Artifacts:")
            for name, path in sorted(result.artifacts.items()):
                print(f"- {name}: {path}")
        print(f"Slack: {payload['slack_notification'].get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
