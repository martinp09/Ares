from __future__ import annotations

import re
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.db.client import utc_now
from app.db.provider_links import ProviderLinksRepository
from app.models.provider_links import ProviderObjectLink
from app.providers.instantly import InstantlyClient

ALLOWED_VERIFICATION_STATUSES = {"valid", "verified", "deliverable"}
SUPPRESSED_RECORD_STATUSES = {"suppressed", "archived"}


class InstantlyEnrollmentService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        provider_links: ProviderLinksRepository | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.provider_links = provider_links

    def preview_enrollment(
        self,
        *,
        records: list[Mapping[str, Any]],
        instantly_campaign_id: str | None = None,
        instantly_list_id: str | None = None,
        campaign_id: str | None = None,
        allow_unverified: bool = False,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        plans = self._build_plans(
            records,
            warnings=warnings,
            allow_unverified=allow_unverified,
            check_links=False,
            business_id=None,
            environment=None,
        )
        if campaign_id and not instantly_campaign_id:
            warnings.append("Internal campaign_id was provided but will not be used as an Instantly provider campaign ID.")
        if not instantly_campaign_id and not instantly_list_id:
            warnings.append("No Instantly campaign/list provider ID was provided; apply will require instantly_campaign_id or instantly_list_id.")
        return self._result_payload(
            dry_run=True,
            live_applied=False,
            target={
                "instantly_campaign_id": instantly_campaign_id,
                "instantly_list_id": instantly_list_id,
                "campaign_id": campaign_id,
            },
            plans=plans,
            warnings=warnings,
            provider_batch_result=None,
            live_enrollment_enabled=self.settings.provider_live_sends_enabled
            and self.settings.instantly_provider_live_enrollment_enabled,
        )

    def apply_enrollment(
        self,
        *,
        business_id: str,
        environment: str,
        records: list[Mapping[str, Any]],
        operator_approval: bool = False,
        instantly_campaign_id: str | None = None,
        instantly_list_id: str | None = None,
        campaign_id: str | None = None,
        allow_unverified: bool = False,
    ) -> dict[str, Any]:
        self._require_live_enrollment_preflight(operator_approval=operator_approval)
        if instantly_campaign_id and instantly_list_id:
            raise RuntimeError("Provide instantly_campaign_id or instantly_list_id, not both.")
        if not instantly_campaign_id and not instantly_list_id:
            raise RuntimeError("Instantly enrollment requires instantly_campaign_id or instantly_list_id; internal campaign_id is not a provider campaign ID.")
        assert self.settings.instantly_api_key
        if self.client is None:
            self.client = InstantlyClient(
                api_key=self.settings.instantly_api_key,
                base_url=self.settings.instantly_base_url,
                batch_size=self.settings.instantly_batch_size,
                batch_wait_seconds=self.settings.instantly_batch_wait_seconds,
            )
        if self.provider_links is None:
            self.provider_links = ProviderLinksRepository(settings=self.settings)

        warnings: list[str] = []
        if campaign_id and not instantly_campaign_id:
            warnings.append("Internal campaign_id was provided but was not used as an Instantly provider campaign ID.")
        plans = self._build_plans(
            records,
            warnings=warnings,
            allow_unverified=allow_unverified,
            check_links=True,
            business_id=business_id,
            environment=environment,
        )
        eligible_plans = [plan for plan in plans if plan["action"] == "enroll"]
        provider_batch_result: Any | None = None
        if eligible_plans:
            leads = [plan["lead"] for plan in eligible_plans]
            try:
                provider_batch_result = self.client.bulk_add_leads(
                    leads,
                    campaign_id=instantly_campaign_id,
                    list_id=instantly_list_id,
                    skip_if_in_workspace=True,
                    skip_if_in_campaign=True,
                    skip_if_in_list=True,
                    verify_leads_on_import=False,
                )
                provider_ids_by_email = self._provider_ids_by_email(provider_batch_result)
                for plan in eligible_plans:
                    email_key = self._email_key(plan["email"])
                    provider_object_id = provider_ids_by_email.get(email_key)
                    if not provider_object_id:
                        plan["action"] = "submitted_unlinked"
                        plan["reason"] = "provider response did not include a per-lead id; provider link was not written"
                        continue
                    link = self.provider_links.upsert_link(
                        ProviderObjectLink(
                            business_id=business_id,
                            environment=environment,
                            provider="instantly",
                            provider_object_type="lead",
                            provider_object_id=provider_object_id,
                            ares_object_type="crm_record",
                            ares_object_id=plan["record_id"],
                            sync_hash=plan.get("sync_hash"),
                            last_synced_at=utc_now(),
                            raw_payload={"source": "instantly_enrollment_apply"},
                        )
                    )
                    plan["provider_object_id"] = provider_object_id
                    plan["provider_link_id"] = link.id
                if any(plan.get("provider_object_id") is None for plan in eligible_plans):
                    warnings.append("One or more Instantly lead IDs were missing from the provider response; provider links were not created for those records.")
            except Exception as exc:  # noqa: BLE001
                safe_error = self._safe_error_message(exc)
                for plan in eligible_plans:
                    plan["action"] = "error"
                    plan["reason"] = safe_error
                provider_batch_result = {"error": safe_error}

        if not eligible_plans:
            warnings.append("No eligible Instantly enrollment records; no provider calls were made.")

        return self._result_payload(
            dry_run=False,
            live_applied=True,
            target={
                "instantly_campaign_id": instantly_campaign_id,
                "instantly_list_id": instantly_list_id,
                "campaign_id": campaign_id,
            },
            plans=plans,
            warnings=warnings,
            provider_batch_result=self._safe_provider_batch_result(provider_batch_result),
            live_enrollment_enabled=self.settings.provider_live_sends_enabled
            and self.settings.instantly_provider_live_enrollment_enabled,
        )

    def _build_plans(
        self,
        records: list[Mapping[str, Any]],
        *,
        warnings: list[str],
        allow_unverified: bool,
        check_links: bool,
        business_id: str | None,
        environment: str | None,
    ) -> list[dict[str, Any]]:
        plans: list[dict[str, Any]] = []
        for record in records:
            normalized = dict(record)
            record_id = str(normalized.get("id") or normalized.get("record_id") or "unknown")
            email = str(normalized.get("email") or "").strip()
            sync_hash = normalized.get("sync_hash")
            base = {
                "record_id": record_id,
                "email": email or None,
                "sync_hash": sync_hash,
                "provider_object_id": None,
                "provider_link_id": None,
            }
            reason = self._exclusion_reason(normalized, allow_unverified=allow_unverified)
            if reason:
                plans.append({**base, "action": "exclude", "reason": reason, "lead": None})
                continue
            if check_links and self.provider_links is not None and business_id and environment:
                existing_link = self.provider_links.get_by_ares_object(
                    business_id=business_id,
                    environment=environment,
                    provider="instantly",
                    ares_object_type="crm_record",
                    ares_object_id=record_id,
                    provider_object_type="lead",
                )
                if existing_link is not None:
                    plans.append(
                        {
                            **base,
                            "action": "skip",
                            "reason": "existing Instantly provider link for crm_record; duplicate enrollment skipped",
                            "provider_object_id": existing_link.provider_object_id,
                            "provider_link_id": existing_link.id,
                            "lead": None,
                        }
                    )
                    continue
            plans.append({**base, "action": "enroll", "reason": "eligible", "lead": self._lead_payload(normalized)})
        if not records:
            warnings.append("No Instantly enrollment records were provided.")
        return plans

    def _exclusion_reason(self, record: Mapping[str, Any], *, allow_unverified: bool) -> str | None:
        if not str(record.get("email") or "").strip():
            return "missing email"
        status = self._record_status(record)
        if status in SUPPRESSED_RECORD_STATUSES:
            return f"record status is {status}"
        verification_status = self._verification_status(record)
        if allow_unverified:
            return None
        if not verification_status:
            return "missing email verification status"
        if verification_status not in ALLOWED_VERIFICATION_STATUSES:
            return f"email verification status is {verification_status}"
        return None

    @staticmethod
    def _record_status(record: Mapping[str, Any]) -> str:
        return str(record.get("status") or record.get("record_status") or "").strip().casefold()

    @staticmethod
    def _verification_status(record: Mapping[str, Any]) -> str:
        value = record.get("verification_status")
        facts = record.get("facts") if isinstance(record.get("facts"), Mapping) else {}
        raw_payload = record.get("raw_payload") if isinstance(record.get("raw_payload"), Mapping) else {}
        value = value or facts.get("email_verification_status") or raw_payload.get("email_verification_status")
        return str(value or "").strip().casefold()

    @staticmethod
    def _lead_payload(record: Mapping[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {"email": str(record.get("email") or "").strip()}
        for source_key, target_key in (("first_name", "first_name"), ("last_name", "last_name"), ("phone", "phone")):
            if record.get(source_key) not in (None, ""):
                payload[target_key] = record.get(source_key)
        if record.get("display_name") not in (None, ""):
            payload["company_name"] = record.get("display_name")
        custom_variables = record.get("custom_variables") if isinstance(record.get("custom_variables"), Mapping) else {}
        if custom_variables:
            payload["custom_variables"] = dict(custom_variables)
        return payload

    def _require_live_enrollment_preflight(self, *, operator_approval: bool) -> None:
        if not operator_approval:
            raise RuntimeError("Instantly enrollment requires explicit operator approval before provider calls.")
        if not self.settings.provider_live_sends_enabled:
            raise RuntimeError("Provider live sends are disabled; set PROVIDER_LIVE_SENDS_ENABLED=true before Instantly enrollment.")
        if not self.settings.instantly_provider_live_enrollment_enabled:
            raise RuntimeError("Instantly live enrollment is disabled; set INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=true before enrollment.")
        if not self.settings.instantly_api_key:
            raise RuntimeError("Instantly API key is required before live enrollment.")

    @staticmethod
    def _provider_ids_by_email(provider_batch_result: Any) -> dict[str, str]:
        ids: dict[str, str] = {}

        def visit(value: Any) -> None:
            if isinstance(value, Mapping):
                email = value.get("email") or value.get("lead_email")
                provider_id = value.get("id") or value.get("lead_id") or value.get("provider_object_id")
                if email and provider_id:
                    ids[InstantlyEnrollmentService._email_key(str(email))] = str(provider_id)
                for nested_key in ("items", "data", "leads", "results", "created", "updated"):
                    if nested_key in value:
                        visit(value[nested_key])
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(provider_batch_result)
        return ids

    @staticmethod
    def _email_key(email: str) -> str:
        return email.strip().casefold()

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        message = f"{exc.__class__.__name__}: {exc}".replace("\n", " ").replace("\r", " ")
        redactions = [
            (r"(?i)(authorization\s*[:=]\s*)bearer\s+[^\s,;]+", r"\1Bearer [redacted]"),
            (r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]"),
            (r"(?i)([?&](?:access_token|token|api[_-]?key|secret|password)=)[^&\s]+", r"\1[redacted]"),
            (r"(?i)\b(token|api[_-]?key|secret|password)\b\s*[:=]\s*[^\s,;]+", r"\1=[redacted]"),
            (r"(?i)(instantly[_-]?api[_-]?key\s*)[^\s,;]+", r"\1[redacted]"),
        ]
        for pattern, replacement in redactions:
            message = re.sub(pattern, replacement, message)
        return message[:240]

    @classmethod
    def _safe_provider_batch_result(cls, provider_batch_result: Any) -> Any:
        if provider_batch_result is None:
            return None
        summary: dict[str, Any] = {
            "type": type(provider_batch_result).__name__,
            "top_level_count_fields": {},
            "top_level_collection_lengths": {},
            "per_lead_id_count": len(cls._provider_ids_by_email(provider_batch_result)),
            "omitted_raw_payload": True,
        }
        if isinstance(provider_batch_result, Mapping):
            for key, value in provider_batch_result.items():
                key_text = str(key)
                if isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)) and re.search(
                    r"(?i)(count|total|created|updated|failed|success|accepted|submitted|skipped)", key_text
                ):
                    summary["top_level_count_fields"][key_text] = value
                elif isinstance(value, (list, tuple)):
                    summary["top_level_collection_lengths"][key_text] = len(value)
        elif isinstance(provider_batch_result, (list, tuple)):
            summary["top_level_collection_lengths"]["items"] = len(provider_batch_result)
        return summary

    @staticmethod
    def _result_payload(
        *,
        dry_run: bool,
        live_applied: bool,
        target: dict[str, Any],
        plans: list[dict[str, Any]],
        warnings: list[str],
        provider_batch_result: Any | None,
        live_enrollment_enabled: bool,
    ) -> dict[str, Any]:
        results = [
            {
                key: value
                for key, value in {
                    "record_id": plan["record_id"],
                    "email": plan.get("email"),
                    "action": plan["action"],
                    "reason": plan.get("reason"),
                    "provider_object_id": plan.get("provider_object_id"),
                    "provider_link_id": plan.get("provider_link_id"),
                    "sync_hash": plan.get("sync_hash"),
                }.items()
                if value is not None
            }
            for plan in plans
        ]
        confirmed_enrolled_count = sum(
            1 for result in results if result["action"] == "enroll" and result.get("provider_object_id")
        )
        submitted_unlinked_count = sum(1 for result in results if result["action"] == "submitted_unlinked")
        eligible_count = sum(1 for result in results if result["action"] in {"enroll", "submitted_unlinked", "error"})
        submitted_count = confirmed_enrolled_count + submitted_unlinked_count if live_applied else 0
        skipped_count = sum(1 for result in results if result["action"] == "skip")
        excluded_count = sum(1 for result in results if result["action"] == "exclude")
        error_count = sum(1 for result in results if result["action"] == "error")
        return {
            "provider": "instantly",
            "dry_run": dry_run,
            "live_applied": live_applied,
            "would_call_provider": (not dry_run) and provider_batch_result is not None,
            "live_enrollment_enabled": live_enrollment_enabled,
            "eligible_count": eligible_count,
            "submitted_count": submitted_count,
            "enrolled_count": confirmed_enrolled_count if live_applied else 0,
            "skipped_count": skipped_count,
            "excluded_count": excluded_count,
            "error_count": error_count,
            "target": target,
            "results": results,
            "warnings": warnings,
            "provider_batch_result": provider_batch_result,
        }
