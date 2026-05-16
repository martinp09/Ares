from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from urllib.error import HTTPError

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.lead_machine_supabase import (
    external_id,
    fetch_rows,
    insert_rows,
    lead_machine_backend_enabled,
    patch_rows,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.commands import generate_id, generate_stable_id
from app.models.sms_agent import (
    SmsAgentEvalLabelRecord,
    SmsAgentEvalLabelRequest,
    SmsAgentJobCreate,
    SmsAgentJobRecord,
    SmsAgentReplyDecisionCreate,
    SmsAgentReplyDecisionRecord,
)


class SmsAgentSendRequestConflict(RuntimeError):
    pass


class SmsAgentRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        if force_memory is None:
            self._force_memory = client is not None and getattr(client, "backend", "memory") != "supabase"
        else:
            self._force_memory = force_memory

    def enqueue_job(self, create: SmsAgentJobCreate) -> SmsAgentJobRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._enqueue_job_in_supabase(create)
        now = utc_now()
        key = self._job_key(create)
        with self.client.transaction() as store:
            has_dedupe_identity = self._job_key_has_dedupe_identity(key)
            if has_dedupe_identity:
                existing_id = store.sms_agent_job_keys.get(key)
                if existing_id is not None:
                    existing = store.sms_agent_jobs[existing_id]
                    return SmsAgentJobRecord.model_validate(existing).model_copy(update={"deduped": True})

            job_id = (
                generate_stable_id("smsjob", *(str(part) for part in key if part is not None))
                if has_dedupe_identity
                else generate_id("smsjob")
            )
            record = SmsAgentJobRecord.model_validate(
                {
                    **create.model_dump(),
                    "id": job_id,
                    "status": "pending",
                    "attempt_count": 0,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            store.sms_agent_jobs[job_id] = record
            if has_dedupe_identity:
                store.sms_agent_job_keys[key] = job_id
            return record

    def claim_pending(self, limit: int, lock_seconds: int) -> list[SmsAgentJobRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._claim_pending_in_supabase(limit=limit, lock_seconds=lock_seconds)
        if limit <= 0:
            return []
        now = utc_now()
        locked_until = now + timedelta(seconds=lock_seconds)
        with self.client.transaction() as store:
            candidates: list[SmsAgentJobRecord] = []
            for stored_job in store.sms_agent_jobs.values():
                job = SmsAgentJobRecord.model_validate(stored_job)
                if job.status in {"pending", "failed_retryable"} and (job.locked_until is None or job.locked_until <= now):
                    candidates.append(job)
            candidates.sort(key=lambda job: (job.created_at or now, job.id))
            claimed: list[SmsAgentJobRecord] = []
            for job in candidates[:limit]:
                updated = job.model_copy(
                    update={
                        "status": "processing",
                        "attempt_count": job.attempt_count + 1,
                        "locked_until": locked_until,
                        "updated_at": now,
                    }
                )
                store.sms_agent_jobs[updated.id] = updated
                claimed.append(updated)
            return claimed

    def record_decision(self, create: SmsAgentReplyDecisionCreate) -> SmsAgentReplyDecisionRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._record_decision_in_supabase(create)
        now = utc_now()
        with self.client.transaction() as store:
            job = store.sms_agent_jobs.get(create.job_id)
            if job is None:
                raise ValueError("SMS agent job does not exist for tenant")
            job_record = SmsAgentJobRecord.model_validate(job)
            if job_record.business_id != create.business_id or job_record.environment != create.environment:
                raise ValueError("SMS agent job does not exist for tenant")
            decision_id = generate_stable_id(
                "smsdec",
                create.business_id,
                create.environment,
                create.job_id,
                str(len(store.sms_agent_decisions) + 1),
            )
            record = SmsAgentReplyDecisionRecord.model_validate(
                {
                    **create.model_dump(),
                    "id": decision_id,
                    "created_at": now,
                }
            )
            store.sms_agent_decisions[decision_id] = record
            return record

    def record_operator_send_request(self, create: SmsAgentReplyDecisionCreate) -> SmsAgentReplyDecisionRecord:
        if create.action != "operator_send_requested":
            raise ValueError("operator_send_requested action is required")
        parent_decision_id = create.metadata.get("parent_decision_id")
        if not isinstance(parent_decision_id, str) or not parent_decision_id.strip():
            raise ValueError("parent_decision_id is required")
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            try:
                return self._record_decision_in_supabase(create)
            except Exception as exc:
                if self._is_duplicate_send_request_error(exc):
                    raise SmsAgentSendRequestConflict("SMS send already requested") from exc
                raise
        now = utc_now()
        with self.client.transaction() as store:
            for existing in store.sms_agent_decisions.values():
                decision = SmsAgentReplyDecisionRecord.model_validate(existing)
                if (
                    decision.business_id == create.business_id
                    and decision.environment == create.environment
                    and decision.action == "operator_send_requested"
                    and decision.metadata.get("parent_decision_id") == parent_decision_id
                ):
                    raise SmsAgentSendRequestConflict("SMS send already requested")
            job = store.sms_agent_jobs.get(create.job_id)
            if job is None:
                raise ValueError("SMS agent job does not exist for tenant")
            job_record = SmsAgentJobRecord.model_validate(job)
            if job_record.business_id != create.business_id or job_record.environment != create.environment:
                raise ValueError("SMS agent job does not exist for tenant")
            decision_id = generate_stable_id(
                "smsdec",
                create.business_id,
                create.environment,
                create.job_id,
                str(len(store.sms_agent_decisions) + 1),
            )
            record = SmsAgentReplyDecisionRecord.model_validate(
                {
                    **create.model_dump(),
                    "id": decision_id,
                    "created_at": now,
                }
            )
            store.sms_agent_decisions[decision_id] = record
            return record

    def list_decisions(
        self,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[SmsAgentReplyDecisionRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._list_decisions_in_supabase(business_id=business_id, environment=environment)
        with self.client.transaction() as store:
            decisions = [
                SmsAgentReplyDecisionRecord.model_validate(decision)
                for decision in store.sms_agent_decisions.values()
            ]
        if business_id is not None:
            decisions = [decision for decision in decisions if decision.business_id == business_id]
        if environment is not None:
            decisions = [decision for decision in decisions if decision.environment == environment]
        decisions.sort(key=lambda decision: (decision.created_at or datetime.min, decision.id))
        return decisions

    def get_decision(self, decision_id: str) -> SmsAgentReplyDecisionRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(decision_id, "smsdec")
            if row_id is None:
                return None
            rows = fetch_rows(
                "sms_agent_decisions",
                params={"select": "*", "id": f"eq.{row_id}", "limit": "1"},
                settings=self.settings,
            )
            return self._decision_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            decision = store.sms_agent_decisions.get(decision_id)
            return SmsAgentReplyDecisionRecord.model_validate(decision) if decision is not None else None

    def record_eval_label(
        self,
        decision_id: str,
        request: SmsAgentEvalLabelRequest,
    ) -> SmsAgentEvalLabelRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._record_eval_label_in_supabase(decision_id, request)
        now = utc_now()
        with self.client.transaction() as store:
            decision = store.sms_agent_decisions.get(decision_id)
            if decision is None:
                raise ValueError("SMS agent decision does not exist")
            decision_record = SmsAgentReplyDecisionRecord.model_validate(decision)
            label_id = generate_stable_id(
                "smslbl",
                decision_id,
                request.label,
                request.reviewer or "",
                request.notes or "",
                str(len(store.sms_agent_eval_labels) + 1),
            )
            record = SmsAgentEvalLabelRecord.model_validate(
                {
                    **request.model_dump(),
                    "id": label_id,
                    "decision_id": decision_record.id,
                    "business_id": decision_record.business_id,
                    "environment": decision_record.environment,
                    "created_at": now,
                }
            )
            store.sms_agent_eval_labels[label_id] = record
            store.sms_agent_eval_label_keys[(decision_id, label_id)] = label_id
            return record

    def list_eval_labels(self, decision_id: str | None = None) -> list[SmsAgentEvalLabelRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._list_eval_labels_in_supabase(decision_id=decision_id)
        with self.client.transaction() as store:
            labels = [
                SmsAgentEvalLabelRecord.model_validate(label)
                for label in store.sms_agent_eval_labels.values()
            ]
        if decision_id is not None:
            labels = [label for label in labels if label.decision_id == decision_id]
        labels.sort(key=lambda label: (label.created_at, label.id))
        return labels

    def mark_completed(self, job_id: str, *, decision_id: str | None = None) -> SmsAgentJobRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._mark_completed_in_supabase(job_id, decision_id=decision_id)
        now = utc_now()
        with self.client.transaction() as store:
            existing = store.sms_agent_jobs.get(job_id)
            if existing is None:
                return None
            job = SmsAgentJobRecord.model_validate(existing)
            resolved_decision_id = decision_id or job.decision_id
            if resolved_decision_id is None:
                raise ValueError("decision_id is required to complete SMS agent job")
            updated = job.model_copy(
                update={
                    "status": "completed",
                    "decision_id": resolved_decision_id,
                    "locked_until": None,
                    "updated_at": now,
                }
            )
            store.sms_agent_jobs[job_id] = updated
            return updated

    def mark_failed(
        self,
        job_id: str,
        *,
        retryable: bool,
        error_message: str,
        decision_id: str | None = None,
    ) -> SmsAgentJobRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._mark_failed_in_supabase(
                job_id,
                retryable=retryable,
                error_message=error_message,
                decision_id=decision_id,
            )
        now = utc_now()
        with self.client.transaction() as store:
            existing = store.sms_agent_jobs.get(job_id)
            if existing is None:
                return None
            job = SmsAgentJobRecord.model_validate(existing)
            resolved_decision_id = decision_id or job.decision_id
            update = {
                "status": "failed_retryable" if retryable else "failed_terminal",
                "last_error": error_message,
                "locked_until": None,
                "updated_at": now,
            }
            if resolved_decision_id is not None:
                update["decision_id"] = resolved_decision_id
            updated = job.model_copy(update=update)
            store.sms_agent_jobs[job_id] = updated
            return updated

    def get_job(self, job_id: str) -> SmsAgentJobRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(job_id, "smsjob")
            if row_id is None:
                return None
            rows = fetch_rows("sms_agent_jobs", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._job_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            job = store.sms_agent_jobs.get(job_id)
            return SmsAgentJobRecord.model_validate(job) if job is not None else None

    @staticmethod
    def _job_key(create: SmsAgentJobCreate) -> tuple[str, str, str | None, str | None, str | None]:
        return (
            create.business_id,
            create.environment,
            create.provider_webhook_id,
            create.message_id,
            create.payload_hash,
        )

    @staticmethod
    def _job_key_has_dedupe_identity(key: tuple[str, str, str | None, str | None, str | None]) -> bool:
        return any(key[2:])

    def _enqueue_job_in_supabase(self, create: SmsAgentJobCreate) -> SmsAgentJobRecord:
        tenant = resolve_tenant(create.business_id, create.environment, settings=self.settings)
        if any((create.provider_webhook_id, create.message_id, create.payload_hash)):
            lookup_params = {
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "limit": "1",
            }
            self._add_nullable_filter(lookup_params, "provider_webhook_id", row_id_from_external_id(create.provider_webhook_id, "wh"))
            self._add_nullable_filter(lookup_params, "message_id", row_id_from_external_id(create.message_id, "msg"))
            self._add_nullable_filter(lookup_params, "payload_hash", create.payload_hash)
            existing = fetch_rows("sms_agent_jobs", params=lookup_params, settings=self.settings)
            if existing:
                return self._job_from_supabase(existing[0], deduped=True)
        row = insert_rows(
            "sms_agent_jobs",
            [self._job_payload_for_supabase(create, business_pk=tenant.business_pk, environment=tenant.environment)],
            select="*",
            settings=self.settings,
        )[0]
        return self._job_from_supabase(row)

    def _claim_pending_in_supabase(self, *, limit: int, lock_seconds: int) -> list[SmsAgentJobRecord]:
        if limit <= 0:
            return []
        now = utc_now()
        unlocked_filter = f"(locked_until.is.null,locked_until.lt.{now.isoformat()})"
        rows = fetch_rows(
            "sms_agent_jobs",
            params={
                "select": "*",
                "status": "in.(pending,failed_retryable)",
                "or": unlocked_filter,
                "order": "created_at.asc,id.asc",
                "limit": str(limit),
            },
            settings=self.settings,
        )
        claimed: list[SmsAgentJobRecord] = []
        locked_until = now + timedelta(seconds=lock_seconds)
        for row in rows:
            patched = patch_rows(
                "sms_agent_jobs",
                params={
                    "id": f"eq.{row['id']}",
                    "status": "in.(pending,failed_retryable)",
                    "or": unlocked_filter,
                },
                row={
                    "status": "processing",
                    "attempt_count": int(row.get("attempt_count") or 0) + 1,
                    "locked_until": locked_until.isoformat(),
                },
                select="*",
                settings=self.settings,
            )
            if patched:
                claimed.append(self._job_from_supabase(patched[0]))
        return claimed

    def _record_decision_in_supabase(self, create: SmsAgentReplyDecisionCreate) -> SmsAgentReplyDecisionRecord:
        tenant = resolve_tenant(create.business_id, create.environment, settings=self.settings)
        job_row_id = row_id_from_external_id(create.job_id, "smsjob")
        if job_row_id is None:
            raise ValueError("SMS agent job does not exist for tenant")
        existing_job = fetch_rows(
            "sms_agent_jobs",
            params={
                "select": "id",
                "id": f"eq.{job_row_id}",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not existing_job:
            raise ValueError("SMS agent job does not exist for tenant")
        row = insert_rows(
            "sms_agent_decisions",
            [self._decision_payload_for_supabase(create, business_pk=tenant.business_pk, environment=tenant.environment)],
            select="*",
            settings=self.settings,
        )[0]
        return self._decision_from_supabase(row)

    def _list_decisions_in_supabase(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[SmsAgentReplyDecisionRecord]:
        params = {
            "select": "*",
            "order": "created_at.asc,id.asc",
        }
        if business_id is not None and environment is not None:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            params["business_id"] = f"eq.{tenant.business_pk}"
            params["environment"] = f"eq.{tenant.environment}"
        elif business_id is not None:
            if not business_id.isdigit():
                raise ValueError("environment is required when filtering decisions by business_id")
            params["business_id"] = f"eq.{business_id}"
        elif environment is not None:
            params["environment"] = f"eq.{environment}"
        rows = fetch_rows("sms_agent_decisions", params=params, settings=self.settings)
        return [self._decision_from_supabase(row) for row in rows]

    def _record_eval_label_in_supabase(
        self,
        decision_id: str,
        request: SmsAgentEvalLabelRequest,
    ) -> SmsAgentEvalLabelRecord:
        decision_row_id = row_id_from_external_id(decision_id, "smsdec")
        if decision_row_id is None:
            raise ValueError("SMS agent decision does not exist")
        decisions = fetch_rows(
            "sms_agent_decisions",
            params={
                "select": "id,business_id,environment",
                "id": f"eq.{decision_row_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not decisions:
            raise ValueError("SMS agent decision does not exist")
        decision = decisions[0]
        row = insert_rows(
            "sms_agent_eval_labels",
            [
                self._eval_label_payload_for_supabase(
                    request,
                    business_pk=int(decision["business_id"]),
                    environment=str(decision["environment"]),
                    decision_row_id=int(decision["id"]),
                )
            ],
            select="*",
            settings=self.settings,
        )[0]
        return self._eval_label_from_supabase(row)

    def _list_eval_labels_in_supabase(self, *, decision_id: str | None = None) -> list[SmsAgentEvalLabelRecord]:
        params = {
            "select": "*",
            "order": "created_at.asc,id.asc",
        }
        if decision_id is not None:
            decision_row_id = row_id_from_external_id(decision_id, "smsdec")
            if decision_row_id is None:
                return []
            params["decision_id"] = f"eq.{decision_row_id}"
        rows = fetch_rows("sms_agent_eval_labels", params=params, settings=self.settings)
        return [self._eval_label_from_supabase(row) for row in rows]

    def _mark_completed_in_supabase(self, job_id: str, *, decision_id: str | None = None) -> SmsAgentJobRecord | None:
        row_id = row_id_from_external_id(job_id, "smsjob")
        if row_id is None:
            return None
        resolved_decision_id = decision_id
        if resolved_decision_id is None:
            rows = fetch_rows("sms_agent_jobs", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            if not rows:
                return None
            existing = self._job_from_supabase(rows[0])
            resolved_decision_id = existing.decision_id
        if resolved_decision_id is None:
            raise ValueError("decision_id is required to complete SMS agent job")
        decision_row_id = row_id_from_external_id(resolved_decision_id, "smsdec")
        if decision_row_id is None:
            raise ValueError("decision_id is required to complete SMS agent job")
        return self._patch_job_in_supabase(job_id, {"status": "completed", "decision_id": decision_row_id})

    def _mark_failed_in_supabase(
        self,
        job_id: str,
        *,
        retryable: bool,
        error_message: str,
        decision_id: str | None = None,
    ) -> SmsAgentJobRecord | None:
        row = {
            "status": "failed_retryable" if retryable else "failed_terminal",
            "last_error": error_message,
            "locked_until": None,
        }
        if decision_id is not None:
            decision_row_id = row_id_from_external_id(decision_id, "smsdec")
            if decision_row_id is None:
                raise ValueError("decision_id must reference an SMS agent decision")
            row["decision_id"] = decision_row_id
        return self._patch_job_in_supabase(
            job_id,
            row,
        )

    def _patch_job_in_supabase(self, job_id: str, row: dict[str, Any]) -> SmsAgentJobRecord | None:
        row_id = row_id_from_external_id(job_id, "smsjob")
        if row_id is None:
            return None
        patched = patch_rows("sms_agent_jobs", params={"id": f"eq.{row_id}"}, row=row, select="*", settings=self.settings)
        return self._job_from_supabase(patched[0]) if patched else None

    @staticmethod
    def _add_nullable_filter(params: dict[str, str], column: str, value: int | str | None) -> None:
        params[column] = "is.null" if value is None else f"eq.{value}"

    @staticmethod
    def _job_payload_for_supabase(create: SmsAgentJobCreate, *, business_pk: int, environment: str) -> dict[str, Any]:
        payload = create.model_dump(mode="json", exclude={"business_id", "environment"})
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["provider_webhook_id"] = row_id_from_external_id(create.provider_webhook_id, "wh")
        payload["message_id"] = row_id_from_external_id(create.message_id, "msg")
        payload["conversation_id"] = row_id_from_external_id(create.conversation_id, "cnv")
        payload["contact_id"] = row_id_from_external_id(create.contact_id, "ctc")
        return payload

    @staticmethod
    def _decision_payload_for_supabase(create: SmsAgentReplyDecisionCreate, *, business_pk: int, environment: str) -> dict[str, Any]:
        payload = create.model_dump(mode="json", exclude={"business_id", "environment"})
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["job_id"] = row_id_from_external_id(create.job_id, "smsjob")
        payload["message_id"] = row_id_from_external_id(create.message_id, "msg")
        payload["conversation_id"] = row_id_from_external_id(create.conversation_id, "cnv")
        payload["contact_id"] = row_id_from_external_id(create.contact_id, "ctc")
        return payload

    @staticmethod
    def _eval_label_payload_for_supabase(
        request: SmsAgentEvalLabelRequest,
        *,
        business_pk: int,
        environment: str,
        decision_row_id: int,
    ) -> dict[str, Any]:
        payload = request.model_dump(mode="json")
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["decision_id"] = decision_row_id
        return payload

    @staticmethod
    def _job_from_supabase(row: dict[str, Any], *, deduped: bool = False) -> SmsAgentJobRecord:
        payload = {key: value for key, value in dict(row).items() if key in SmsAgentJobRecord.model_fields}
        payload["id"] = external_id("smsjob", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("provider_webhook_id") is not None:
            payload["provider_webhook_id"] = external_id("wh", row["provider_webhook_id"])
        if row.get("message_id") is not None:
            payload["message_id"] = external_id("msg", row["message_id"])
        if row.get("conversation_id") is not None:
            payload["conversation_id"] = external_id("cnv", row["conversation_id"])
        if row.get("contact_id") is not None:
            payload["contact_id"] = external_id("ctc", row["contact_id"])
        if row.get("decision_id") is not None:
            payload["decision_id"] = external_id("smsdec", row["decision_id"])
        payload["deduped"] = deduped or bool(row.get("deduped"))
        SmsAgentRepository._normalize_datetime_fields(payload, ("locked_until", "created_at", "updated_at"))
        return SmsAgentJobRecord.model_validate(payload)

    @staticmethod
    def _decision_from_supabase(row: dict[str, Any]) -> SmsAgentReplyDecisionRecord:
        payload = {key: value for key, value in dict(row).items() if key in SmsAgentReplyDecisionRecord.model_fields}
        payload["id"] = external_id("smsdec", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["job_id"] = external_id("smsjob", row["job_id"])
        if row.get("message_id") is not None:
            payload["message_id"] = external_id("msg", row["message_id"])
        if row.get("conversation_id") is not None:
            payload["conversation_id"] = external_id("cnv", row["conversation_id"])
        if row.get("contact_id") is not None:
            payload["contact_id"] = external_id("ctc", row["contact_id"])
        if isinstance(payload.get("confidence"), str):
            payload["confidence"] = float(payload["confidence"])
        SmsAgentRepository._normalize_datetime_fields(payload, ("created_at",))
        return SmsAgentReplyDecisionRecord.model_validate(payload)

    @staticmethod
    def _eval_label_from_supabase(row: dict[str, Any]) -> SmsAgentEvalLabelRecord:
        payload = {key: value for key, value in dict(row).items() if key in SmsAgentEvalLabelRecord.model_fields}
        payload["id"] = external_id("smslbl", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["decision_id"] = external_id("smsdec", row["decision_id"])
        if payload.get("metadata") is None:
            payload["metadata"] = {}
        SmsAgentRepository._normalize_datetime_fields(payload, ("created_at",))
        return SmsAgentEvalLabelRecord.model_validate(payload)

    @staticmethod
    def _normalize_datetime_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> None:
        for field in fields:
            value = payload.get(field)
            if isinstance(value, str):
                payload[field] = datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _is_duplicate_send_request_error(exc: Exception) -> bool:
        if isinstance(exc, HTTPError):
            if exc.code == 409:
                return True
            try:
                body = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                body = ""
            return "23505" in body or "duplicate key" in body.lower()
        status_code = getattr(exc, "status_code", None)
        if status_code == 409:
            return True
        response = getattr(exc, "response", None)
        if getattr(response, "status_code", None) == 409:
            return True
        text = str(exc)
        return "23505" in text or "duplicate key" in text.lower()
