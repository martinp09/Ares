from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.db.leads import LeadsRepository
from app.models.ares_chief_of_staff import (
    AresChiefOfStaffBrief,
    AresChiefOfStaffBucket,
    AresChiefOfStaffLeadCard,
    AresChiefOfStaffRunResult,
)
from app.models.commands import generate_stable_id, utc_now
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.slack_notifications import SlackNotificationRoute
from app.services.slack_notification_service import slack_notification_service


class SlackNotifier(Protocol):
    def notify(self, **kwargs: Any) -> Any: ...


class LeadMachineReader(Protocol):
    def get_latest_morning_brief(self, *, business_id: str, environment: str) -> Any | None: ...

    def get_probate_autopilot_health(self, *, business_id: str, environment: str, max_brief_age_hours: float | None = None) -> Any: ...

    def summarize_morning_brief(self, brief: Any | None) -> Any | None: ...


QUEUE_ORDER = (
    AresChiefOfStaffBucket.HOT,
    AresChiefOfStaffBucket.CONTACT_READY,
    AresChiefOfStaffBucket.NEEDS_RESEARCH,
    AresChiefOfStaffBucket.NEEDS_SKIPTRACE,
    AresChiefOfStaffBucket.BLOCKED,
    AresChiefOfStaffBucket.WATCHLIST,
    AresChiefOfStaffBucket.PASS,
)


class AresChiefOfStaffService:
    """Read-only operator brief for Martin's real-estate lead desk.

    This service can write local artifacts and send internal Slack operator
    notifications, but it never sends seller outreach, spends skiptrace credits,
    enrolls campaigns, mutates CRM/provider records, or calls live county/source
    systems.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        leads_repository: LeadsRepository | None = None,
        slack_notifier: SlackNotifier | None = None,
        lead_machine_service: LeadMachineReader | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.leads_repository = leads_repository or LeadsRepository(settings=self.settings)
        self.slack_notifier = slack_notifier or slack_notification_service
        self.lead_machine_service = lead_machine_service

    def run_digest(
        self,
        *,
        business_id: str,
        environment: str,
        limit: int = 5,
        artifact_root: str | Path | None = None,
        send_slack: bool = False,
        idempotency_key: str | None = None,
        write_artifacts: bool = True,
    ) -> AresChiefOfStaffRunResult:
        brief = self.build_brief(
            business_id=business_id,
            environment=environment,
            limit=limit,
            idempotency_key=idempotency_key,
        )
        artifacts: dict[str, str] = {}
        resolved_artifact_root = self._artifact_root(artifact_root) if write_artifacts else None
        if resolved_artifact_root is not None:
            artifacts = self.write_artifacts(brief, resolved_artifact_root)
            brief = brief.model_copy(update={"artifact_path": str(Path(artifacts["brief_json"]).parent)})

        slack_notification: dict[str, Any] = {"status": "not_requested"}
        if send_slack:
            slack_notification = self.send_slack_digest(brief, idempotency_key=idempotency_key)

        return AresChiefOfStaffRunResult(
            brief=brief,
            artifacts=artifacts,
            slack_notification=slack_notification,
        )

    def build_brief(
        self,
        *,
        business_id: str,
        environment: str,
        limit: int = 5,
        idempotency_key: str | None = None,
    ) -> AresChiefOfStaffBrief:
        leads = self.leads_repository.list(business_id=business_id, environment=environment)
        cards = [self._lead_card(lead) for lead in leads]
        cards.sort(key=lambda card: (card.score, card.lead_id), reverse=True)

        queue_map: dict[str, list[AresChiefOfStaffLeadCard]] = {bucket.value: [] for bucket in QUEUE_ORDER}
        for card in cards:
            for tag in card.queue_tags:
                queue_map[tag.value].append(card)
        limited_queues = {bucket.value: queue_map[bucket.value][:limit] for bucket in QUEUE_ORDER}
        queue_counts = {bucket.value: len(queue_map[bucket.value]) for bucket in QUEUE_ORDER}
        generated_at = utc_now().isoformat()
        operational_context = self._operational_context(business_id=business_id, environment=environment)
        recommended_focus = self._recommended_focus(limited_queues)
        priorities = self._employee_priorities(limited_queues, queue_counts=queue_counts, operational_context=operational_context)
        blockers = self._employee_blockers(queue_counts=queue_counts, operational_context=operational_context)
        approval_requests = self._approval_requests(queue_counts)
        worklog = self._worklog(
            business_id=business_id,
            environment=environment,
            lead_count=len(leads),
            queue_counts=queue_counts,
            operational_context=operational_context,
        )
        brief_id = generate_stable_id(
            "cos_brief",
            business_id,
            environment,
            idempotency_key or generated_at[:10],
        )
        return AresChiefOfStaffBrief(
            id=brief_id,
            business_id=business_id,
            environment=environment,
            generated_at=generated_at,
            input_lead_count=len(leads),
            source_summary=self._source_summary(leads),
            operational_context=operational_context,
            queue_counts=queue_counts,
            queues=limited_queues,
            worklog=worklog,
            priorities=priorities,
            blockers=blockers,
            approval_requests=approval_requests,
            recommended_focus=recommended_focus,
            safety_boundaries=[
                "No seller outreach sent by Chief of Staff v1.",
                "No paid skiptrace credits spent by Chief of Staff v1.",
                "No Instantly, HubSpot, SMS, email, Vapi, buyer-blast, or provider mutation performed.",
                "Hot lead and contact-ready are separate; authority/title blockers prevent contact-ready status.",
            ],
        )

    def write_artifacts(self, brief: AresChiefOfStaffBrief, artifact_root: str | Path) -> dict[str, str]:
        root = Path(artifact_root)
        generated_date = _date_from_iso(brief.generated_at)
        output_dir = root / "chief-of-staff" / generated_date
        output_dir.mkdir(parents=True, exist_ok=True)

        brief_json = output_dir / "brief.json"
        brief_md = output_dir / "brief.md"
        hot_csv = output_dir / "hot_leads.csv"
        contact_ready_csv = output_dir / "contact_ready.csv"
        needs_research_csv = output_dir / "needs_research.csv"
        skiptrace_csv = output_dir / "skiptrace_candidates.csv"
        blocked_csv = output_dir / "blocked.csv"

        brief_json.write_text(json.dumps(brief.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
        brief_md.write_text(self.render_markdown(brief), encoding="utf-8")
        self._write_queue_csv(hot_csv, brief.queues[AresChiefOfStaffBucket.HOT.value])
        self._write_queue_csv(contact_ready_csv, brief.queues[AresChiefOfStaffBucket.CONTACT_READY.value])
        self._write_queue_csv(needs_research_csv, brief.queues[AresChiefOfStaffBucket.NEEDS_RESEARCH.value])
        self._write_queue_csv(skiptrace_csv, brief.queues[AresChiefOfStaffBucket.NEEDS_SKIPTRACE.value])
        self._write_queue_csv(blocked_csv, brief.queues[AresChiefOfStaffBucket.BLOCKED.value])

        return {
            "brief_json": str(brief_json),
            "brief_markdown": str(brief_md),
            "hot_csv": str(hot_csv),
            "contact_ready_csv": str(contact_ready_csv),
            "needs_research_csv": str(needs_research_csv),
            "skiptrace_candidates_csv": str(skiptrace_csv),
            "blocked_csv": str(blocked_csv),
        }

    def send_slack_digest(self, brief: AresChiefOfStaffBrief, *, idempotency_key: str | None = None) -> dict[str, Any]:
        text, blocks = self.render_slack(brief)
        dedupe_key = idempotency_key or f"chief-of-staff:{brief.business_id}:{brief.environment}:{brief.generated_at[:10]}"
        attempt = self.slack_notifier.notify(
            route=SlackNotificationRoute.CHIEF_OF_STAFF_DIGEST,
            business_id=brief.business_id,
            environment=brief.environment,
            dedupe_key=dedupe_key,
            text=text,
            blocks=blocks,
            payload=self._slack_payload(brief),
        )
        if hasattr(attempt, "model_dump"):
            return attempt.model_dump(mode="json")
        return dict(attempt)

    def render_markdown(self, brief: AresChiefOfStaffBrief) -> str:
        lines = [
            "# Ares Chief of Staff Brief",
            "",
            f"- Employee: **{brief.employee_name}** ({brief.employee_role})",
            f"- Reports to: **{brief.manager_name}** via `{brief.reporting_channel}`",
            f"- Status: `{brief.shift_status}`",
            f"- Business: `{brief.business_id}`",
            f"- Environment: `{brief.environment}`",
            f"- Generated: `{brief.generated_at}`",
            f"- Leads reviewed: **{brief.input_lead_count}**",
            "",
            "## Worklog",
        ]
        lines.extend([f"- {item}" for item in brief.worklog] or ["- No worklog entries generated."])
        lines.extend(["", "## Priorities"])
        lines.extend([f"- {item}" for item in brief.priorities] or ["- No priority actions from current data."])
        lines.extend(["", "## Blockers"])
        lines.extend([f"- {item}" for item in brief.blockers] or ["- No active blockers from current data."])
        lines.extend(["", "## Approvals Needed"])
        lines.extend([f"- {item}" for item in brief.approval_requests] or ["- No new approval request from this report."])
        lines.extend(["", "## Operational Status"])
        lines.extend([f"- {item}" for item in self._operational_status_lines(brief.operational_context)])
        lines.extend(["", "## Queue Counts"])
        for bucket in QUEUE_ORDER:
            lines.append(f"- {bucket.value}: {brief.queue_counts.get(bucket.value, 0)}")
        lines.extend(["", "## Recommended Focus"])
        lines.extend([f"- {item}" for item in brief.recommended_focus] or ["- No priority actions from current data."])
        for bucket in QUEUE_ORDER[:5]:
            cards = brief.queues.get(bucket.value, [])
            if not cards:
                continue
            lines.extend(["", f"## {bucket.value.replace('_', ' ').title()}"])
            for card in cards:
                lines.append(f"- **{card.display_name}** — score {card.score:.0f} — {card.primary_lane}")
                if card.property_address:
                    lines.append(f"  - Property: {card.property_address}")
                lines.append(f"  - Next action: {card.next_action}")
                if card.reasons:
                    lines.append(f"  - Why: {'; '.join(card.reasons[:3])}")
                if card.blockers:
                    lines.append(f"  - Blockers: {'; '.join(card.blockers[:3])}")
        lines.extend(["", "## Safety Boundaries"])
        lines.extend([f"- {item}" for item in brief.safety_boundaries])
        lines.append("")
        return "\n".join(lines)

    def render_slack(self, brief: AresChiefOfStaffBrief) -> tuple[str, list[dict[str, Any]]]:
        hot = brief.queue_counts.get(AresChiefOfStaffBucket.HOT.value, 0)
        contact_ready = brief.queue_counts.get(AresChiefOfStaffBucket.CONTACT_READY.value, 0)
        research = brief.queue_counts.get(AresChiefOfStaffBucket.NEEDS_RESEARCH.value, 0)
        skiptrace = brief.queue_counts.get(AresChiefOfStaffBucket.NEEDS_SKIPTRACE.value, 0)
        blocked = brief.queue_counts.get(AresChiefOfStaffBucket.BLOCKED.value, 0)
        status_line = self._operational_status_line(brief.operational_context)
        text = (
            f"Ares Chief of Staff checking in for {brief.manager_name}: reviewed {brief.input_lead_count} leads; "
            f"hot {hot}, contact-ready {contact_ready}, research {research}, "
            f"skiptrace {skiptrace}, blocked {blocked}. {status_line}. No outreach sent."
        )
        top_lines = self._slack_queue_lines(brief.queues.get(AresChiefOfStaffBucket.CONTACT_READY.value, []), "Top contact-ready queue")
        if not top_lines:
            top_lines = self._slack_queue_lines(brief.queues.get(AresChiefOfStaffBucket.HOT.value, []), "Top hot queue")
        worklog = self._slack_bullets(brief.worklog[:4], fallback="I did not find enough data to create a full worklog yet.")
        priorities = self._slack_bullets(brief.priorities[:4], fallback="No priority actions from current data.")
        blockers = self._slack_bullets(brief.blockers[:4], fallback="No active blockers from current data.")
        approvals = self._slack_bullets(brief.approval_requests[:4], fallback="No new approval request from this report.")
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{brief.employee_name} — Lead Desk Check-in*\n"
                        f"Morning {brief.manager_name} — I reviewed *{brief.input_lead_count}* leads for "
                        f"`{brief.business_id}/{brief.environment}`. {status_line}."
                    ),
                },
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*What I did*\n{worklog}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*What I recommend next*\n{priorities}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Blocked / Needs research*\n{blockers}"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Need your approval*\n{approvals}"}},
        ]
        if top_lines:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(top_lines[:6])}})
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Safety: no seller outreach, paid skiptrace, CRM/provider writes, SMS/email/Vapi sends, buyer blasts, or Telegram delivery were performed.",
                    }
                ],
            }
        )
        return text, blocks

    def _lead_card(self, lead: LeadRecord) -> AresChiefOfStaffLeadCard:
        score = self._score(lead)
        has_phone = bool(_clean(lead.phone))
        has_email = bool(_clean(lead.email))
        has_mailing_address = bool(_clean(lead.mailing_address))
        has_direct_contact = has_phone or has_email
        probate_signal = lead.source == LeadSource.PROBATE_INTAKE or bool(_clean(lead.probate_case_number))
        tax_signal = self._raw_bool(lead, "tax_delinquent", "delinquent_taxes", "taxes_delinquent")
        estate_signal = self._raw_bool(lead, "estate_of", "estate_signal") or "estate" in self._display_name(lead).lower()
        title_review = self._title_review_needed(lead)
        authority_unclear = self._authority_unclear(lead, probate_signal=probate_signal, estate_signal=estate_signal)
        suppressed = lead.lifecycle_status in {LeadLifecycleStatus.SUPPRESSED, LeadLifecycleStatus.CLOSED}
        hot_signal = score >= 70 or self._raw_text(lead, "lead_temperature", "temperature").lower() == "hot"

        reasons = self._reasons(
            score=score,
            probate_signal=probate_signal,
            tax_signal=tax_signal,
            estate_signal=estate_signal,
            title_review=title_review,
            has_direct_contact=has_direct_contact,
        )
        blockers = self._blockers(
            lead,
            suppressed=suppressed,
            has_direct_contact=has_direct_contact,
            authority_unclear=authority_unclear,
            title_review=title_review,
        )
        contact_ready = has_direct_contact and not suppressed and not authority_unclear and not title_review
        needs_research = not suppressed and (authority_unclear or title_review or self._case_detail_incomplete(lead))
        needs_skiptrace = not suppressed and not has_direct_contact and bool(_clean(lead.property_address) or self._display_name(lead) != (lead.id or "lead"))

        tags: list[AresChiefOfStaffBucket] = []
        if hot_signal and not suppressed:
            tags.append(AresChiefOfStaffBucket.HOT)
        if contact_ready:
            tags.append(AresChiefOfStaffBucket.CONTACT_READY)
        if needs_research:
            tags.append(AresChiefOfStaffBucket.NEEDS_RESEARCH)
        if needs_skiptrace:
            tags.append(AresChiefOfStaffBucket.NEEDS_SKIPTRACE)
        if suppressed or (not _clean(lead.property_address) and not has_direct_contact):
            tags.append(AresChiefOfStaffBucket.BLOCKED)
        if not tags:
            tags.append(AresChiefOfStaffBucket.WATCHLIST if score >= 40 else AresChiefOfStaffBucket.PASS)

        primary_bucket = self._primary_bucket(tags)
        primary_lane, secondary_lanes = self._lanes(
            lead,
            probate_signal=probate_signal,
            tax_signal=tax_signal,
            estate_signal=estate_signal,
            title_review=title_review,
        )
        return AresChiefOfStaffLeadCard(
            lead_id=lead.id or lead.identity_key(),
            display_name=self._display_name(lead),
            property_address=_clean(lead.property_address),
            county=self._raw_text(lead, "county") or None,
            source=lead.source.value,
            primary_lane=primary_lane,
            secondary_lanes=secondary_lanes,
            score=score,
            primary_bucket=primary_bucket,
            queue_tags=tags,
            contact_ready=contact_ready,
            has_phone=has_phone,
            has_email=has_email,
            has_mailing_address=has_mailing_address,
            approval_required=True,
            reasons=reasons,
            blockers=blockers,
            next_action=self._next_action(primary_bucket, needs_research=needs_research, needs_skiptrace=needs_skiptrace),
            suggested_contact_angle=self._contact_angle(primary_lane) if contact_ready else None,
            risk_notes=self._risk_notes(lead, authority_unclear=authority_unclear, title_review=title_review),
            evidence={
                "probate_signal": probate_signal,
                "tax_delinquent_signal": tax_signal,
                "estate_or_heirship_signal": estate_signal,
                "title_review_signal": title_review,
                "has_direct_contact": has_direct_contact,
                "outreach_sent_by_chief_of_staff": False,
            },
        )

    def _operational_context(self, *, business_id: str, environment: str) -> dict[str, Any]:
        if self.lead_machine_service is None:
            return {
                "status": "not_attached",
                "message": "No lead-machine reader was attached to this Chief of Staff run.",
            }
        try:
            health = self.lead_machine_service.get_probate_autopilot_health(
                business_id=business_id,
                environment=environment,
                max_brief_age_hours=None,
            )
            health_data = _model_dump(health)
            latest = self.lead_machine_service.get_latest_morning_brief(business_id=business_id, environment=environment)
            latest_summary = self.lead_machine_service.summarize_morning_brief(latest)
            summary_data = _model_dump(latest_summary) if latest_summary is not None else None
            return self._safe_operational_context(health_data=health_data, morning_brief=summary_data)
        except Exception as exc:  # noqa: BLE001 - report read-only context failures without failing the lead brief.
            return {
                "status": "unavailable",
                "read_error": exc.__class__.__name__,
                "message": "Lead-machine operational context could not be read; lead scoring still completed from current lead records.",
            }

    def _safe_operational_context(self, *, health_data: dict[str, Any], morning_brief: dict[str, Any] | None) -> dict[str, Any]:
        backlog = dict(health_data.get("enrichment_backlog") or {})
        source_quality = dict(health_data.get("source_quality") or {})
        sla_health = dict(health_data.get("sla_health") or {})
        operator_actions = [
            {
                "priority": str(item.get("priority") or "normal"),
                "action": str(item.get("action") or "review"),
                "reason": "Lead-machine requested operator review; see local morning-brief artifacts for exact details.",
            }
            for item in list(health_data.get("operator_next_actions") or [])[:5]
            if isinstance(item, dict)
        ]
        latest_brief = None
        if morning_brief:
            sections = dict(morning_brief.get("sections") or {})
            latest_brief = {
                "id": morning_brief.get("id"),
                "generated_at": _json_safe(morning_brief.get("generated_at")),
                "new_record_count": morning_brief.get("new_record_count", 0),
                "hot_lead_count": morning_brief.get("hot_lead_count", 0),
                "warm_lead_count": morning_brief.get("warm_lead_count", 0),
                "blocked_count": morning_brief.get("blocked_count", 0),
                "approval_required_count": morning_brief.get("approval_required_count", 0),
                "source_health": _small_dict(sections.get("source_health")),
                "county_counts": _small_list(sections.get("county_counts"), limit=4),
                "operator_next_actions": [
                    {
                        "priority": str(item.get("priority") or "normal"),
                        "action": str(item.get("action") or "review"),
                    }
                    for item in _small_list(sections.get("operator_next_actions"), limit=5)
                    if isinstance(item, dict)
                ],
            }
        return {
            "status": str(health_data.get("status") or "unknown"),
            "latest_brief_id": health_data.get("latest_brief_id"),
            "generated_at": _json_safe(health_data.get("generated_at")),
            "brief_age_hours": health_data.get("brief_age_hours"),
            "freshness_ok": bool(health_data.get("freshness_ok")),
            "stale_brief": bool(health_data.get("stale_brief")),
            "no_send_ok": bool(health_data.get("no_send_ok")),
            "outbound_allowed": bool(health_data.get("outbound_allowed")),
            "source_run_count": int(health_data.get("source_run_count") or 0),
            "warning_count": int(health_data.get("warning_count") or 0),
            "new_record_count": int(health_data.get("new_record_count") or 0),
            "anomaly_count": int(health_data.get("anomaly_count") or 0),
            "operator_next_actions": operator_actions,
            "sla_health": _small_dict(sla_health),
            "source_quality": _small_dict(source_quality),
            "enrichment_backlog": _small_dict(backlog),
            "latest_morning_brief": latest_brief,
        }

    def _worklog(
        self,
        *,
        business_id: str,
        environment: str,
        lead_count: int,
        queue_counts: dict[str, int],
        operational_context: dict[str, Any],
    ) -> list[str]:
        items = [
            f"Reviewed {lead_count} current lead record(s) for {business_id}/{environment}.",
            "Scored and bucketed leads into hot, contact-ready, research, skiptrace, blocked, watchlist, and pass queues.",
            "Prepared an operator-only report; I did not contact sellers, spend skiptrace credits, or mutate providers.",
        ]
        status = operational_context.get("status")
        if status and status != "not_attached":
            items.append(
                f"Checked lead-machine health: status={status}, source runs={operational_context.get('source_run_count', 0)}, warnings={operational_context.get('warning_count', 0)}."
            )
        if queue_counts.get(AresChiefOfStaffBucket.CONTACT_READY.value, 0):
            items.append("Separated contact-ready leads from hot leads that still need authority/title research.")
        return items

    def _employee_priorities(
        self,
        queues: dict[str, list[AresChiefOfStaffLeadCard]],
        *,
        queue_counts: dict[str, int],
        operational_context: dict[str, Any],
    ) -> list[str]:
        priorities = list(self._recommended_focus(queues))
        for item in list(operational_context.get("operator_next_actions") or [])[:3]:
            if isinstance(item, dict):
                action = str(item.get("action") or "review_lead_machine")
                reason = str(item.get("reason") or "Lead-machine requested operator review.")
                priorities.append(f"Lead-machine action: {action.replace('_', ' ')} — {reason}")
        if operational_context.get("stale_brief"):
            priorities.insert(0, "Repair or rerun the lead-machine source pull before trusting today's pipeline health.")
        if not priorities and queue_counts.get(AresChiefOfStaffBucket.WATCHLIST.value, 0):
            priorities.append("Review the watchlist; no contact-ready lead surfaced from current data.")
        return priorities[:6]

    def _employee_blockers(self, *, queue_counts: dict[str, int], operational_context: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        research = queue_counts.get(AresChiefOfStaffBucket.NEEDS_RESEARCH.value, 0)
        skiptrace = queue_counts.get(AresChiefOfStaffBucket.NEEDS_SKIPTRACE.value, 0)
        blocked = queue_counts.get(AresChiefOfStaffBucket.BLOCKED.value, 0)
        if research:
            blockers.append(f"{research} lead(s) need authority/title/case-detail research before seller outreach.")
        if skiptrace:
            blockers.append(f"{skiptrace} lead(s) lack direct contact info; paid skiptrace requires approval before lookup.")
        if blocked:
            blockers.append(f"{blocked} lead(s) are blocked by suppression, missing identity, missing property/contact data, or closed status.")
        if operational_context.get("status") in {"blocked", "warning", "unavailable", "no_data"}:
            blockers.append(f"Lead-machine health is {operational_context.get('status')}; check source-run health before relying on new intake velocity.")
        if operational_context.get("outbound_allowed"):
            blockers.append("Unexpected outbound_allowed=true in operational health; keep this report read-only until gates are reviewed.")
        return blockers

    def _approval_requests(self, queue_counts: dict[str, int]) -> list[str]:
        approvals: list[str] = []
        contact_ready = queue_counts.get(AresChiefOfStaffBucket.CONTACT_READY.value, 0)
        skiptrace = queue_counts.get(AresChiefOfStaffBucket.NEEDS_SKIPTRACE.value, 0)
        research = queue_counts.get(AresChiefOfStaffBucket.NEEDS_RESEARCH.value, 0)
        if contact_ready:
            approvals.append(f"Approve exact outreach/campaign copy before I contact {contact_ready} contact-ready lead(s).")
        if skiptrace:
            approvals.append(f"Approve paid skiptrace budget and provider before I enrich {skiptrace} lead(s).")
        if research:
            approvals.append(f"Approve the title/legal research lane for {research} authority/title-blocked lead(s).")
        if not approvals:
            approvals.append("No seller outreach, paid skiptrace, or provider mutation approval requested from this report.")
        return approvals

    def _operational_status_line(self, operational_context: dict[str, Any]) -> str:
        status = str(operational_context.get("status") or "not_attached")
        if status == "not_attached":
            return "Lead-machine health not attached to this run"
        if status == "no_data":
            return "Lead-machine health has no current morning brief"
        if operational_context.get("stale_brief"):
            return f"Lead-machine health is stale ({operational_context.get('brief_age_hours')}h old)"
        return f"Lead-machine health: {status}; no-send OK={operational_context.get('no_send_ok', False)}"

    def _operational_status_lines(self, operational_context: dict[str, Any]) -> list[str]:
        latest = operational_context.get("latest_morning_brief") or {}
        return [
            self._operational_status_line(operational_context),
            f"Source runs: {operational_context.get('source_run_count', 0)}; new records: {operational_context.get('new_record_count', 0)}; warnings: {operational_context.get('warning_count', 0)}; anomalies: {operational_context.get('anomaly_count', 0)}.",
            f"Latest brief: {latest.get('id') or operational_context.get('latest_brief_id') or 'none'} generated at {latest.get('generated_at') or operational_context.get('generated_at') or 'unknown'}.",
        ]

    @staticmethod
    def _slack_bullets(items: list[str], *, fallback: str) -> str:
        return "\n".join(f"• {item}" for item in items) if items else f"• {fallback}"

    def _source_summary(self, leads: list[LeadRecord]) -> dict[str, Any]:
        source_counts: dict[str, int] = defaultdict(int)
        status_counts: dict[str, int] = defaultdict(int)
        for lead in leads:
            source_counts[lead.source.value] += 1
            status_counts[lead.lifecycle_status.value] += 1
        return {
            "source_counts": dict(sorted(source_counts.items())),
            "lifecycle_status_counts": dict(sorted(status_counts.items())),
        }

    def _recommended_focus(self, queues: dict[str, list[AresChiefOfStaffLeadCard]]) -> list[str]:
        contact_ready = queues.get(AresChiefOfStaffBucket.CONTACT_READY.value, [])
        research = queues.get(AresChiefOfStaffBucket.NEEDS_RESEARCH.value, [])
        skiptrace = queues.get(AresChiefOfStaffBucket.NEEDS_SKIPTRACE.value, [])
        focus: list[str] = []
        if contact_ready:
            focus.append(f"Work {len(contact_ready)} contact-ready lead(s) first; use the local artifacts for exact record details.")
        if research:
            focus.append(f"Resolve authority/title research for {len(research)} hot-but-not-ready lead(s).")
        if skiptrace:
            focus.append(f"Review {len(skiptrace)} skiptrace candidate(s); approval is required before any paid lookup.")
        if not focus:
            focus.append("No contact-ready lead surfaced; review watchlist and latest lead-machine run health.")
        return focus

    def _slack_safe_operational_context(self, operational_context: dict[str, Any]) -> dict[str, Any]:
        latest = operational_context.get("latest_morning_brief") or {}
        return {
            "status": operational_context.get("status"),
            "latest_brief_id": operational_context.get("latest_brief_id") or latest.get("id"),
            "generated_at": operational_context.get("generated_at") or latest.get("generated_at"),
            "brief_age_hours": operational_context.get("brief_age_hours"),
            "freshness_ok": operational_context.get("freshness_ok"),
            "stale_brief": operational_context.get("stale_brief"),
            "no_send_ok": operational_context.get("no_send_ok"),
            "outbound_allowed": operational_context.get("outbound_allowed"),
            "source_run_count": operational_context.get("source_run_count", 0),
            "warning_count": operational_context.get("warning_count", 0),
            "new_record_count": operational_context.get("new_record_count", 0),
            "anomaly_count": operational_context.get("anomaly_count", 0),
        }

    def _slack_payload(self, brief: AresChiefOfStaffBrief) -> dict[str, Any]:
        top_by_queue = {
            bucket.value: [self._slack_safe_card(card, bucket=bucket.value, index=index) for index, card in enumerate(brief.queues.get(bucket.value, [])[:5], start=1)]
            for bucket in QUEUE_ORDER
        }
        return {
            "kind": brief.kind,
            "brief_id": brief.id,
            "generated_at": brief.generated_at,
            "employee": {
                "name": brief.employee_name,
                "role": brief.employee_role,
                "manager": brief.manager_name,
                "reporting_channel": brief.reporting_channel,
                "shift_status": brief.shift_status,
            },
            "input_lead_count": brief.input_lead_count,
            "queue_counts": brief.queue_counts,
            "top_by_queue": top_by_queue,
            "worklog": brief.worklog,
            "priorities": brief.priorities,
            "blockers": brief.blockers,
            "approval_requests": brief.approval_requests,
            "recommended_focus": brief.recommended_focus,
            "operational_context": self._slack_safe_operational_context(brief.operational_context),
            "slack_payload_redaction": "lead names, contact details, property addresses, raw case numbers, and raw lead IDs omitted",
            "safety": {
                "seller_outreach_sent": False,
                "paid_skiptrace_spent": False,
                "provider_mutation_performed": False,
                "telegram_delivery": False,
            },
        }

    @staticmethod
    def _slack_safe_card(card: AresChiefOfStaffLeadCard, *, bucket: str, index: int) -> dict[str, Any]:
        return {
            "lead_ref": f"COS-{bucket.replace('_', '-').upper()}-{index}",
            "bucket": bucket,
            "score": card.score,
            "county": card.county,
            "source": card.source,
            "primary_lane": card.primary_lane,
            "contact_ready": card.contact_ready,
            "has_direct_contact": card.has_phone or card.has_email,
            "has_mailing_address": card.has_mailing_address,
            "approval_required": card.approval_required,
            "next_action": card.next_action,
            "reason_count": len(card.reasons),
            "blocker_count": len(card.blockers),
        }

    def _slack_queue_lines(self, cards: list[AresChiefOfStaffLeadCard], label: str) -> list[str]:
        if not cards:
            return []
        lines = [f"*{label}* — anonymized refs; use artifacts for full lead details."]
        for index, card in enumerate(cards[:5], start=1):
            ref = f"COS-{label.split()[1].upper() if len(label.split()) > 1 else 'LEAD'}-{index}"
            county = f" — {card.county}" if card.county else ""
            lines.append(f"{index}. `{ref}`{county} — score {card.score:.0f} — {card.primary_lane} — {card.next_action}")
        return lines

    @staticmethod
    def _write_queue_csv(path: Path, cards: list[AresChiefOfStaffLeadCard]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "lead_id",
                    "display_name",
                    "property_address",
                    "county",
                    "primary_lane",
                    "score",
                    "contact_ready",
                    "has_phone",
                    "has_email",
                    "has_mailing_address",
                    "next_action",
                    "reasons",
                    "blockers",
                ],
            )
            writer.writeheader()
            for card in cards:
                writer.writerow(
                    {
                        "lead_id": card.lead_id,
                        "display_name": card.display_name,
                        "property_address": card.property_address or "",
                        "county": card.county or "",
                        "primary_lane": card.primary_lane,
                        "score": card.score,
                        "contact_ready": card.contact_ready,
                        "has_phone": card.has_phone,
                        "has_email": card.has_email,
                        "has_mailing_address": card.has_mailing_address,
                        "next_action": card.next_action,
                        "reasons": "; ".join(card.reasons),
                        "blockers": "; ".join(card.blockers),
                    }
                )

    def _artifact_root(self, artifact_root: str | Path | None) -> Path | None:
        if artifact_root is not None:
            return Path(artifact_root)
        configured = getattr(self.settings, "ares_chief_of_staff_artifact_root", None) or self.settings.lead_machine_artifact_root
        return Path(configured) if configured else None

    def _score(self, lead: LeadRecord) -> float:
        explicit = lead.score
        if explicit is None:
            explicit = _number_or_none(self._raw_value(lead, "lead_score", "score", "hot_score"))
        if explicit is not None:
            return max(0.0, min(100.0, float(explicit)))
        score = 35.0
        if lead.source == LeadSource.PROBATE_INTAKE or lead.probate_case_number:
            score += 20
        if self._raw_bool(lead, "tax_delinquent", "delinquent_taxes"):
            score += 20
        if self._raw_bool(lead, "estate_of", "estate_signal"):
            score += 15
        if lead.phone or lead.email:
            score += 10
        if lead.property_address:
            score += 10
        return max(0.0, min(100.0, score))

    def _reasons(
        self,
        *,
        score: float,
        probate_signal: bool,
        tax_signal: bool,
        estate_signal: bool,
        title_review: bool,
        has_direct_contact: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if score >= 70:
            reasons.append("Score is 70+ based on current Ares data.")
        if probate_signal:
            reasons.append("Probate/heirship signal is present.")
        if tax_signal:
            reasons.append("Tax delinquency signal is present.")
        if estate_signal:
            reasons.append("Estate/title complexity may create curative-title edge.")
        if title_review:
            reasons.append("Title friction exists and needs operator review.")
        if has_direct_contact:
            reasons.append("Direct phone/email exists for operator-approved outreach.")
        return reasons or ["Lead is retained for watchlist review."]

    def _blockers(
        self,
        lead: LeadRecord,
        *,
        suppressed: bool,
        has_direct_contact: bool,
        authority_unclear: bool,
        title_review: bool,
    ) -> list[str]:
        blockers: list[str] = []
        if suppressed:
            blockers.append("Lead lifecycle is suppressed/closed.")
        if not has_direct_contact:
            blockers.append("No direct phone/email on record.")
        if authority_unclear:
            blockers.append("Living decision-maker or seller authority is unclear.")
        if title_review:
            blockers.append("Title/probate friction needs review before contact-ready status.")
        if not _clean(lead.property_address):
            blockers.append("Property address is missing.")
        if self._case_detail_incomplete(lead):
            blockers.append("Case-detail enrichment is incomplete/postback-only.")
        return blockers

    def _next_action(
        self,
        primary_bucket: AresChiefOfStaffBucket,
        *,
        needs_research: bool,
        needs_skiptrace: bool,
    ) -> str:
        if primary_bucket == AresChiefOfStaffBucket.BLOCKED:
            return "Repair missing identity/suppression state before action."
        if primary_bucket == AresChiefOfStaffBucket.CONTACT_READY:
            return "Contact this lead today with an operator-approved outreach step."
        if needs_research:
            return "Resolve authority/title research before seller outreach."
        if needs_skiptrace:
            return "Approve skiptrace only if the deal thesis still holds."
        if primary_bucket == AresChiefOfStaffBucket.HOT:
            return "Review the deal thesis and promote to Deal Desk if still valid."
        if primary_bucket == AresChiefOfStaffBucket.PASS:
            return "Pass unless new evidence changes the deal thesis."
        return "Keep on watchlist and wait for stronger motivation/contact evidence."

    def _lanes(
        self,
        lead: LeadRecord,
        *,
        probate_signal: bool,
        tax_signal: bool,
        estate_signal: bool,
        title_review: bool,
    ) -> tuple[str, list[str]]:
        lanes: list[str] = []
        if estate_signal or (probate_signal and (tax_signal or title_review)):
            lanes.append("curative_title")
        if probate_signal:
            lanes.append("probate_heirship")
        if tax_signal:
            lanes.append("tax_delinquent")
        if lead.source == LeadSource.INSTANTLY_SYNC or lead.source == LeadSource.INSTANTLY_IMPORT:
            lanes.append("outbound_followup")
        if self._raw_bool(lead, "lease_option_candidate"):
            lanes.append("lease_option")
        if self._raw_bool(lead, "creative_finance_candidate", "seller_finance_candidate"):
            lanes.append("creative_finance")
        if not lanes:
            lanes.append("general_real_estate")
        return lanes[0], lanes[1:]

    def _contact_angle(self, primary_lane: str) -> str:
        if primary_lane in {"curative_title", "probate_heirship"}:
            return "Ask about property plans and decision-maker authority; do not imply legal conclusions."
        if primary_lane == "tax_delinquent":
            return "Ask if they want a simple sale or flexible solution before tax pressure worsens."
        if primary_lane in {"lease_option", "creative_finance"}:
            return "Ask if they are open to flexible terms instead of a straight sale."
        return "Ask if they would consider selling or discussing flexible options."

    def _risk_notes(self, lead: LeadRecord, *, authority_unclear: bool, title_review: bool) -> list[str]:
        notes: list[str] = []
        if authority_unclear:
            notes.append("Do not treat decedent/estate as a contact target; identify a living authority contact first.")
        if title_review:
            notes.append("Title complexity may be edge, but requires operator/legal review before offer confidence.")
        if lead.lifecycle_status == LeadLifecycleStatus.SUPPRESSED:
            notes.append("Suppressed lead must not receive outreach.")
        return notes

    def _display_name(self, lead: LeadRecord) -> str:
        full_name = " ".join(part for part in [_clean(lead.first_name), _clean(lead.last_name)] if part)
        if full_name:
            return full_name
        for value in (
            lead.company_name,
            self._raw_text(lead, "owner_name"),
            self._raw_text(lead, "decedent_name"),
            lead.property_address,
            lead.id,
        ):
            cleaned = _clean(value)
            if cleaned:
                return cleaned
        return "unknown lead"

    def _title_review_needed(self, lead: LeadRecord) -> bool:
        title_value = self._raw_value(lead, "title_friction", "title_status", "title_review")
        if isinstance(title_value, dict):
            status = str(title_value.get("status") or title_value.get("review_status") or "").lower()
            if any(clear_marker in status for clear_marker in ("clear", "matched", "complete")) and "review_needed" not in status:
                return False
            return any(marker in status for marker in ("review_needed", "friction", "quiet", "partition", "heir"))
        status_text = str(title_value or "").lower()
        if any(clear_marker in status_text for clear_marker in ("clear", "matched", "complete")) and "review_needed" not in status_text:
            return False
        return any(marker in status_text for marker in ("review_needed", "friction", "quiet", "partition", "heir"))

    def _authority_unclear(self, lead: LeadRecord, *, probate_signal: bool, estate_signal: bool) -> bool:
        authority = self._raw_text(lead, "authority_status", "seller_authority_status")
        if authority:
            return authority.lower() not in {"clear", "verified", "seller_verified", "authority_verified"}
        return probate_signal and estate_signal

    def _case_detail_incomplete(self, lead: LeadRecord) -> bool:
        detail_status = self._raw_text(lead, "case_detail_status", "case_detail_enrichment_status")
        return detail_status.lower() in {"incomplete", "postback_only", "blocked", "missing"}

    def _raw_bool(self, lead: LeadRecord, *keys: str) -> bool:
        value = self._raw_value(lead, *keys)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "1", "y", "hot"}
        return False

    def _raw_text(self, lead: LeadRecord, *keys: str) -> str:
        value = self._raw_value(lead, *keys)
        return str(value).strip() if value is not None else ""

    def _raw_value(self, lead: LeadRecord, *keys: str) -> Any:
        sources = (lead.raw_payload, lead.custom_variables, lead.personalization)
        for key in keys:
            for source in sources:
                value = _nested_lookup(source, key)
                if value is not None:
                    return value
        return None

    @staticmethod
    def _primary_bucket(tags: list[AresChiefOfStaffBucket]) -> AresChiefOfStaffBucket:
        for bucket in (
            AresChiefOfStaffBucket.BLOCKED,
            AresChiefOfStaffBucket.CONTACT_READY,
            AresChiefOfStaffBucket.NEEDS_RESEARCH,
            AresChiefOfStaffBucket.NEEDS_SKIPTRACE,
            AresChiefOfStaffBucket.HOT,
            AresChiefOfStaffBucket.WATCHLIST,
            AresChiefOfStaffBucket.PASS,
        ):
            if bucket in tags:
                return bucket
        return AresChiefOfStaffBucket.WATCHLIST


def _model_dump(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dict(dumped) if isinstance(dumped, dict) else {}
    if isinstance(value, dict):
        return dict(value)
    return {}


def _json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _small_dict(value: Any, *, limit: int = 12) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    safe: dict[str, Any] = {}
    for key, item in list(value.items())[:limit]:
        if isinstance(item, dict):
            safe[str(key)] = _small_dict(item, limit=limit)
        elif isinstance(item, list):
            safe[str(key)] = _small_list(item, limit=5)
        else:
            safe[str(key)] = _json_safe(item)
    return safe


def _small_list(value: Any, *, limit: int = 5) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [_small_dict(item) if isinstance(item, dict) else _json_safe(item) for item in value[:limit]]


def _nested_lookup(data: dict[str, Any], key: str) -> Any:
    if key in data:
        return data[key]
    for value in data.values():
        if isinstance(value, dict):
            found = _nested_lookup(value, key)
            if found is not None:
                return found
    return None


def _clean(value: str | None) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _number_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date_from_iso(value: str) -> str:
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return utc_now().date().isoformat()
