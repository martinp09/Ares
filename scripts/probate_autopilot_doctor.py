from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.source_runs import SourceRunsRepository  # noqa: E402
from app.services.nightly_lead_machine_service import NightlyLeadMachineService  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read the probate autopilot source-run ledger and emit a no-send operator health report.")
    parser.add_argument("--state-path", required=True, help="Path to LEAD_MACHINE_SOURCE_RUNS_STATE_PATH JSON state.")
    parser.add_argument("--business-id", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--fail-on-blocked", action="store_true", help="Exit 2 when latest SLA health is blocked.")
    parser.add_argument(
        "--max-brief-age-hours",
        type=float,
        default=None,
        help="Optional freshness SLA. Marks the report blocked when the latest brief is older than this many hours.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=args.state_path))
    brief = service.get_latest_morning_brief(business_id=args.business_id, environment=args.environment)
    if brief is None:
        print(
            json.dumps(
                {
                    "status": "no_data",
                    "business_id": args.business_id,
                    "environment": args.environment,
                    "message": "No probate autopilot morning brief is present in the source-run ledger.",
                    "outbound_allowed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    report = build_report(brief.sections, source_run_count=len(brief.source_runs), warning_count=len(brief.warnings))
    report.update(
        {
            "business_id": brief.business_id,
            "environment": brief.environment,
            "generated_at": brief.generated_at.isoformat(),
            "new_record_count": brief.new_record_count,
            "warning_count": len(brief.warnings),
            "source_run_count": len(brief.source_runs),
        }
    )
    apply_freshness_gate(report, generated_at=brief.generated_at, max_age_hours=args.max_brief_age_hours)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_on_blocked and report["status"] == "blocked":
        return 2
    return 0


def build_report(sections: dict[str, Any], *, source_run_count: int, warning_count: int) -> dict[str, Any]:
    sla_health = _dict(sections.get("sla_health"))
    source_quality = _dict(sections.get("source_quality"))
    enrichment_backlog = _dict(sections.get("enrichment_backlog"))
    no_send = _dict(sections.get("no_send_confirmation"))
    anomalies = _list(sections.get("source_anomalies"))
    operator_next_actions = _list(sections.get("operator_next_actions"))
    status = str(sla_health.get("status") or "unknown")
    return {
        "status": status,
        "outbound_allowed": bool(sla_health.get("outbound_allowed")) and bool(no_send.get("provider_sends_enabled")),
        "no_send_ok": no_send.get("no_send") is True and no_send.get("provider_sends_enabled") is False,
        "source_run_count": source_run_count,
        "warning_count": warning_count,
        "sla_health": sla_health,
        "source_quality": source_quality,
        "enrichment_backlog": enrichment_backlog,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:10],
        "operator_next_actions": operator_next_actions[:10],
    }


def apply_freshness_gate(
    report: dict[str, Any],
    *,
    generated_at: datetime,
    max_age_hours: float | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at_aware = generated_at if generated_at.tzinfo else generated_at.replace(tzinfo=timezone.utc)
    now_aware = now or datetime.now(timezone.utc)
    age_hours = max(0.0, (now_aware - generated_at_aware).total_seconds() / 3600)
    report["brief_age_hours"] = round(age_hours, 3)
    report["freshness_sla_hours"] = max_age_hours
    report["freshness_ok"] = max_age_hours is None or age_hours <= max_age_hours
    if max_age_hours is not None and age_hours > max_age_hours:
        report["status"] = "blocked"
        report["stale_brief"] = True
        report["stale_reason"] = f"Latest probate autopilot brief is {age_hours:.2f} hours old; SLA is {max_age_hours:.2f} hours."
        actions = _list(report.get("operator_next_actions"))
        report["operator_next_actions"] = [
            {
                "priority": "urgent",
                "action": "run_or_repair_probate_autopilot_source_pull",
                "reason": report["stale_reason"],
            },
            *actions,
        ][:10]
    else:
        report["stale_brief"] = False
    return report


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
