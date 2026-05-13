from __future__ import annotations

import json
from typing import Any

from app.core.config import Settings, get_settings
from app.models.crm_records import CrmRecordStatus
from app.models.mission_control import (
    MissionControlOpportunityStageMoveRequest,
    MissionControlRecordPromotionRequest,
    MissionControlRecordStatusRequest,
    MissionControlRecordSuppressionRequest,
)
from app.models.voice_agents import (
    VapiWebhookResponse,
    VoiceAssistantCreateRequest,
    VoiceOutboundCallRequest,
    VoicePhoneNumberCreateRequest,
    VoiceProviderActionResponse,
)
from app.providers.textgrid import normalize_phone_number
from app.services.mission_control_service import mission_control_service as default_mission_control_service
from app.services.providers.vapi import VapiProviderClient

VOICE_ACTOR_ID = "vapi_voice_agent"
VOICE_ACTOR_TYPE = "voice_agent"

ARES_REAL_ESTATE_SYSTEM_PROMPT = """You are the Ares real estate voice agent for an operator-led distressed real-estate CRM.

Ares reference:
- Ares is the self-hosted operating system for distressed real-estate lead management.
- Mission Control is the operator cockpit for records, tasks, opportunities, pipelines, and stage movement.
- probate outbound / curative-title outreach is one lane. lease-option inbound marketing is another lane. Do not merge these lanes.
- Records, tasks, and opportunities should be created as operator-review work, not automatic legal or financial decisions.

Primary job:
1. Pull Ares context before asking repeated questions when a phone number, record id, opportunity id, thread id, or property address is available.
2. Identify whether the caller is an owner, heir, tenant, buyer, vendor, wrong number, or unknown.
3. Classify the source lane: outbound_probate, inbound_lease_option, curative_title, seller_direct, buyer_inquiry, vendor, wrong_number, or unknown.
4. Collect enough context for a human operator: name, phone, property address, role/authority, reason for calling, timeline, motivation, condition, occupancy, volunteered liens/taxes/probate/title issues, and consent to follow up.
5. If the caller wants to sell or discuss terms, qualify the lead and create or update Mission Control work.
6. If the caller needs legal/tax advice, is upset, or mentions an attorney/court deadline, request human handoff.

Conversation rules:
- Keep each spoken turn under 35 words unless summarizing.
- Ask one question at a time.
- Be calm, direct, and respectful, especially around probate or family situations.
- Never claim you are an attorney, broker, lender, or tax advisor.
- Never give legal, tax, financial, or valuation advice.
- Never promise an offer, approval, closing date, or outcome.
- Confirm the best callback number and permission before follow-up.
- End with a concise summary of what will happen next.

Tool rules:
- Use search_ares_leads when the caller gives a phone, email, name, record id, lead id, contact id, or property address.
- Use get_ares_record_detail when you need current Ares record, task, opportunity, inbox, or lead-machine context.
- Use get_ares_call_script before sensitive probate, curative-title, or lease-option turns if lane-specific wording helps.
- Use update_ares_record only after identity and follow-up intent are clear.
- Use move_ares_opportunity_stage only when the stage change is supported by the call.
- Use complete_ares_task only after enough call information has been gathered.
- Use request_human_handoff for urgent, legal-sensitive, angry, ambiguous, or high-value calls."""

COMMON_GUARDRAILS = [
    "Do not give legal, tax, valuation, or brokerage advice.",
    "Do not promise an offer, closing date, approval, or outcome.",
    "Confirm permission before any follow-up.",
    "Escalate probate disputes, attorney involvement, court deadlines, threats, or angry callers to a human.",
]


class VoiceAgentService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        vapi_client: VapiProviderClient | None = None,
        mission_control_service: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.vapi_client = vapi_client or VapiProviderClient(settings=self.settings)
        self.mission_control_service = mission_control_service or default_mission_control_service

    def create_assistant(self, request: VoiceAssistantCreateRequest) -> VoiceProviderActionResponse:
        payload = self.build_assistant_payload(
            name=request.name,
            first_message=request.first_message,
            system_prompt=request.system_prompt,
            server_url=request.server_url,
            model_provider=request.model_provider,
            model=request.model,
            voice_provider=request.voice_provider,
            voice_id=request.voice_id,
            metadata=request.metadata,
        )
        if request.dry_run_only or not self._vapi_config_changes_enabled():
            return VoiceProviderActionResponse(
                action="create_assistant",
                status="skipped",
                dry_run=True,
                request_payload=payload,
            )
        response = self.vapi_client.create_assistant(payload)
        return VoiceProviderActionResponse(
            action="create_assistant",
            status="created",
            dry_run=False,
            provider_id=_extract_vapi_id(response),
            request_payload=payload,
            provider_response=response,
        )

    def create_phone_number(self, request: VoicePhoneNumberCreateRequest) -> VoiceProviderActionResponse:
        payload: dict[str, Any] = {
            "provider": "vapi",
            "name": request.name,
        }
        assistant_id = request.assistant_id or self.settings.vapi_default_assistant_id
        if assistant_id:
            payload["assistantId"] = assistant_id
        if request.number_desired_area_code:
            payload["numberDesiredAreaCode"] = request.number_desired_area_code
        server_url = request.server_url or self.settings.vapi_webhook_url
        if server_url:
            payload["server"] = {"url": server_url}

        if request.dry_run_only or not self._vapi_config_changes_enabled():
            return VoiceProviderActionResponse(
                action="create_phone_number",
                status="skipped",
                dry_run=True,
                request_payload=payload,
            )
        response = self.vapi_client.create_phone_number(payload)
        return VoiceProviderActionResponse(
            action="create_phone_number",
            status="created",
            dry_run=False,
            provider_id=_extract_vapi_id(response),
            request_payload=payload,
            provider_response=response,
        )

    def create_outbound_call(self, request: VoiceOutboundCallRequest) -> VoiceProviderActionResponse:
        assistant_id = request.assistant_id or self.settings.vapi_default_assistant_id
        phone_number_id = request.phone_number_id or self.settings.vapi_default_phone_number_id
        payload: dict[str, Any] = {
            "customer": {"number": normalize_phone_number(request.to)},
            "metadata": {"ares_voice_agent": True, **request.metadata},
        }
        if assistant_id:
            payload["assistantId"] = assistant_id
        else:
            payload["assistant"] = self.build_assistant_payload(
                first_message=request.first_message or "Hi, this is Ares. I’m calling about your property request.",
                system_prompt=request.system_prompt,
            )
        if phone_number_id:
            payload["phoneNumberId"] = phone_number_id
        if request.earliest_at:
            payload["schedulePlan"] = {"earliestAt": request.earliest_at}
            if request.latest_at:
                payload["schedulePlan"]["latestAt"] = request.latest_at

        if request.dry_run_only or not self._outbound_calls_enabled():
            return VoiceProviderActionResponse(
                action="create_outbound_call",
                status="skipped",
                dry_run=True,
                request_payload=payload,
            )
        if "phoneNumberId" not in payload:
            raise RuntimeError("VAPI_DEFAULT_PHONE_NUMBER_ID or phone_number_id is required for outbound calls")
        response = self.vapi_client.create_call(payload)
        return VoiceProviderActionResponse(
            action="create_outbound_call",
            status="queued",
            dry_run=False,
            provider_id=_extract_vapi_id(response),
            request_payload=payload,
            provider_response=response,
        )

    def handle_webhook(self, payload: dict[str, Any]) -> VapiWebhookResponse:
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict):
            return VapiWebhookResponse(status="accepted", event_type="unknown")
        message_type = str(message.get("type") or "unknown")
        if message_type == "assistant-request":
            if self.settings.vapi_default_assistant_id:
                return VapiWebhookResponse(assistantId=self.settings.vapi_default_assistant_id)
            assistant = self.build_assistant_payload()
            return VapiWebhookResponse(assistant=assistant)
        if message_type == "tool-calls":
            tool_calls = message.get("toolCallList") or message.get("toolCalls") or []
            results: list[dict[str, Any]] = []
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue
                    tool_call_id = str(tool_call.get("id") or tool_call.get("toolCallId") or "")
                    name = str(tool_call.get("name") or tool_call.get("function", {}).get("name") or "unknown")
                    parameters = _tool_call_parameters(tool_call)
                    try:
                        tool_result = self._handle_tool_call(name, parameters)
                    except Exception as exc:
                        tool_result = {"status": "error", "message": str(exc), "tool": name}
                    results.append(
                        {
                            "name": name,
                            "toolCallId": tool_call_id,
                            "result": json.dumps(tool_result, default=str),
                        }
                    )
            return VapiWebhookResponse(results=results)
        return VapiWebhookResponse(status="accepted", event_type=message_type)

    def build_assistant_payload(
        self,
        *,
        name: str = "Ares Voice Agent",
        first_message: str = "Hi, this is Ares. How can I help?",
        system_prompt: str | None = None,
        server_url: str | None = None,
        model_provider: str | None = None,
        model: str | None = None,
        voice_provider: str | None = None,
        voice_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "firstMessage": first_message,
            "model": {
                "provider": model_provider or self.settings.vapi_default_model_provider,
                "model": model or self.settings.vapi_default_model,
                "messages": [{"role": "system", "content": system_prompt or ARES_REAL_ESTATE_SYSTEM_PROMPT}],
                "tools": self._build_tools(),
            },
            "voice": {
                "provider": voice_provider or self.settings.vapi_default_voice_provider,
                "voiceId": voice_id or self.settings.vapi_default_voice_id,
            },
        }
        active_server_url = server_url or self.settings.vapi_webhook_url
        if active_server_url:
            payload["server"] = {"url": active_server_url}
        if metadata:
            payload["metadata"] = metadata
        return payload

    def _handle_tool_call(self, name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if name == "search_ares_leads":
            return self._search_ares_leads(parameters)
        if name == "get_ares_record_detail":
            return self._get_ares_record_detail(parameters)
        if name == "get_ares_call_script":
            return self._get_ares_call_script(parameters)
        if name == "update_ares_record":
            return self._update_ares_record(parameters)
        if name == "move_ares_opportunity_stage":
            return self._move_ares_opportunity_stage(parameters)
        if name == "complete_ares_task":
            return self._complete_ares_task(parameters)
        if name == "qualify_real_estate_lead":
            return self._qualify_real_estate_lead(parameters)
        if name == "create_operator_task":
            return {"status": "prepared", "task": parameters, "visible_in_mission_control": True}
        if name == "prepare_follow_up_summary":
            return {"status": "prepared", "summary": parameters}
        if name == "request_human_handoff":
            return {"status": "handoff_requested", "handoff": parameters, "visible_in_mission_control": True}
        return {"status": "unsupported", "message": "Tool not wired in Ares yet"}

    def _search_ares_leads(self, parameters: dict[str, Any]) -> dict[str, Any]:
        records_response = self.mission_control_service.get_records(**self._mission_control_scope())
        records = _extract_list(records_response, "records")
        matches = [_jsonable(record) for record in records if _record_matches(record, parameters)]
        limit = int(parameters.get("limit") or 5)
        lead_machine = self.mission_control_service.get_lead_machine(
            **self._mission_control_scope(),
            lead_id=_clean(parameters.get("leadId") or parameters.get("lead_id")),
            limit=limit,
        )
        return {
            "status": "found" if matches else "not_found",
            "matches": matches[:limit],
            "lead_machine": _jsonable(lead_machine),
            "searched": {key: value for key, value in parameters.items() if value not in (None, "")},
        }

    def _get_ares_record_detail(self, parameters: dict[str, Any]) -> dict[str, Any]:
        records_response = self.mission_control_service.get_records(**self._mission_control_scope())
        records = _extract_list(records_response, "records")
        record = next((record for record in records if _record_matches(record, parameters)), None)
        opportunities = self.mission_control_service.get_opportunities(**self._mission_control_scope())
        tasks = self.mission_control_service.get_tasks(**self._mission_control_scope())
        inbox = self.mission_control_service.get_inbox(
            **self._mission_control_scope(),
            selected_thread_id=_clean(parameters.get("threadId") or parameters.get("thread_id")),
        )
        lead_machine = self.mission_control_service.get_lead_machine(
            **self._mission_control_scope(),
            lead_id=_clean(parameters.get("leadId") or parameters.get("lead_id")),
            limit=int(parameters.get("limit") or 10),
        )
        return {
            "status": "found" if record is not None else "not_found",
            "record": _jsonable(record) if record is not None else None,
            "opportunities": _jsonable(opportunities),
            "tasks": _jsonable(tasks),
            "inbox": _jsonable(inbox),
            "lead_machine": _jsonable(lead_machine),
        }

    def _get_ares_call_script(self, parameters: dict[str, Any]) -> dict[str, Any]:
        source_lane = str(parameters.get("sourceLane") or parameters.get("source_lane") or "unknown")
        situation = str(parameters.get("situation") or "initial_qualification")
        script = CALL_SCRIPTS.get(source_lane, CALL_SCRIPTS["unknown"])
        opening = script["opening"].get(situation) or script["opening"]["initial_qualification"]
        return {
            "status": "ready",
            "source_lane": source_lane,
            "situation": situation,
            "opening": opening,
            "questions": script["questions"],
            "next_steps": script["next_steps"],
            "guardrails": COMMON_GUARDRAILS,
        }

    def _update_ares_record(self, parameters: dict[str, Any]) -> dict[str, Any]:
        record_id = _require(parameters, "recordId", "record_id")
        action = str(parameters.get("action") or "status")
        if action == "suppress":
            result = self.mission_control_service.suppress_record(
                record_id,
                MissionControlRecordSuppressionRequest(reason=str(parameters.get("reason") or "Suppressed by voice agent")),
                actor_id=VOICE_ACTOR_ID,
                actor_type=VOICE_ACTOR_TYPE,
            )
        elif action == "promote":
            result = self.mission_control_service.promote_record(
                record_id,
                MissionControlRecordPromotionRequest(
                    source_lane=str(parameters.get("sourceLane") or parameters.get("source_lane") or "seller_direct"),
                    lead_id=_clean(parameters.get("leadId") or parameters.get("lead_id")),
                    contact_id=_clean(parameters.get("contactId") or parameters.get("contact_id")),
                    strategy_lane=_clean(parameters.get("strategyLane") or parameters.get("strategy_lane")),
                    reason=_clean(parameters.get("reason")),
                    metadata=parameters.get("metadata") if isinstance(parameters.get("metadata"), dict) else {},
                ),
                actor_id=VOICE_ACTOR_ID,
                actor_type=VOICE_ACTOR_TYPE,
            )
        else:
            result = self.mission_control_service.update_record_status(
                record_id,
                MissionControlRecordStatusRequest(
                    status=CrmRecordStatus(str(parameters.get("status") or "marketable")),
                    reason=_clean(parameters.get("reason")) or "Updated by voice agent",
                ),
                actor_id=VOICE_ACTOR_ID,
                actor_type=VOICE_ACTOR_TYPE,
            )
        return {"status": "updated", "result": _jsonable(result)}

    def _move_ares_opportunity_stage(self, parameters: dict[str, Any]) -> dict[str, Any]:
        opportunity_id = _require(parameters, "opportunityId", "opportunity_id")
        result = self.mission_control_service.move_opportunity_stage(
            opportunity_id,
            MissionControlOpportunityStageMoveRequest(
                stage=str(parameters.get("stage")),
                reason=_clean(parameters.get("reason")),
                metadata=parameters.get("metadata") if isinstance(parameters.get("metadata"), dict) else {},
            ),
            actor_id=VOICE_ACTOR_ID,
            actor_type=VOICE_ACTOR_TYPE,
        )
        return {"status": "updated", "result": _jsonable(result)}

    def _complete_ares_task(self, parameters: dict[str, Any]) -> dict[str, Any]:
        result = self.mission_control_service.complete_task_for_thread(
            thread_id=_require(parameters, "threadId", "thread_id"),
            org_id=self.settings.default_org_id,
            notes=_clean(parameters.get("notes")),
            follow_up_outcome=_clean(parameters.get("followUpOutcome") or parameters.get("follow_up_outcome")),
        )
        return {"status": "completed", "result": _jsonable(result)}

    def _qualify_real_estate_lead(self, parameters: dict[str, Any]) -> dict[str, Any]:
        source_lane = _classify_source_lane(parameters)
        score = _score_lead(parameters)
        return {
            "status": "qualified",
            "visible_in_mission_control": True,
            "source_lane": source_lane,
            "score": score,
            "crm_record": {
                "display_name": _clean(parameters.get("callerName") or parameters.get("caller_name")) or "Unknown caller",
                "phone": _clean(parameters.get("phone")),
                "email": _clean(parameters.get("email")),
                "property_address": _clean(parameters.get("propertyAddress") or parameters.get("property_address")),
                "source_lane": source_lane,
            },
        }

    def _mission_control_scope(self) -> dict[str, str]:
        return {
            "org_id": self.settings.default_org_id,
            "business_id": "1",
            "environment": "prod",
        }

    def _build_tools(self) -> list[dict[str, Any]]:
        return _build_vapi_tools()

    def _vapi_config_changes_enabled(self) -> bool:
        return self.settings.provider_live_sends_enabled and self.settings.vapi_provider_live_sends_enabled

    def _outbound_calls_enabled(self) -> bool:
        return self._vapi_config_changes_enabled()


def _extract_vapi_id(response: dict[str, Any]) -> str | None:
    value = response.get("id") or response.get("assistantId") or response.get("phoneNumberId") or response.get("callId")
    return str(value) if value is not None else None


def _build_vapi_tools() -> list[dict[str, Any]]:
    return [
        _function_tool(
            "search_ares_leads",
            "Search Ares Mission Control records and lead-machine context by record id, lead id, phone, email, name, or property address.",
            {
                "recordId": _string_schema("Ares CRM record id, if known."),
                "leadId": _string_schema("Ares source lead id, if known."),
                "contactId": _string_schema("Ares source contact id, if known."),
                "phone": _string_schema("Phone number to search."),
                "email": _string_schema("Email address to search."),
                "name": _string_schema("Caller, owner, or lead name to search."),
                "propertyAddress": _string_schema("Property address or partial address to search."),
                "limit": {"type": "number", "description": "Maximum matching records to return."},
            },
        ),
        _function_tool(
            "get_ares_record_detail",
            "Pull fuller Ares context for a record, lead, opportunity, thread, phone, name, or property address.",
            {
                "recordId": _string_schema("Ares CRM record id."),
                "leadId": _string_schema("Ares source lead id."),
                "contactId": _string_schema("Ares contact id."),
                "opportunityId": _string_schema("Ares opportunity id."),
                "threadId": _string_schema("Mission Control thread id."),
                "phone": _string_schema("Phone number."),
                "name": _string_schema("Caller, owner, or lead name."),
                "propertyAddress": _string_schema("Property address or partial address."),
                "limit": {"type": "number", "description": "Maximum lead-machine records to include."},
            },
        ),
        _function_tool(
            "get_ares_call_script",
            "Retrieve lane-specific Ares call scripts, questions, next steps, and compliance guardrails.",
            {
                "sourceLane": {
                    "type": "string",
                    "enum": [
                        "outbound_probate",
                        "inbound_lease_option",
                        "curative_title",
                        "seller_direct",
                        "buyer_inquiry",
                        "vendor",
                        "wrong_number",
                        "unknown",
                    ],
                    "description": "Ares source lane.",
                },
                "situation": {
                    "type": "string",
                    "enum": ["initial_qualification", "callback", "objection", "closing_summary"],
                    "description": "Call situation.",
                },
            },
            required=["sourceLane"],
        ),
        _function_tool(
            "update_ares_record",
            "Update an Ares CRM record through Mission Control status, suppress, or promote endpoints.",
            {
                "recordId": _string_schema("Ares CRM record id to update."),
                "action": {"type": "string", "enum": ["status", "suppress", "promote"], "description": "Update action."},
                "status": {
                    "type": "string",
                    "enum": ["new", "incomplete", "clean", "needs_skip_trace", "marketable", "suppressed", "promoted", "archived"],
                    "description": "Target record status for action=status.",
                },
                "reason": _string_schema("Reason for the change."),
                "sourceLane": _string_schema("Source lane for promotion."),
                "leadId": _string_schema("Source lead id for promotion."),
                "contactId": _string_schema("Source contact id for promotion."),
                "strategyLane": _string_schema("Strategy lane for promotion."),
                "metadata": {"type": "object", "description": "Additional update metadata."},
            },
            required=["recordId", "action"],
        ),
        _function_tool(
            "move_ares_opportunity_stage",
            "Move an Ares opportunity to a new pipeline stage using the Mission Control stage movement endpoint.",
            {
                "opportunityId": _string_schema("Ares opportunity id."),
                "stage": _string_schema("Target Ares pipeline stage."),
                "reason": _string_schema("Reason for movement."),
                "metadata": {"type": "object", "description": "Additional stage movement metadata."},
            },
            required=["opportunityId", "stage"],
        ),
        _function_tool(
            "complete_ares_task",
            "Complete a Mission Control task/thread after enough call information has been gathered.",
            {
                "threadId": _string_schema("Mission Control thread id."),
                "notes": _string_schema("Completion notes."),
                "followUpOutcome": _string_schema("Follow-up outcome, if applicable."),
            },
            required=["threadId"],
        ),
        _function_tool(
            "qualify_real_estate_lead",
            "Create an Ares-style qualification snapshot for a real estate caller or outbound lead.",
            {
                "callerName": _string_schema("Caller or lead name, if known."),
                "phone": _string_schema("Best phone number for follow-up, if known."),
                "email": _string_schema("Email address, if volunteered."),
                "propertyAddress": _string_schema("Property address or area being discussed."),
                "intent": _string_schema("Caller intent or reason for the call."),
                "timeline": _string_schema("Timeline to sell, resolve title, move, lease-option, or follow up."),
                "motivation": _string_schema("Motivation or pain point in the caller's own words."),
                "authority": _string_schema("Caller authority: owner, heir, spouse, tenant, agent, neighbor, vendor, unknown."),
                "propertyCondition": _string_schema("Property condition, occupancy, repair, vacancy, or title context."),
                "sourceHint": _string_schema("Known source hint such as probate, lease option, tax delinquency, website, SMS, cold call."),
                "consentToFollowUp": {"type": "boolean", "description": "Whether the caller gave permission for follow-up."},
            },
            required=["intent"],
        ),
        _function_tool(
            "create_operator_task",
            "Prepare the next Mission Control operator task for follow-up, review, callback, or suppression.",
            {
                "taskType": {"type": "string", "enum": ["callback", "manual_review", "send_follow_up", "suppress", "research", "handoff"]},
                "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                "summary": _string_schema("Short task summary for Mission Control."),
            },
            required=["taskType", "summary"],
        ),
        _function_tool(
            "prepare_follow_up_summary",
            "Prepare a concise end-of-call summary and recommended next action for Ares Mission Control.",
            {
                "keyFacts": {"type": "array", "items": {"type": "string"}},
                "nextAction": _string_schema("Recommended next operator action."),
                "followUpWindow": _string_schema("Best follow-up time or urgency."),
            },
            required=["keyFacts", "nextAction"],
        ),
        _function_tool(
            "request_human_handoff",
            "Flag a call that needs immediate human review, callback, or live transfer outside the AI workflow.",
            {
                "reason": _string_schema("Why a human should take over."),
                "urgency": {"type": "string", "enum": ["normal", "high", "urgent"]},
                "summary": _string_schema("Concise handoff summary."),
            },
            required=["reason", "urgency", "summary"],
        ),
    ]


def _function_tool(name: str, description: str, properties: dict[str, Any], *, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "async": False,
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


def _string_schema(description: str) -> dict[str, str]:
    return {"type": "string", "description": description}


def _tool_call_parameters(tool_call: dict[str, Any]) -> dict[str, Any]:
    raw_parameters = tool_call.get("parameters")
    if isinstance(raw_parameters, dict):
        return raw_parameters
    function = tool_call.get("function")
    if isinstance(function, dict):
        raw_arguments = function.get("arguments")
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if isinstance(raw_arguments, str) and raw_arguments.strip():
            try:
                parsed = json.loads(raw_arguments)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
    return {}


def _extract_list(value: Any, key: str) -> list[Any]:
    if isinstance(value, dict):
        raw = value.get(key)
    else:
        raw = getattr(value, key, None)
    return raw if isinstance(raw, list) else []


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {key: _jsonable(entry) for key, entry in value.items()}
    if isinstance(value, list):
        return [_jsonable(entry) for entry in value]
    return value


def _record_matches(record: Any, parameters: dict[str, Any]) -> bool:
    record_id = _field(record, "id")
    source_lead_id = _field(record, "source_lead_id", "sourceLeadId")
    source_contact_id = _field(record, "source_contact_id", "sourceContactId")
    if parameters.get("recordId") and record_id == parameters["recordId"]:
        return True
    if parameters.get("leadId") and (source_lead_id == parameters["leadId"] or record_id == parameters["leadId"]):
        return True
    if parameters.get("contactId") and source_contact_id == parameters["contactId"]:
        return True
    if parameters.get("phone") and _digits(parameters["phone"]) and _digits(parameters["phone"]) in _digits(_field(record, "phone")):
        return True
    if parameters.get("email") and _same_text(_field(record, "email"), parameters["email"]):
        return True
    if parameters.get("name") and _contains_text(_field(record, "display_name", "displayName", "owner_name", "ownerName"), parameters["name"]):
        return True
    if parameters.get("propertyAddress") and _contains_text(_field(record, "property_address", "propertyAddress"), parameters["propertyAddress"]):
        return True
    return not any(parameters.get(key) for key in ["recordId", "leadId", "contactId", "phone", "email", "name", "propertyAddress"])


def _field(record: Any, *names: str) -> Any:
    for name in names:
        if isinstance(record, dict) and name in record:
            return record[name]
        if hasattr(record, name):
            return getattr(record, name)
    return None


def _require(parameters: dict[str, Any], *names: str) -> str:
    for name in names:
        value = _clean(parameters.get(name))
        if value:
            return value
    raise ValueError(f"{names[0]} is required")


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _digits(value: Any) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def _same_text(value: Any, query: Any) -> bool:
    return str(value or "").strip().lower() == str(query or "").strip().lower()


def _contains_text(value: Any, query: Any) -> bool:
    return str(query or "").strip().lower() in str(value or "").strip().lower()


def _classify_source_lane(parameters: dict[str, Any]) -> str:
    haystack = " ".join(
        str(parameters.get(key) or "")
        for key in ["intent", "sourceHint", "motivation", "propertyCondition", "summary"]
    ).lower()
    if any(term in haystack for term in ["probate", "heir", "estate", "executor", "administrator"]):
        return "outbound_probate"
    if any(term in haystack for term in ["lease option", "lease-option", "rent to own", "seller finance"]):
        return "inbound_lease_option"
    if any(term in haystack for term in ["title", "deed", "lien", "tax delinquent", "quiet title"]):
        return "curative_title"
    if any(term in haystack for term in ["wrong number", "do not call", "remove me"]):
        return "wrong_number"
    if any(term in haystack for term in ["sell", "offer", "vacant", "repairs"]):
        return "seller_direct"
    return "unknown"


def _score_lead(parameters: dict[str, Any]) -> dict[str, Any]:
    haystack = " ".join(
        str(parameters.get(key) or "")
        for key in ["intent", "timeline", "motivation", "authority", "propertyCondition"]
    ).lower()
    score = 20
    if any(term in haystack for term in ["owner", "heir", "executor", "administrator", "spouse"]):
        score += 25
    if any(term in haystack for term in ["7 days", "this week", "today", "asap", "urgent", "this month", "30 days"]):
        score += 20
    if any(term in haystack for term in ["vacant", "repairs", "behind", "tax", "probate", "title", "lien", "foreclosure"]):
        score += 20
    if any(term in haystack for term in ["sell", "offer", "cash", "lease option", "needs to"]):
        score += 15
    if any(term in haystack for term in ["curious", "next year", "neighbor", "unknown", "not interested"]):
        score -= 20
    bounded = max(0, min(100, score))
    return {"score": bounded, "temperature": "hot" if bounded >= 70 else "warm" if bounded >= 45 else "cold"}


CALL_SCRIPTS: dict[str, dict[str, Any]] = {
    "outbound_probate": {
        "opening": {
            "initial_qualification": "I’m calling about a property tied to an estate record. I’m not an attorney, but I can collect details for our property team. Are you connected to the estate or property?",
            "callback": "I’m following up on the estate property conversation. Has anything changed with the property, title, or family decision since we last spoke?",
            "objection": "That makes sense. I’m not trying to pressure you. I only need to understand whether a property solution is useful and route it to a human if it is.",
            "closing_summary": "I have the estate-property notes. A human operator will review the details before any next step.",
        },
        "questions": [
            "What is your relationship to the owner or estate?",
            "Is the property occupied, vacant, rented, or unknown?",
            "Is the family trying to sell, keep, transfer, or still deciding?",
            "Are there title, deed, tax, or court issues we should know about?",
            "What is the best number for a human follow-up?",
        ],
        "next_steps": ["Create a Mission Control review task.", "Classify as outbound_probate or curative_title based on volunteered facts."],
    },
    "inbound_lease_option": {
        "opening": {
            "initial_qualification": "I can collect the basics about lease-option terms and have a human review the fit. What made you reach out?",
            "callback": "I’m following up on the lease-option request. Are you still open to discussing terms for the property?",
            "objection": "No problem. I can keep this simple: timeline, property basics, and the best way for a human to follow up.",
            "closing_summary": "I have the lease-option notes. The next step is human review and follow-up.",
        },
        "questions": [
            "Are you the owner or authorized decision maker?",
            "What property are we talking about?",
            "Are you looking to sell now, lease with an option, or compare both?",
            "What timeline are you hoping for?",
        ],
        "next_steps": ["Create or update the Ares record.", "Create a callback task when terms need human review."],
    },
    "curative_title": {
        "opening": {
            "initial_qualification": "I can collect the property and title issue details for our review team. I’m not an attorney, but I can route this correctly. What title issue are you dealing with?",
            "callback": "I’m following up on the title issue. Do you have any new deed, lien, tax, or ownership details?",
            "objection": "I can keep this to factual notes and have a human decide whether follow-up makes sense.",
            "closing_summary": "I have the title notes. A human will review before any next action.",
        },
        "questions": [
            "What is the property address?",
            "Who currently has authority to make decisions?",
            "Is the issue a deed, lien, tax, heirship, probate, or ownership dispute?",
            "Is there a deadline or pending court/action date?",
        ],
        "next_steps": ["Request human handoff for legal-sensitive facts.", "Attach notes to a Mission Control task."],
    },
    "unknown": {
        "opening": {
            "initial_qualification": "I can help route this to the right real estate workflow. Are you calling about selling, lease-option terms, a title issue, probate, or something else?",
            "callback": "I’m following up from the property desk. What would you like us to review?",
            "objection": "Understood. I’ll keep the note brief and avoid follow-up unless you confirm it is okay.",
            "closing_summary": "I have the note and will route it for review.",
        },
        "questions": ["What is the reason for the call?", "What property is involved?", "What is your role with the property?"],
        "next_steps": ["Classify the lane after one or two facts.", "Do not update Ares unless identity and follow-up permission are clear."],
    },
}

CALL_SCRIPTS["seller_direct"] = CALL_SCRIPTS["inbound_lease_option"]
CALL_SCRIPTS["buyer_inquiry"] = CALL_SCRIPTS["unknown"]
CALL_SCRIPTS["vendor"] = CALL_SCRIPTS["unknown"]
CALL_SCRIPTS["wrong_number"] = CALL_SCRIPTS["unknown"]
