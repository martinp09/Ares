from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings
from app.models.ares_chief_of_staff import AresChiefOfStaffCheckInRequest, AresChiefOfStaffCheckInResponse
from app.services.ares_chief_of_staff_service import AresChiefOfStaffService
from app.services.nightly_lead_machine_service import nightly_lead_machine_service

router = APIRouter(prefix="/ares-chief-of-staff", tags=["ares-chief-of-staff"])


def _build_chief_of_staff_service() -> AresChiefOfStaffService:
    return AresChiefOfStaffService(lead_machine_service=nightly_lead_machine_service)


@router.post("/internal/check-in", response_model=AresChiefOfStaffCheckInResponse)
def run_chief_of_staff_check_in(request: AresChiefOfStaffCheckInRequest) -> AresChiefOfStaffCheckInResponse:
    """Run the Slack-native Chief of Staff employee check-in through the protected runtime API.

    The endpoint returns a Trigger-safe summary only. Local artifacts may contain
    exact operator details, but the API response intentionally omits names,
    addresses, contact details, raw lead IDs, and raw case numbers.
    """

    settings = get_settings()
    slack_allowed = bool(request.send_slack and settings.ares_chief_of_staff_scheduled_slack_enabled)
    result = _build_chief_of_staff_service().run_digest(
        business_id=request.business_id,
        environment=request.environment,
        limit=request.limit,
        artifact_root=request.artifact_root,
        send_slack=slack_allowed,
        idempotency_key=request.idempotency_key,
        write_artifacts=request.write_artifacts,
    )
    slack_notification: dict[str, Any] = result.slack_notification
    if request.send_slack and not slack_allowed:
        slack_notification = {"status": "blocked_by_chief_of_staff_slack_gate"}

    brief = result.brief
    return AresChiefOfStaffCheckInResponse(
        brief_id=brief.id,
        business_id=brief.business_id,
        environment=brief.environment,
        generated_at=brief.generated_at,
        input_lead_count=brief.input_lead_count,
        queue_counts=brief.queue_counts,
        manager_action_item_count=len(brief.manager_action_items),
        artifacts=result.artifacts,
        slack_notification=slack_notification,
        no_send=True,
        provider_sends_enabled=False,
        outreach_allowed=False,
        live_source_calls_attempted=False,
        provider_writes_attempted=False,
        trigger_safe_summary={
            "brief_id": brief.id,
            "employee_name": brief.employee_name,
            "manager_name": brief.manager_name,
            "reporting_channel": brief.reporting_channel,
            "input_lead_count": brief.input_lead_count,
            "queue_counts": brief.queue_counts,
            "manager_action_item_count": len(brief.manager_action_items),
            "artifact_keys": sorted(result.artifacts.keys()),
            "slack_requested": request.send_slack,
            "slack_allowed": slack_allowed,
            "safety": {
                "no_send": True,
                "provider_sends_enabled": False,
                "outreach_allowed": False,
                "live_source_calls_attempted": False,
                "provider_writes_attempted": False,
            },
            "redaction": "counts_only_no_lead_pii",
        },
    )
