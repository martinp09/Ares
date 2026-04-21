from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
import re

from pydantic import BaseModel, ConfigDict

from app.domains.ares import (
    AresCounty,
    AresExecutionActionSpec,
    AresExecutionDecision,
    AresExecutionGuardrailResult,
    AresExecutionRunSpec,
    AresLeadRecord,
    AresSourceLane,
)
from app.services.ares_copy_service import AresCopyService, AresLeadBrief, AresOutreachDraft
from app.services.ares_policy_service import AresPolicyDecision, AresPolicyService
from app.services.ares_service import AresMatchingService, RankedAresLead


CountyFetchPayload = Mapping[str, Sequence[Mapping[str, object]]]
CountyFetcher = Callable[[AresCounty], CountyFetchPayload]
_ADDRESS_WHITESPACE_PATTERN = re.compile(r"\s+")


class AresExecutionAuditAction(StrEnum):
    RUN_REGISTERED = "run_registered"
    ACTION_AUTHORIZED = "action_authorized"
    KILL_SWITCH_UPDATED = "kill_switch_updated"
    RUN_EXECUTED = "run_executed"
    COUNTY_FETCH_FAILED = "county_fetch_failed"
    RUN_INTERRUPTED = "run_interrupted"


class AresExecutionAuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    action: AresExecutionAuditAction
    run_id: str | None = None
    action_id: str | None = None
    tool_name: str | None = None
    decision: AresExecutionDecision | None = None
    reason: str | None = None
    attempt: int | None = None
    budget_remaining: int | None = None
    kill_switch_enabled: bool | None = None
    county: AresCounty | None = None
    stage: str | None = None


class AresExecutionFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    county: AresCounty | None
    stage: str
    reason: str


@dataclass(frozen=True)
class AresExecutionTaskSuggestion:
    task_type: str
    rank: int
    county: AresCounty
    title: str
    reason: str


@dataclass(frozen=True)
class AresExecutionFollowUpWork:
    work_type: str
    rank: int
    county: AresCounty
    payload: dict[str, object]


@dataclass(frozen=True)
class AresExecutionRunOutput:
    normalized_probate_records: list[AresLeadRecord]
    normalized_tax_records: list[AresLeadRecord]
    ranked_leads: list[RankedAresLead]
    briefs: list[AresLeadBrief]
    drafts: list[AresOutreachDraft]
    task_suggestions: list[AresExecutionTaskSuggestion]
    follow_up_work_queue: list[AresExecutionFollowUpWork]
    failures: list[AresExecutionFailure]
    interrupted: bool


class AresExecutionService:
    def __init__(
        self,
        *,
        policy_service: AresPolicyService,
        county_fetcher: CountyFetcher | None = None,
        matching_service: AresMatchingService | None = None,
        copy_service: AresCopyService | None = None,
    ) -> None:
        self._policy_service = policy_service
        self._county_fetcher: CountyFetcher = county_fetcher or self._default_county_fetcher
        self._matching_service = matching_service or AresMatchingService()
        self._copy_service = copy_service or AresCopyService()
        self._runs: dict[str, AresExecutionRunSpec] = {}
        self._consumed_actions_by_run: dict[str, set[tuple[str, int]]] = {}
        self._audit_entries: list[AresExecutionAuditEntry] = []
        self._kill_switch_enabled = False
        self._kill_switch_reason = ""

    def set_county_fetcher(self, county_fetcher: CountyFetcher) -> None:
        self._county_fetcher = county_fetcher

    def register_run(self, run: AresExecutionRunSpec) -> None:
        self._runs[run.run_id] = run
        self._consumed_actions_by_run.setdefault(run.run_id, set())
        self._append_audit_entry(
            action=AresExecutionAuditAction.RUN_REGISTERED,
            run_id=run.run_id,
            reason="Execution run registered",
            budget_remaining=run.action_budget,
        )

    def authorize_action(
        self,
        *,
        run_id: str,
        action: AresExecutionActionSpec,
    ) -> AresExecutionGuardrailResult:
        run = self._runs.get(run_id)
        if run is None:
            return self._audit_authorization(
                run_id=run_id,
                action=action,
                decision=AresExecutionDecision.DENY,
                reason="Execution run is not registered",
                budget_remaining=None,
            )

        if self._kill_switch_enabled:
            return self._audit_authorization(
                run_id=run_id,
                action=action,
                decision=AresExecutionDecision.DENY,
                reason=f"Denied by kill switch: {self._kill_switch_reason}",
                budget_remaining=self._budget_remaining(run_id=run_id),
            )

        if action.tool_name not in run.approved_tools:
            return self._audit_authorization(
                run_id=run_id,
                action=action,
                decision=AresExecutionDecision.DENY,
                reason="Tool denied by execution allowlist",
                budget_remaining=self._budget_remaining(run_id=run_id),
            )

        if action.attempt > run.retry_limit:
            return self._audit_authorization(
                run_id=run_id,
                action=action,
                decision=AresExecutionDecision.DENY,
                reason="Action exceeds retry limit",
                budget_remaining=self._budget_remaining(run_id=run_id),
            )

        consumed_actions = self._consumed_actions_by_run[run_id]
        action_key = (action.action_id, action.attempt)
        if action_key in consumed_actions:
            return self._audit_authorization(
                run_id=run_id,
                action=action,
                decision=AresExecutionDecision.DENY,
                reason="Execution action was already authorized for this attempt",
                budget_remaining=self._budget_remaining(run_id=run_id),
            )
        if len(consumed_actions) >= run.action_budget:
            return self._audit_authorization(
                run_id=run_id,
                action=action,
                decision=AresExecutionDecision.DENY,
                reason="Action budget exhausted for run",
                budget_remaining=0,
            )

        policy_result = self._policy_service.evaluate_call(
            tool_name=action.tool_name,
            raw_input=action.raw_input,
            requested_effects=action.requested_effects,
            hard_approval_id=action.hard_approval_id,
            business_id=run.business_id,
            environment=run.environment,
        )
        if policy_result.decision is not AresPolicyDecision.ALLOW:
            return self._audit_authorization(
                run_id=run_id,
                action=action,
                decision=AresExecutionDecision.DENY,
                reason=policy_result.reason,
                budget_remaining=self._budget_remaining(run_id=run_id),
            )

        consumed_actions.add(action_key)
        return self._audit_authorization(
            run_id=run_id,
            action=action,
            decision=AresExecutionDecision.ALLOW,
            reason="Execution action is within guardrails",
            budget_remaining=self._budget_remaining(run_id=run_id),
        )

    def execute_bounded_run(self, *, run_id: str) -> AresExecutionRunOutput:
        run = self._runs.get(run_id)
        if run is None:
            failure = AresExecutionFailure(county=None, stage="run_lookup", reason="Execution run is not registered")
            return self._empty_output(failures=[failure], interrupted=False)

        if self._kill_switch_enabled:
            self._append_audit_entry(
                action=AresExecutionAuditAction.RUN_INTERRUPTED,
                run_id=run_id,
                reason=self._kill_switch_reason,
            )
            return self._empty_output(failures=[], interrupted=True)

        probate_records: list[AresLeadRecord] = []
        tax_records: list[AresLeadRecord] = []
        failures: list[AresExecutionFailure] = []
        interrupted = False

        for county in run.counties:
            if self._kill_switch_enabled:
                interrupted = True
                self._append_audit_entry(
                    action=AresExecutionAuditAction.RUN_INTERRUPTED,
                    run_id=run_id,
                    county=county,
                    reason=self._kill_switch_reason,
                )
                break

            try:
                payload = self._county_fetcher(county)
            except Exception as exc:  # pragma: no cover - exercised by tests
                reason = str(exc).strip() or "County data fetch failed"
                failures.append(AresExecutionFailure(county=county, stage="fetch", reason=reason))
                self._append_audit_entry(
                    action=AresExecutionAuditAction.COUNTY_FETCH_FAILED,
                    run_id=run_id,
                    county=county,
                    stage="fetch",
                    reason=reason,
                )
                continue

            probate_records.extend(self._normalize_records(county=county, lane=AresSourceLane.PROBATE, raw_records=payload.get("probate", ())))
            tax_records.extend(
                self._normalize_records(county=county, lane=AresSourceLane.TAX_DELINQUENT, raw_records=payload.get("tax", ()))
            )

        deduped_tax = self._dedupe_records(tax_records)
        tax_by_key = {self._record_key(record): record for record in deduped_tax}
        deduped_probate = self._enrich_probate_records(self._dedupe_records(probate_records), tax_by_key=tax_by_key)

        ranked = self._matching_service.rank_leads(probate_records=deduped_probate, tax_records=deduped_tax)
        briefs = self._copy_service.generate_lead_briefs(ranked)
        drafts = self._copy_service.generate_outreach_drafts(ranked)
        task_suggestions = self._build_task_suggestions(briefs=briefs, drafts=drafts)
        follow_up_queue = self._build_follow_up_queue(task_suggestions=task_suggestions, drafts=drafts)

        self._append_audit_entry(
            action=AresExecutionAuditAction.RUN_EXECUTED,
            run_id=run_id,
            reason=f"Generated {len(ranked)} ranked leads",
        )

        return AresExecutionRunOutput(
            normalized_probate_records=deduped_probate,
            normalized_tax_records=deduped_tax,
            ranked_leads=ranked,
            briefs=briefs,
            drafts=drafts,
            task_suggestions=task_suggestions,
            follow_up_work_queue=follow_up_queue,
            failures=failures,
            interrupted=interrupted,
        )

    def set_kill_switch(self, *, enabled: bool, reason: str) -> None:
        self._kill_switch_enabled = enabled
        self._kill_switch_reason = reason.strip()
        self._append_audit_entry(
            action=AresExecutionAuditAction.KILL_SWITCH_UPDATED,
            reason=self._kill_switch_reason,
            kill_switch_enabled=enabled,
        )

    def audit_trail(self) -> list[AresExecutionAuditEntry]:
        return [entry.model_copy(deep=True) for entry in self._audit_entries]

    def _budget_remaining(self, *, run_id: str) -> int:
        run = self._runs[run_id]
        consumed = len(self._consumed_actions_by_run[run_id])
        return max(0, run.action_budget - consumed)

    def _audit_authorization(
        self,
        *,
        run_id: str,
        action: AresExecutionActionSpec,
        decision: AresExecutionDecision,
        reason: str,
        budget_remaining: int | None,
    ) -> AresExecutionGuardrailResult:
        self._append_audit_entry(
            action=AresExecutionAuditAction.ACTION_AUTHORIZED,
            run_id=run_id,
            action_id=action.action_id,
            tool_name=action.tool_name,
            decision=decision,
            reason=reason,
            attempt=action.attempt,
            budget_remaining=budget_remaining,
        )
        return AresExecutionGuardrailResult(decision=decision, reason=reason)

    def _append_audit_entry(
        self,
        *,
        action: AresExecutionAuditAction,
        run_id: str | None = None,
        action_id: str | None = None,
        tool_name: str | None = None,
        decision: AresExecutionDecision | None = None,
        reason: str | None = None,
        attempt: int | None = None,
        budget_remaining: int | None = None,
        kill_switch_enabled: bool | None = None,
        county: AresCounty | None = None,
        stage: str | None = None,
    ) -> None:
        entry = AresExecutionAuditEntry(
            sequence=len(self._audit_entries) + 1,
            action=action,
            run_id=run_id,
            action_id=action_id,
            tool_name=tool_name,
            decision=decision,
            reason=reason,
            attempt=attempt,
            budget_remaining=budget_remaining,
            kill_switch_enabled=kill_switch_enabled,
            county=county,
            stage=stage,
        )
        self._audit_entries.append(entry)

    def _normalize_records(
        self,
        *,
        county: AresCounty,
        lane: AresSourceLane,
        raw_records: Sequence[Mapping[str, object]],
    ) -> list[AresLeadRecord]:
        normalized: list[AresLeadRecord] = []
        for raw in raw_records:
            address_value = raw.get("property_address")
            address = self._normalize_address(address_value)
            if not address:
                continue
            owner = self._normalize_owner(raw.get("owner_name"))
            estate_of = bool(raw.get("estate_of", False))
            normalized.append(
                AresLeadRecord(
                    county=county,
                    source_lane=lane,
                    property_address=address,
                    owner_name=owner,
                    estate_of=estate_of,
                )
            )
        return normalized

    def _dedupe_records(self, records: Sequence[AresLeadRecord]) -> list[AresLeadRecord]:
        deduped: dict[tuple[str, str, str], AresLeadRecord] = {}
        for record in records:
            key = (record.county.value, record.source_lane.value, self._normalized_key(record.property_address))
            existing = deduped.get(key)
            if existing is None:
                deduped[key] = record
                continue
            deduped[key] = self._prefer_record(existing=existing, candidate=record)
        return list(deduped.values())

    def _enrich_probate_records(
        self,
        probate_records: Sequence[AresLeadRecord],
        *,
        tax_by_key: Mapping[tuple[str, str], AresLeadRecord],
    ) -> list[AresLeadRecord]:
        enriched: list[AresLeadRecord] = []
        for record in probate_records:
            tax_record = tax_by_key.get(self._record_key(record))
            owner_name = record.owner_name or (tax_record.owner_name if tax_record is not None else None)
            enriched.append(
                AresLeadRecord(
                    county=record.county,
                    source_lane=record.source_lane,
                    property_address=record.property_address,
                    owner_name=owner_name,
                    estate_of=record.estate_of,
                )
            )
        return enriched

    def _build_task_suggestions(
        self,
        *,
        briefs: Sequence[AresLeadBrief],
        drafts: Sequence[AresOutreachDraft],
    ) -> list[AresExecutionTaskSuggestion]:
        suggestions: list[AresExecutionTaskSuggestion] = []
        for brief in briefs:
            suggestions.append(
                AresExecutionTaskSuggestion(
                    task_type="review_lead_brief",
                    rank=brief.rank,
                    county=brief.county,
                    title=f"Review lead brief rank #{brief.rank}",
                    reason=brief.rationale,
                )
            )
        for draft in drafts:
            suggestions.append(
                AresExecutionTaskSuggestion(
                    task_type="review_outreach_draft",
                    rank=draft.rank,
                    county=draft.county,
                    title=f"Review outreach draft rank #{draft.rank}",
                    reason=draft.rationale,
                )
            )
        return suggestions

    def _build_follow_up_queue(
        self,
        *,
        task_suggestions: Sequence[AresExecutionTaskSuggestion],
        drafts: Sequence[AresOutreachDraft],
    ) -> list[AresExecutionFollowUpWork]:
        queue: list[AresExecutionFollowUpWork] = []
        draft_subject_by_rank = {draft.rank: draft.subject for draft in drafts}
        for suggestion in task_suggestions:
            work_type = "operator_review" if suggestion.task_type == "review_lead_brief" else "draft_approval"
            payload: dict[str, object] = {
                "title": suggestion.title,
                "reason": suggestion.reason,
            }
            if suggestion.rank in draft_subject_by_rank:
                payload["draft_subject"] = draft_subject_by_rank[suggestion.rank]
            queue.append(
                AresExecutionFollowUpWork(
                    work_type=work_type,
                    rank=suggestion.rank,
                    county=suggestion.county,
                    payload=payload,
                )
            )
        return queue

    def _empty_output(self, *, failures: list[AresExecutionFailure], interrupted: bool) -> AresExecutionRunOutput:
        return AresExecutionRunOutput(
            normalized_probate_records=[],
            normalized_tax_records=[],
            ranked_leads=[],
            briefs=[],
            drafts=[],
            task_suggestions=[],
            follow_up_work_queue=[],
            failures=failures,
            interrupted=interrupted,
        )

    def _record_key(self, record: AresLeadRecord) -> tuple[str, str]:
        return (record.county.value, self._normalized_key(record.property_address))

    def _normalize_address(self, value: object) -> str:
        text = str(value or "")
        collapsed = _ADDRESS_WHITESPACE_PATTERN.sub(" ", text).strip()
        if not collapsed:
            return ""
        return collapsed.title()

    def _normalize_owner(self, value: object) -> str | None:
        text = _ADDRESS_WHITESPACE_PATTERN.sub(" ", str(value or "")).strip()
        if not text:
            return None
        return text

    def _normalized_key(self, address: str) -> str:
        return _ADDRESS_WHITESPACE_PATTERN.sub(" ", address).strip().lower()

    def _prefer_record(self, *, existing: AresLeadRecord, candidate: AresLeadRecord) -> AresLeadRecord:
        existing_score = int(bool(existing.owner_name)) + int(existing.estate_of)
        candidate_score = int(bool(candidate.owner_name)) + int(candidate.estate_of)
        if candidate_score > existing_score:
            return candidate
        return existing

    @staticmethod
    def _default_county_fetcher(_: AresCounty) -> CountyFetchPayload:
        return {"probate": (), "tax": ()}
