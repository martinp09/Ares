from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.models.crm_records import CrmRecord, CrmRecordStatus
from app.models.hubspot_crm import (
    HubSpotCustomizationRequest,
    HubSpotPipelineSpec,
    HubSpotPipelineStageSpec,
    HubSpotPropertyDefinition,
    HubSpotPropertyOption,
    HubSpotProviderActionResponse,
    HubSpotRecordSyncRequest,
)
from app.providers.textgrid import normalize_phone_number
from app.services.providers.hubspot import HubSpotProviderClient

CONTACT_ROLE_OPTIONS = [
    ("Owner", "owner"),
    ("Heir / family", "heir"),
    ("Executor / administrator", "executor"),
    ("Probate applicant", "applicant"),
    ("Attorney / legal rep", "attorney"),
    ("Tenant / occupant", "tenant"),
    ("Buyer", "buyer"),
    ("Vendor", "vendor"),
    ("Wrong number", "wrong_number"),
    ("Unknown", "unknown"),
]
SOURCE_LANE_OPTIONS = [
    ("Curative title", "curative_title"),
    ("Outbound probate", "outbound_probate"),
    ("Inbound lease option", "inbound_lease_option"),
    ("Seller direct", "seller_direct"),
    ("Buyer inquiry", "buyer_inquiry"),
    ("Vendor", "vendor"),
    ("Unknown", "unknown"),
]
OPERATOR_LANE_OPTIONS = [
    ("A - pull docs first", "a_pull_docs_first"),
    ("B - review docs second", "b_review_docs_second"),
    ("C - identity / property-type review", "c_identity_or_property_type_review"),
    ("D - backup / out of band", "d_backup_low_tax_or_out_of_band"),
    ("Keep now", "keep_now"),
    ("Needs skiptrace", "needs_skiptrace"),
    ("Contact ready", "contact_ready"),
    ("Unknown", "unknown"),
]
SKIPTRACE_OPTIONS = [
    ("Not needed", "not_needed"),
    ("Needs skiptrace", "needs_skiptrace"),
    ("Skiptraced", "skiptraced"),
    ("Bad number", "bad_number"),
    ("Do not skiptrace", "do_not_skiptrace"),
]
DOC_PULL_OPTIONS = [
    ("Not started", "not_started"),
    ("Needed", "needed"),
    ("In progress", "in_progress"),
    ("Verified", "verified"),
    ("Blocked", "blocked"),
]


class HubSpotCrmService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        hubspot_client: HubSpotProviderClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.hubspot_client = hubspot_client or HubSpotProviderClient(settings=self.settings)

    def configure_crm(self, request: HubSpotCustomizationRequest) -> HubSpotProviderActionResponse:
        property_defs = build_ares_hubspot_property_definitions() if request.include_properties else []
        pipeline_spec = build_ares_hubspot_pipeline() if request.include_deal_pipeline else None
        request_payload: dict[str, Any] = {
            "business_id": request.business_id,
            "environment": request.environment,
            "operator_approval": request.operator_approval,
            "properties": [definition.model_dump() for definition in property_defs],
            "deal_pipeline": pipeline_spec.model_dump() if pipeline_spec else None,
            "hubspot_docs_reference": {
                "objects": "/crm/v3/objects/{objectType}",
                "properties": "/crm/v3/properties/{objectType}",
                "pipelines": "/crm/v3/pipelines/{objectType}",
            },
        }
        missing = self._missing_live_config()
        dry_run = request.dry_run_only or not self._live_writes_enabled()
        if dry_run:
            return HubSpotProviderActionResponse(
                action="configure_hubspot_crm",
                status="skipped",
                dry_run=True,
                request_payload=request_payload,
                missing_config=missing,
                notes=[
                    "Dry-run only: no HubSpot portal properties, pipelines, contacts, or deals were changed.",
                    "The developer key is not used for CRM bearer requests; use a private-app/personal access token in HUBSPOT_ACCESS_TOKEN or HUBSPOT_PERSONAL_KEY.",
                ],
            )
        self._require_operator_approval(request.operator_approval)
        if missing:
            raise RuntimeError(f"Missing HubSpot live config: {', '.join(missing)}")

        property_results = [
            self.hubspot_client.upsert_property(definition.object_type, definition.name, definition.hubspot_payload())
            for definition in property_defs
        ]
        pipeline_result = None
        if pipeline_spec:
            pipeline_result = self.hubspot_client.upsert_pipeline_by_label(pipeline_spec.object_type, pipeline_spec.hubspot_payload())
        return HubSpotProviderActionResponse(
            action="configure_hubspot_crm",
            status="applied",
            dry_run=False,
            request_payload=request_payload,
            provider_response={"properties": property_results, "deal_pipeline": pipeline_result},
        )

    def sync_record(self, request: HubSpotRecordSyncRequest) -> HubSpotProviderActionResponse:
        contact_properties = build_contact_properties(request.record)
        deal_properties = build_deal_properties(request.record, request=request, settings=self.settings)
        request_payload = {
            "contact": {"object_type": "contacts", "properties": contact_properties} if request.create_contact else None,
            "deal": {"object_type": "deals", "properties": deal_properties} if request.create_deal else None,
            "associations": {
                "planned": bool(request.create_contact and request.create_deal),
                "note": "Ares prepares contact/deal payloads first; live association IDs are a follow-up gate after portal schema is confirmed.",
            },
            "metadata": {"ares_hubspot_sync": True, **request.metadata},
            "operator_approval": request.operator_approval,
        }
        missing = self._missing_live_config()
        dry_run = request.dry_run_only or not self._live_writes_enabled()
        if dry_run:
            return HubSpotProviderActionResponse(
                action="sync_hubspot_record",
                status="skipped",
                dry_run=True,
                request_payload=request_payload,
                missing_config=missing,
                notes=["Dry-run only: no HubSpot contact, deal, or association was changed."],
            )
        self._require_operator_approval(request.operator_approval)
        if missing:
            raise RuntimeError(f"Missing HubSpot live config: {', '.join(missing)}")

        provider_response: dict[str, Any] = {}
        if request.create_contact:
            lookup_property, lookup_value = _contact_lookup(contact_properties)
            provider_response["contact"] = self.hubspot_client.upsert_object_by_property(
                "contacts",
                lookup_property=lookup_property,
                lookup_value=lookup_value,
                properties=contact_properties,
            )
        if request.create_deal:
            lookup_value = _required_string(deal_properties.get("ares_external_key"), "ares_external_key")
            provider_response["deal"] = self.hubspot_client.upsert_object_by_property(
                "deals",
                lookup_property="ares_external_key",
                lookup_value=lookup_value,
                properties=deal_properties,
            )
        return HubSpotProviderActionResponse(
            action="sync_hubspot_record",
            status="synced",
            dry_run=False,
            request_payload=request_payload,
            provider_response=provider_response,
        )

    def _live_writes_enabled(self) -> bool:
        return bool(self.settings.provider_live_sends_enabled and self.settings.hubspot_provider_live_writes_enabled)

    def _missing_live_config(self) -> list[str]:
        missing = []
        if not self.settings.hubspot_access_token:
            missing.append("HUBSPOT_ACCESS_TOKEN or HUBSPOT_PERSONAL_KEY")
        if not self.settings.provider_live_sends_enabled:
            missing.append("PROVIDER_LIVE_SENDS_ENABLED=true")
        if not self.settings.hubspot_provider_live_writes_enabled:
            missing.append("HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true")
        return missing

    @staticmethod
    def _require_operator_approval(operator_approval: bool) -> None:
        if operator_approval is not True:
            raise RuntimeError("HubSpot live writes require operator_approval=true")


def build_ares_hubspot_property_definitions() -> list[HubSpotPropertyDefinition]:
    definitions = [
        _contact_property("ares_role", "Ares role", "select", "enumeration", "How this person fits the real-estate thread.", CONTACT_ROLE_OPTIONS, 10),
        _contact_property("ares_source_lane", "Ares source lane", "select", "enumeration", "Ares acquisition or marketing lane.", SOURCE_LANE_OPTIONS, 20),
        _contact_property("ares_record_status", "Ares record status", "select", "enumeration", "Current Ares CRM record state.", [(status.value.replace("_", " ").title(), status.value) for status in CrmRecordStatus], 30),
        _contact_property("ares_skiptrace_status", "Ares skiptrace status", "select", "enumeration", "Whether phone/email enrichment is needed or completed.", SKIPTRACE_OPTIONS, 40),
        _contact_property("ares_follow_up_permission", "Ares follow-up permission", "booleancheckbox", "bool", "True only when the contact consented to follow-up.", [], 50),
        _contact_property("ares_contact_confidence", "Ares contact confidence", "number", "number", "0-100 confidence that this is the right living contact.", [], 60),
        _deal_property("ares_external_key", "Ares external key", "text", "string", "Deterministic Ares source/record key for idempotent sync.", [], 10),
        _deal_property("ares_source_lane", "Ares source lane", "select", "enumeration", "Ares lane such as curative title, probate outbound, or lease-option inbound.", SOURCE_LANE_OPTIONS, 20),
        _deal_property("ares_operator_lane", "Ares operator lane", "select", "enumeration", "Operator queue lane for document pull, review, or contact readiness.", OPERATOR_LANE_OPTIONS, 30),
        _deal_property("ares_property_address", "Ares property address", "text", "string", "Subject property address.", [], 40),
        _deal_property("ares_mailing_address", "Ares mailing address", "text", "string", "Owner/contact mailing address.", [], 50),
        _deal_property("ares_county", "Ares county", "text", "string", "County source for the record.", [], 60),
        _deal_property("ares_hctax_account", "Ares HCTax account", "text", "string", "Harris County tax account or equivalent county account number.", [], 70),
        _deal_property("ares_probate_case_number", "Ares probate case number", "text", "string", "Probate case number when known.", [], 80),
        _deal_property("ares_estimated_value", "Ares estimated value", "number", "number", "County/appraised/estimated value used for triage.", [], 90),
        _deal_property("ares_delinquent_tax_amount", "Ares delinquent tax amount", "number", "number", "Verified delinquent tax amount due.", [], 100),
        _deal_property("ares_delinquent_years", "Ares delinquent years", "number", "number", "Count of delinquent tax years.", [], 110),
        _deal_property("ares_debt_to_value_pct", "Ares debt/value %", "number", "number", "Tax debt divided by estimated value as a percentage.", [], 120),
        _deal_property("ares_title_flags", "Ares title flags", "textarea", "string", "Comma-separated title/probate/tax caution flags.", [], 130),
        _deal_property("ares_document_pull_status", "Ares document pull status", "select", "enumeration", "Status of deed/probate/tax document authority checks.", DOC_PULL_OPTIONS, 140),
        _deal_property("ares_next_action", "Ares next action", "textarea", "string", "Concrete operator next step before outreach or offer work.", [], 150),
    ]
    return definitions


def build_ares_hubspot_pipeline() -> HubSpotPipelineSpec:
    stages = [
        ("Research / title packet", "research_title_packet", 0, 0.05, False, False),
        ("Needs skiptrace", "needs_skiptrace", 1, 0.10, False, False),
        ("Contact ready", "contact_ready", 2, 0.20, False, False),
        ("Reached / qualifying", "reached_qualifying", 3, 0.30, False, False),
        ("Seller or heir interested", "seller_heir_interested", 4, 0.45, False, False),
        ("Title / legal review", "title_legal_review", 5, 0.55, False, False),
        ("Offer drafted", "offer_drafted", 6, 0.65, False, False),
        ("Under contract", "under_contract", 7, 0.85, False, False),
        ("Closed won", "closed_won", 8, 1.00, True, False),
        ("Closed lost / suppressed", "closed_lost_suppressed", 9, 0.00, False, True),
    ]
    return HubSpotPipelineSpec(
        stages=[
            HubSpotPipelineStageSpec(
                label=label,
                stage_id=stage_id,
                displayOrder=display_order,
                probability=probability,
                closed_won=closed_won,
                closed_lost=closed_lost,
            )
            for label, stage_id, display_order, probability, closed_won, closed_lost in stages
        ]
    )


def build_contact_properties(record: CrmRecord) -> dict[str, Any]:
    first_name, last_name = _split_name(record.owner_name or record.display_name)
    properties: dict[str, Any] = {
        "firstname": first_name,
        "lastname": last_name,
        "lifecyclestage": "lead",
        "ares_role": _first_text(record.facts, "contact_role", "role", default="unknown"),
        "ares_source_lane": _source_lane(record),
        "ares_record_status": record.status.value,
        "ares_skiptrace_status": _skiptrace_status(record),
    }
    if record.email:
        properties["email"] = record.email.strip()
    if record.phone:
        properties["phone"] = normalize_phone_number(record.phone)
    confidence = _first_number(record.facts, "contact_confidence", "confidence", "heir_confidence")
    if confidence is not None:
        properties["ares_contact_confidence"] = confidence
    follow_up = _first_bool(record.facts, "follow_up_permission", "consent_to_follow_up", "sms_consent_confirmed")
    if follow_up is not None:
        properties["ares_follow_up_permission"] = follow_up
    return {key: value for key, value in properties.items() if value not in (None, "")}


def build_deal_properties(record: CrmRecord, *, request: HubSpotRecordSyncRequest, settings: Settings) -> dict[str, Any]:
    external_key = record.identity_key or record.resolved_identity_key()
    deal_name = request.deal_name or _deal_name(record)
    properties: dict[str, Any] = {
        "dealname": deal_name,
        "ares_external_key": external_key,
        "ares_source_lane": _source_lane(record),
        "ares_operator_lane": _operator_lane(record),
        "ares_property_address": record.property_address,
        "ares_mailing_address": record.mailing_address,
        "ares_county": _first_text(record.facts, "county", default=None),
        "ares_hctax_account": _first_text(record.facts, "hctax_account", "tax_account", "account", default=None),
        "ares_probate_case_number": _first_text(record.facts, "probate_case_number", "case_number", default=None),
        "ares_estimated_value": _first_number(record.facts, "market_value", "estimated_value", "appraised_value", "value"),
        "ares_delinquent_tax_amount": _first_number(record.facts, "total_amount_due", "tax_due", "delinquent_tax_amount"),
        "ares_delinquent_years": _first_number(record.facts, "delinquent_years", "tax_year_count"),
        "ares_debt_to_value_pct": _first_number(record.facts, "debt_to_value_pct", "tax_debt_to_value_pct"),
        "ares_title_flags": _title_flags(record),
        "ares_document_pull_status": _first_text(record.facts, "document_pull_status", "doc_pull_status", default="needed"),
        "ares_next_action": _first_text(record.facts, "next_action", "operator_next_step", "why_now", default=None),
    }
    pipeline_id = request.pipeline_id or settings.hubspot_default_pipeline_id
    deal_stage = request.deal_stage or settings.hubspot_default_deal_stage_id
    owner_id = request.owner_id or settings.hubspot_owner_id
    if pipeline_id:
        properties["pipeline"] = pipeline_id
    if deal_stage:
        properties["dealstage"] = deal_stage
    if owner_id:
        properties["hubspot_owner_id"] = owner_id
    return {key: value for key, value in properties.items() if value not in (None, "")}


def _contact_property(
    name: str,
    label: str,
    field_type: str,
    property_type: str,
    description: str,
    options: list[tuple[str, str]],
    display_order: int,
) -> HubSpotPropertyDefinition:
    return _property("contacts", "contactinformation", name, label, field_type, property_type, description, options, display_order)


def _deal_property(
    name: str,
    label: str,
    field_type: str,
    property_type: str,
    description: str,
    options: list[tuple[str, str]],
    display_order: int,
) -> HubSpotPropertyDefinition:
    return _property("deals", "dealinformation", name, label, field_type, property_type, description, options, display_order)


def _property(
    object_type: str,
    group_name: str,
    name: str,
    label: str,
    field_type: str,
    property_type: str,
    description: str,
    options: list[tuple[str, str]],
    display_order: int,
) -> HubSpotPropertyDefinition:
    return HubSpotPropertyDefinition(
        object_type=object_type,  # type: ignore[arg-type]
        name=name,
        label=label,
        type=property_type,  # type: ignore[arg-type]
        fieldType=field_type,  # type: ignore[arg-type]
        groupName=group_name,
        description=description,
        displayOrder=display_order,
        options=[
            HubSpotPropertyOption(label=option_label, value=value, displayOrder=index, hidden=False)
            for index, (option_label, value) in enumerate(options)
        ],
    )


def _contact_lookup(properties: dict[str, Any]) -> tuple[str, str]:
    if properties.get("email"):
        return "email", str(properties["email"])
    if properties.get("phone"):
        return "phone", str(properties["phone"])
    raise RuntimeError("HubSpot contact sync requires email or phone")


def _required_string(value: Any, field_name: str) -> str:
    if value is None or str(value).strip() == "":
        raise RuntimeError(f"HubSpot deal sync requires {field_name}")
    return str(value)


def _deal_name(record: CrmRecord) -> str:
    if record.property_address and (record.owner_name or record.display_name):
        return f"{record.owner_name or record.display_name} - {record.property_address}"
    return record.display_name


def _split_name(name: str | None) -> tuple[str, str]:
    cleaned = str(name or "Unknown").strip()
    if not cleaned:
        return "Unknown", "Contact"
    parts = cleaned.split()
    if len(parts) == 1:
        return parts[0], "Contact"
    return " ".join(parts[:-1]), parts[-1]


def _source_lane(record: CrmRecord) -> str:
    return _first_text(record.facts, "source_lane", "lane", default=None) or _source_lane_from_record(record)


def _source_lane_from_record(record: CrmRecord) -> str:
    source = _first_text(record.raw_payload, "source", "source_lane", default="unknown") or "unknown"
    normalized = source.strip().lower().replace("-", "_").replace(" ", "_")
    if "lease" in normalized:
        return "inbound_lease_option"
    if "probate" in normalized:
        return "outbound_probate"
    if "curative" in normalized or "title" in normalized:
        return "curative_title"
    if normalized in {value for _, value in SOURCE_LANE_OPTIONS}:
        return normalized
    return "unknown"


def _operator_lane(record: CrmRecord) -> str:
    lane = _first_text(record.facts, "operator_lane", "crm_stage", "lane", default=None)
    if lane:
        return lane.strip().lower().replace(" ", "_")
    if record.status == CrmRecordStatus.NEEDS_SKIP_TRACE:
        return "needs_skiptrace"
    if record.status in {CrmRecordStatus.MARKETABLE, CrmRecordStatus.CLEAN}:
        return "contact_ready"
    return "unknown"


def _skiptrace_status(record: CrmRecord) -> str:
    explicit = _first_text(record.facts, "skiptrace_status", "contact_unlock_status", default=None)
    if explicit:
        return explicit.strip().lower().replace(" ", "_")
    if record.status == CrmRecordStatus.SUPPRESSED:
        return "do_not_skiptrace"
    if record.status == CrmRecordStatus.NEEDS_SKIP_TRACE or not (record.phone or record.email):
        return "needs_skiptrace"
    return "not_needed"


def _title_flags(record: CrmRecord) -> str | None:
    flags = record.facts.get("title_flags") or record.facts.get("flags")
    if isinstance(flags, list):
        return ", ".join(str(flag) for flag in flags if str(flag).strip()) or None
    if flags is not None:
        return str(flags)
    return None


def _first_text(payload: dict[str, Any], *keys: str, default: str | None = "unknown") -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    custom = payload.get("custom_variables")
    if isinstance(custom, dict):
        for key in keys:
            value = custom.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    return default


def _first_number(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        number = _number(value)
        if number is not None:
            return number
    custom = payload.get("custom_variables")
    if isinstance(custom, dict):
        for key in keys:
            number = _number(custom.get(key))
            if number is not None:
                return number
    return None


def _first_bool(payload: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        value = payload.get(key)
        parsed = _bool(value)
        if parsed is not None:
            return parsed
    custom = payload.get("custom_variables")
    if isinstance(custom, dict):
        for key in keys:
            parsed = _bool(custom.get(key))
            if parsed is not None:
                return parsed
    return None


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None
