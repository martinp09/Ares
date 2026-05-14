from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.db.client import utc_now
from app.db.provider_links import ProviderLinksRepository
from app.models.provider_links import ProviderObjectLink
from app.providers.hubspot import HubSpotClient

HUBSPOT_OBJECT_TYPES = ("contacts", "deals", "companies")

PROPERTY_GROUP_PAYLOAD = {
    "name": "ares_information",
    "label": "Ares Information",
    "displayOrder": 50,
}

CONTACT_PROPERTY_NAMES = [
    "ares_contact_id",
    "ares_record_id",
    "ares_source_lane",
    "ares_contact_role",
    "ares_contact_address",
    "ares_property_address",
    "ares_contact_status",
    "ares_skiptrace_status",
    "ares_email_verification_status",
    "ares_phone_verification_status",
    "ares_mailing_address",
    "ares_probate_case_number",
    "ares_decedent_name",
    "ares_estate_name",
    "ares_best_contact_name",
    "ares_best_contact_role",
    "ares_best_contact_address",
    "ares_heir_candidate_count",
    "ares_heir_candidates_summary",
    "ares_heir_status",
    "ares_heir_confidence",
    "ares_heir_next_gate",
    "ares_priority_tier",
    "ares_last_outreach_channel",
    "ares_last_outreach_at",
    "ares_next_best_action",
    "ares_last_agent_summary",
]

DEAL_PROPERTY_NAMES = [
    "ares_opportunity_id",
    "ares_primary_record_id",
    "ares_property_address",
    "ares_mailing_address",
    "ares_county",
    "ares_hcad_account",
    "ares_hctax_account",
    "ares_hcad_owner_names",
    "ares_source_lane",
    "ares_source_run_id",
    "ares_lead_temperature",
    "ares_lead_score",
    "ares_tax_delinquency_status",
    "ares_tax_overlay_status",
    "ares_tax_overlay_query",
    "ares_tax_overlay_candidate_hit_count",
    "ares_title_complexity",
    "ares_occupancy_hint",
    "ares_equity_hint",
    "ares_probate_case_number",
    "ares_probate_court_number",
    "ares_probate_file_date",
    "ares_probate_status",
    "ares_probate_filing_type",
    "ares_probate_filing_subtype",
    "ares_estate_name",
    "ares_decedent_name",
    "ares_best_contact_name",
    "ares_best_contact_role",
    "ares_best_contact_address",
    "ares_heir_candidate_count",
    "ares_heir_candidates_summary",
    "ares_heir_status",
    "ares_heir_confidence",
    "ares_heir_next_gate",
    "ares_party_count",
    "ares_event_count",
    "ares_priority_tier",
    "ares_priority_flags",
    "ares_skiptrace_status",
    "ares_outreach_status",
    "ares_instantly_campaign_id",
    "ares_vapi_last_call_status",
    "ares_vapi_last_call_outcome",
    "ares_next_best_action",
    "ares_last_agent_summary",
    "ares_sync_hash",
]

COMPANY_PROPERTY_NAMES = [
    "ares_entity_id",
    "ares_entity_role",
    "ares_source_lane",
    "ares_mailing_address",
    "ares_probate_case_number",
    "ares_decedent_name",
    "ares_last_agent_summary",
]

NUMBER_PROPERTY_NAMES = {
    "ares_lead_score",
    "ares_heir_candidate_count",
    "ares_tax_overlay_candidate_hit_count",
    "ares_party_count",
    "ares_event_count",
}

TEXTAREA_PROPERTY_NAMES = {
    "ares_contact_address",
    "ares_mailing_address",
    "ares_property_address",
    "ares_hcad_owner_names",
    "ares_tax_overlay_query",
    "ares_best_contact_address",
    "ares_heir_candidates_summary",
    "ares_heir_next_gate",
    "ares_priority_flags",
    "ares_next_best_action",
    "ares_last_agent_summary",
}

PIPELINE_STAGE_LABELS = [
    "New Lead",
    "Data QC",
    "Needs Skiptrace",
    "Contact Ready",
    "Outreach Queued",
    "Outreach Active",
    "Engaged",
    "Appointment Set",
    "Offer / Title Review",
    "Contracting",
    "Closed Won",
    "Closed Lost / Dead",
]


def _label_for_property(name: str) -> str:
    return name.removeprefix("ares_").replace("_", " ").title()


def _property_payload(name: str, *, field_type: str = "text", property_type: str = "string") -> dict[str, Any]:
    return {
        "name": name,
        "label": _label_for_property(name),
        "type": property_type,
        "fieldType": field_type,
        "groupName": PROPERTY_GROUP_PAYLOAD["name"],
    }


def _typed_property_payload(name: str) -> dict[str, Any]:
    if name in NUMBER_PROPERTY_NAMES:
        return _property_payload(name, field_type="number", property_type="number")
    if name in TEXTAREA_PROPERTY_NAMES:
        return _property_payload(name, field_type="textarea", property_type="string")
    return _property_payload(name)


def _deal_stage_id(label: str) -> str:
    return label.lower().replace(" / ", "_").replace(" ", "_").replace("/", "_").replace("-", "_")


def _pipeline_payload() -> dict[str, Any]:
    return {
        "label": "Ares Acquisitions",
        "displayOrder": 0,
        "stages": [
            {
                "label": label,
                "displayOrder": index,
                "metadata": {
                    "probability": "1.0" if label == "Closed Won" else "0.0" if label == "Closed Lost / Dead" else "0.2",
                    "isClosed": "true" if label in {"Closed Won", "Closed Lost / Dead"} else "false",
                },
                "stageId": _deal_stage_id(label),
            }
            for index, label in enumerate(PIPELINE_STAGE_LABELS)
        ],
    }


class HubSpotMirrorService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: HubSpotClient | None = None,
        provider_links: ProviderLinksRepository | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.provider_links = provider_links

    def build_customization_preview(self, *, dry_run: bool = True) -> dict[str, Any]:
        if not dry_run:
            self._require_live_write_preflight()
            raise RuntimeError("HubSpot live apply is not implemented in Phase 1; use dry_run=true.")
        payloads = self._customization_payloads()
        return {
            "provider": "hubspot",
            "dry_run": dry_run,
            "would_call_provider": False,
            "live_write_enabled": self.settings.provider_live_sends_enabled and self.settings.hubspot_provider_live_writes_enabled,
            "payloads": payloads,
            "warnings": [],
        }

    def apply_customization(self, *, operator_approval: bool = False) -> dict[str, Any]:
        self._require_live_write_preflight(operator_approval=operator_approval)
        assert self.client is not None
        payloads = self._customization_payloads()
        property_groups_created: dict[str, list[dict[str, Any]]] = {object_type: [] for object_type in HUBSPOT_OBJECT_TYPES}
        property_groups_skipped: dict[str, list[dict[str, Any]]] = {object_type: [] for object_type in HUBSPOT_OBJECT_TYPES}
        properties_created: dict[str, list[dict[str, Any]]] = {object_type: [] for object_type in HUBSPOT_OBJECT_TYPES}
        properties_skipped: dict[str, list[dict[str, Any]]] = {object_type: [] for object_type in HUBSPOT_OBJECT_TYPES}
        mutation_count = 0
        warnings: list[str] = []

        for object_type in HUBSPOT_OBJECT_TYPES:
            existing_group_names = self._names_from_results(self.client.list_property_groups(object_type))
            for group_payload in payloads["property_groups"][object_type]:
                if group_payload["name"] in existing_group_names:
                    property_groups_skipped[object_type].append({"name": group_payload["name"]})
                    continue
                created = self.client.create_property_group(object_type, group_payload)
                property_groups_created[object_type].append(self._created_summary(group_payload, created))
                mutation_count += 1

            existing_property_names = self._names_from_results(self.client.list_properties(object_type))
            for property_payload in payloads["properties"][object_type]:
                if property_payload["name"] in existing_property_names:
                    properties_skipped[object_type].append({"name": property_payload["name"]})
                    continue
                created = self.client.create_property(object_type, property_payload)
                properties_created[object_type].append(self._created_summary(property_payload, created))
                mutation_count += 1

        pipeline_payload = payloads["pipelines"]["deals"][0]
        pipeline_result = self._apply_deal_pipeline(pipeline_payload)
        mutation_count += pipeline_result.pop("mutation_count")
        warnings.extend(pipeline_result.pop("warnings", []))

        return {
            "provider": "hubspot",
            "live_applied": True,
            "property_groups_created": property_groups_created,
            "property_groups_skipped": property_groups_skipped,
            "properties_created": properties_created,
            "properties_skipped": properties_skipped,
            **pipeline_result,
            "mutation_count": mutation_count,
            "warnings": warnings,
        }

    def build_record_sync_preview(self, records: list[Mapping[str, Any]], *, dry_run: bool = True) -> dict[str, Any]:
        if not dry_run:
            self._require_live_write_preflight()
            raise RuntimeError("HubSpot live record sync requires /mission-control/providers/hubspot/records/apply-sync with operator approval.")
        payloads, warnings = self._record_sync_payloads(records)
        return {
            "provider": "hubspot",
            "dry_run": dry_run,
            "would_call_provider": False,
            "live_write_enabled": self.settings.provider_live_sends_enabled and self.settings.hubspot_provider_live_writes_enabled,
            "payloads": payloads,
            "warnings": warnings,
        }

    def apply_record_sync(
        self,
        *,
        business_id: str,
        environment: str,
        records: list[Mapping[str, Any]],
        operator_approval: bool = False,
    ) -> dict[str, Any]:
        self._require_live_write_preflight(operator_approval=operator_approval)
        assert self.client is not None
        if self.provider_links is None:
            self.provider_links = ProviderLinksRepository(settings=self.settings)

        warnings: list[str] = []
        results: list[dict[str, Any]] = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0

        plans = self._record_sync_plans(records, warnings)
        if not plans:
            warnings.append("No HubSpot record sync items were provided; no provider calls were made.")

        for plan in plans:
            record = plan["record"]
            record_id = str(record.get("id") or record.get("record_id") or "unknown")
            object_type = plan["provider_object_type"]
            ares_object_type = plan["ares_object_type"]
            ares_object_id = plan["ares_object_id"]
            sync_hash = record.get("sync_hash")
            base_result = {
                "record_id": record_id,
                "object_type": object_type,
                "ares_object_type": ares_object_type,
                "ares_object_id": ares_object_id,
                "sync_hash": sync_hash,
            }
            payload = plan["payload"]
            if not payload.get("properties"):
                skipped_count += 1
                results.append({**base_result, "action": "skip", "error": "No HubSpot properties could be built for record."})
                continue
            try:
                existing_link = self.provider_links.get_by_ares_object(
                    business_id=business_id,
                    environment=environment,
                    provider="hubspot",
                    ares_object_type=ares_object_type,
                    ares_object_id=ares_object_id,
                    provider_object_type=object_type,
                )
                if existing_link is not None:
                    if sync_hash not in (None, "") and str(existing_link.sync_hash or "") == str(sync_hash):
                        skipped_count += 1
                        results.append(
                            {
                                **base_result,
                                "action": "skip",
                                "provider_object_id": existing_link.provider_object_id,
                                "provider_link_id": existing_link.id,
                            }
                        )
                        continue
                    self.client.update_object(plan["client_object_type"], existing_link.provider_object_id, payload)
                    updated_link = self.provider_links.upsert_link(
                        existing_link.model_copy(update={"sync_hash": sync_hash, "last_synced_at": utc_now()})
                    )
                    updated_count += 1
                    results.append(
                        {
                            **base_result,
                            "action": "update",
                            "provider_object_id": updated_link.provider_object_id,
                            "provider_link_id": updated_link.id,
                        }
                    )
                    continue

                created = self.client.create_object(plan["client_object_type"], payload)
                provider_object_id = self._provider_object_id(created)
                if not provider_object_id:
                    failed_count += 1
                    results.append({**base_result, "action": "skip", "error": "HubSpot create response did not include id or hs_object_id."})
                    continue
                link = self.provider_links.upsert_link(
                    ProviderObjectLink(
                        business_id=business_id,
                        environment=environment,
                        provider="hubspot",
                        provider_object_type=object_type,
                        provider_object_id=provider_object_id,
                        ares_object_type=ares_object_type,
                        ares_object_id=ares_object_id,
                        sync_hash=sync_hash,
                        last_synced_at=utc_now(),
                        raw_payload={"source": "hubspot_record_apply_sync"},
                    )
                )
                created_count += 1
                results.append(
                    {
                        **base_result,
                        "action": "create",
                        "provider_object_id": provider_object_id,
                        "provider_link_id": link.id,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                failed_count += 1
                results.append({**base_result, "action": "skip", "error": self._safe_error_message(exc)})

        return {
            "provider": "hubspot",
            "live_applied": True,
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "error_count": failed_count,
            "results": results,
            "warnings": warnings,
        }

    def _record_sync_payloads(self, records: list[Mapping[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
        warnings: list[str] = []
        payloads = {"contacts": [], "deals": [], "companies": []}
        for plan in self._record_sync_plans(records, warnings):
            payloads[plan["client_object_type"]].append(plan["payload"])
        return payloads, warnings

    def _record_sync_plans(self, records: list[Mapping[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
        plans: list[dict[str, Any]] = []
        for record in records:
            normalized = dict(record)
            record_id = str(normalized.get("id") or normalized.get("record_id") or "unknown")
            record_type = str(normalized.get("record_type") or "contact_record")
            if record_type != "entity_record" and not normalized.get("email") and not normalized.get("phone"):
                warnings.append(f"Record {record_id} has no email or phone for HubSpot contact matching.")
            if record_type == "entity_record":
                plans.append(
                    {
                        "record": normalized,
                        "client_object_type": "companies",
                        "provider_object_type": "company",
                        "ares_object_type": "crm_record",
                        "ares_object_id": record_id,
                        "payload": self._company_payload(normalized),
                    }
                )
            else:
                plans.append(
                    {
                        "record": normalized,
                        "client_object_type": "contacts",
                        "provider_object_type": "contact",
                        "ares_object_type": "crm_record",
                        "ares_object_id": record_id,
                        "payload": self._contact_payload(normalized),
                    }
                )
            deal_ares_object_type = "opportunity" if normalized.get("opportunity_id") else "crm_record"
            deal_ares_object_id = str(normalized.get("opportunity_id") or record_id)
            plans.append(
                {
                    "record": normalized,
                    "client_object_type": "deals",
                    "provider_object_type": "deal",
                    "ares_object_type": deal_ares_object_type,
                    "ares_object_id": deal_ares_object_id,
                    "payload": self._deal_payload(normalized),
                }
            )
        return plans

    @staticmethod
    def _provider_object_id(response: Mapping[str, Any]) -> str | None:
        identifier = response.get("id") or response.get("hs_object_id")
        properties = response.get("properties") if isinstance(response.get("properties"), Mapping) else {}
        identifier = identifier or properties.get("hs_object_id")
        return str(identifier) if identifier not in (None, "") else None

    @staticmethod
    def _safe_error_message(exc: Exception) -> str:
        message = f"{exc.__class__.__name__}: {exc}".replace("\n", " ").replace("\r", " ")
        redactions = [
            (r"(?i)(authorization\s*[:=]\s*)bearer\s+[^\s,;]+", r"\1Bearer [redacted]"),
            (r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [redacted]"),
            (r"(?i)([?&](?:access_token|token|api[_-]?key|secret|password)=)[^&\s]+", r"\1[redacted]"),
            (r"(?i)\b(token|api[_-]?key|secret|password)\b\s*[:=]\s*[^\s,;]+", r"\1=[redacted]"),
        ]
        for pattern, replacement in redactions:
            message = re.sub(pattern, replacement, message)
        return message[:240]

    def _customization_payloads(self) -> dict[str, Any]:
        return {
            "property_groups": {
                "contacts": [dict(PROPERTY_GROUP_PAYLOAD)],
                "deals": [dict(PROPERTY_GROUP_PAYLOAD)],
                "companies": [dict(PROPERTY_GROUP_PAYLOAD)],
            },
            "properties": {
                "contacts": [_typed_property_payload(name) for name in CONTACT_PROPERTY_NAMES],
                "deals": [_typed_property_payload(name) for name in DEAL_PROPERTY_NAMES],
                "companies": [_typed_property_payload(name) for name in COMPANY_PROPERTY_NAMES],
            },
            "pipelines": {
                "deals": [_pipeline_payload()],
            },
        }

    def _apply_deal_pipeline(self, pipeline_payload: Mapping[str, Any]) -> dict[str, Any]:
        assert self.client is not None
        existing_pipelines = self._results(self.client.list_pipelines("deals"))
        existing_pipeline = next(
            (pipeline for pipeline in existing_pipelines if pipeline.get("label") == pipeline_payload["label"]),
            None,
        )
        warnings: list[str] = []
        if existing_pipeline is None and len(existing_pipelines) == 1:
            existing_pipeline = existing_pipelines[0]
            warnings.append(
                "HubSpot portal already has its maximum deal-pipeline count; reused the existing deal pipeline and added missing Ares stages."
            )
        if existing_pipeline is None:
            created_pipeline = self.client.create_pipeline("deals", pipeline_payload)
            stage_summaries = [
                self._created_summary(stage_payload, self._matching_stage_response(created_pipeline, stage_payload))
                for stage_payload in pipeline_payload.get("stages", [])
            ]
            return {
                "pipeline_created": self._created_summary(pipeline_payload, created_pipeline),
                "pipeline_existing": None,
                "stages_created": stage_summaries,
                "stages_skipped": [],
                "mutation_count": 1,
                "warnings": warnings,
            }

        pipeline_id = str(existing_pipeline.get("id") or existing_pipeline.get("pipelineId") or pipeline_payload["label"])
        existing_stage_labels = {str(stage.get("label")) for stage in existing_pipeline.get("stages", []) if stage.get("label")}
        stages_created: list[dict[str, Any]] = []
        stages_skipped: list[dict[str, Any]] = []
        mutation_count = 0
        for stage_payload in pipeline_payload.get("stages", []):
            if stage_payload["label"] in existing_stage_labels:
                stages_skipped.append({"label": stage_payload["label"], "id": self._stage_id_by_label(existing_pipeline, stage_payload["label"])})
                continue
            created = self.client.create_pipeline_stage("deals", pipeline_id, stage_payload)
            stages_created.append(self._created_summary(stage_payload, created))
            mutation_count += 1
        return {
            "pipeline_created": None,
            "pipeline_existing": {"label": existing_pipeline.get("label"), "id": pipeline_id},
            "stages_created": stages_created,
            "stages_skipped": stages_skipped,
            "mutation_count": mutation_count,
            "warnings": warnings,
        }

    def _contact_payload(self, record: Mapping[str, Any]) -> dict[str, Any]:
        first_name, last_name = self._split_name(str(record.get("display_name") or record.get("owner_name") or "Unknown Contact"))
        properties = {
            "firstname": first_name,
            "lastname": last_name,
            "email": record.get("email"),
            "phone": record.get("phone"),
            "ares_contact_id": record.get("contact_id"),
            "ares_record_id": record.get("id") or record.get("record_id"),
            "ares_source_lane": record.get("source_lane") or record.get("source"),
            "ares_contact_role": record.get("contact_role") or record.get("best_contact_role") or record.get("applicant_role"),
            "ares_contact_address": record.get("contact_address") or record.get("best_contact_address") or record.get("applicant_address"),
            "ares_property_address": record.get("property_address"),
            "ares_contact_status": record.get("record_status") or record.get("status"),
            "ares_skiptrace_status": record.get("skiptrace_status"),
            "ares_mailing_address": record.get("mailing_address") or record.get("best_contact_address") or record.get("applicant_address"),
            "ares_probate_case_number": record.get("probate_case_number"),
            "ares_decedent_name": record.get("decedent_name") or record.get("owner_name"),
            "ares_estate_name": record.get("estate_name"),
            "ares_best_contact_name": record.get("best_contact_name") or record.get("applicant_name") or record.get("display_name"),
            "ares_best_contact_role": record.get("best_contact_role") or record.get("applicant_role"),
            "ares_best_contact_address": record.get("best_contact_address") or record.get("applicant_address"),
            "ares_heir_candidate_count": record.get("heir_candidate_count"),
            "ares_heir_candidates_summary": record.get("heir_candidates_summary"),
            "ares_heir_status": record.get("heir_status"),
            "ares_heir_confidence": record.get("heir_confidence"),
            "ares_heir_next_gate": record.get("heir_next_gate"),
            "ares_priority_tier": record.get("priority_tier"),
            "ares_next_best_action": record.get("next_best_action"),
            "ares_last_agent_summary": record.get("last_agent_summary"),
            "hubspot_owner_id": self.settings.hubspot_owner_id,
        }
        return {"properties": self._compact(properties)}

    def _deal_payload(self, record: Mapping[str, Any]) -> dict[str, Any]:
        lead_score = record.get("lead_score")
        if lead_score is None:
            lead_score = record.get("data_quality_score")
        properties = {
            "dealname": record.get("deal_name") or record.get("property_address") or record.get("display_name") or "Ares Opportunity",
            "pipeline": record.get("hubspot_pipeline_id") or self.settings.hubspot_default_pipeline_id,
            "dealstage": record.get("hubspot_deal_stage_id") or self.settings.hubspot_default_deal_stage_id,
            "hubspot_owner_id": self.settings.hubspot_owner_id,
            "ares_opportunity_id": record.get("opportunity_id"),
            "ares_primary_record_id": record.get("id") or record.get("record_id"),
            "ares_property_address": record.get("property_address"),
            "ares_mailing_address": record.get("mailing_address") or record.get("best_contact_address") or record.get("applicant_address"),
            "ares_county": record.get("county"),
            "ares_hcad_account": record.get("hcad_account"),
            "ares_hctax_account": record.get("hctax_account"),
            "ares_hcad_owner_names": record.get("hcad_owner_names"),
            "ares_source_lane": record.get("source_lane") or record.get("source"),
            "ares_source_run_id": record.get("source_run_id"),
            "ares_lead_temperature": record.get("lead_temperature"),
            "ares_lead_score": lead_score,
            "ares_tax_delinquency_status": record.get("tax_delinquency_status"),
            "ares_tax_overlay_status": record.get("tax_overlay_status"),
            "ares_tax_overlay_query": record.get("tax_overlay_query"),
            "ares_tax_overlay_candidate_hit_count": record.get("tax_overlay_candidate_hit_count"),
            "ares_title_complexity": record.get("title_complexity"),
            "ares_occupancy_hint": record.get("occupancy_hint"),
            "ares_equity_hint": record.get("equity_hint"),
            "ares_probate_case_number": record.get("probate_case_number"),
            "ares_probate_court_number": record.get("probate_court_number") or record.get("court_number"),
            "ares_probate_file_date": record.get("probate_file_date") or record.get("file_date"),
            "ares_probate_status": record.get("probate_status"),
            "ares_probate_filing_type": record.get("probate_filing_type") or record.get("filing_type"),
            "ares_probate_filing_subtype": record.get("probate_filing_subtype") or record.get("filing_subtype"),
            "ares_estate_name": record.get("estate_name"),
            "ares_decedent_name": record.get("decedent_name") or record.get("owner_name"),
            "ares_best_contact_name": record.get("best_contact_name") or record.get("applicant_name"),
            "ares_best_contact_role": record.get("best_contact_role") or record.get("applicant_role"),
            "ares_best_contact_address": record.get("best_contact_address") or record.get("applicant_address"),
            "ares_heir_candidate_count": record.get("heir_candidate_count"),
            "ares_heir_candidates_summary": record.get("heir_candidates_summary"),
            "ares_heir_status": record.get("heir_status"),
            "ares_heir_confidence": record.get("heir_confidence"),
            "ares_heir_next_gate": record.get("heir_next_gate"),
            "ares_party_count": record.get("party_count"),
            "ares_event_count": record.get("event_count"),
            "ares_priority_tier": record.get("priority_tier"),
            "ares_priority_flags": record.get("priority_flags"),
            "ares_skiptrace_status": record.get("skiptrace_status"),
            "ares_outreach_status": record.get("outreach_status"),
            "ares_instantly_campaign_id": record.get("campaign_id"),
            "ares_next_best_action": record.get("next_best_action"),
            "ares_last_agent_summary": record.get("last_agent_summary"),
            "ares_sync_hash": record.get("sync_hash"),
        }
        return {"properties": self._compact(properties)}

    def _company_payload(self, record: Mapping[str, Any]) -> dict[str, Any]:
        properties = {
            "name": record.get("entity_name") or record.get("display_name") or record.get("owner_name"),
            "ares_entity_id": record.get("entity_id") or record.get("id") or record.get("record_id"),
            "ares_entity_role": record.get("entity_role") or record.get("record_type"),
            "ares_source_lane": record.get("source_lane") or record.get("source"),
            "ares_mailing_address": record.get("mailing_address"),
            "ares_probate_case_number": record.get("probate_case_number"),
            "ares_decedent_name": record.get("decedent_name"),
            "ares_last_agent_summary": record.get("last_agent_summary"),
            "hubspot_owner_id": self.settings.hubspot_owner_id,
        }
        return {"properties": self._compact(properties)}

    def _require_live_write_preflight(self, *, operator_approval: bool | None = None) -> None:
        if operator_approval is False:
            raise RuntimeError("Explicit operator approval is required before HubSpot live writes/record sync.")
        if not self.settings.provider_live_sends_enabled:
            raise RuntimeError("Provider live sends are disabled; set PROVIDER_LIVE_SENDS_ENABLED=true before any mutation.")
        if not self.settings.hubspot_provider_live_writes_enabled:
            raise RuntimeError("HubSpot live writes are disabled; set HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true before any mutation.")
        if not self.settings.hubspot_access_token:
            raise RuntimeError("HubSpot access token is required before any live provider mutation.")
        if self.client is None:
            self.client = HubSpotClient(
                access_token=self.settings.hubspot_access_token,
                base_url=self.settings.hubspot_base_url,
                timeout_seconds=self.settings.provider_request_timeout_seconds,
            )

    @staticmethod
    def _split_name(name: str) -> tuple[str, str]:
        parts = [part for part in name.strip().split(" ") if part]
        if not parts:
            return "Unknown", "Contact"
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    @classmethod
    def _compact(cls, properties: Mapping[str, Any]) -> dict[str, Any]:
        compacted: dict[str, Any] = {}
        for key, value in properties.items():
            normalized = cls._hubspot_property_value(value)
            if normalized in (None, ""):
                continue
            compacted[key] = normalized
        return compacted

    @staticmethod
    def _hubspot_property_value(value: Any) -> Any:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return "; ".join(str(item) for item in value if item not in (None, ""))
        return value

    @staticmethod
    def _results(response: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        results = response.get("results", [])
        return results if isinstance(results, list) else []

    @classmethod
    def _names_from_results(cls, response: Mapping[str, Any]) -> set[str]:
        return {str(item.get("name")) for item in cls._results(response) if item.get("name")}

    @staticmethod
    def _created_summary(payload: Mapping[str, Any], response: Mapping[str, Any] | None) -> dict[str, Any]:
        response = response or {}
        summary = {"name": payload.get("name"), "label": payload.get("label")}
        identifier = response.get("id") or response.get("name") or response.get("stageId")
        if identifier:
            summary["id"] = identifier
        if response.get("stageId"):
            summary["stageId"] = response.get("stageId")
        return {key: value for key, value in summary.items() if value is not None}

    @staticmethod
    def _stage_id_by_label(pipeline: Mapping[str, Any], label: str) -> str | None:
        for stage in pipeline.get("stages", []) or []:
            if stage.get("label") == label:
                return stage.get("id") or stage.get("stageId")
        return None

    @staticmethod
    def _matching_stage_response(pipeline: Mapping[str, Any], stage_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        for stage in pipeline.get("stages", []) or []:
            if stage.get("label") == stage_payload.get("label"):
                return stage
        return stage_payload
