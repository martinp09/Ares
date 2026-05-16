# TextGrid SMS Reply Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an always-on TextGrid SMS reply agent that ingests lead replies, classifies/drafts safe responses, stores operational truth in Supabase, and exports a redacted evaluation corpus without enabling live auto-sends by default.

**Architecture:** The TextGrid webhook records and enqueues work, then returns immediately. A protected internal processor and Trigger.dev schedule drain jobs, reuse existing Ares TextGrid/message/conversation/Mission Control/provider patterns, and keep all live outbound sends behind existing and new SMS-agent gates. Supabase stores hot operational state; Obsidian/JSONL stores redacted cold eval archives.

**Tech Stack:** FastAPI, Pydantic, Supabase/Postgres migrations, Trigger.dev v4, React/Mission Control, existing Ares provider registry, TextGrid Twilio-compatible SMS APIs.

---

## File Structure

- Modify: `app/core/config.py`
  - Add SMS-agent mode, auto-reply, queue, retention, and archive settings.
- Modify: `app/main.py`
  - Mount a public TextGrid webhook router without runtime bearer auth and keep internal/operator SMS routes protected.
- Modify: `app/api/sms_agent.py`
  - Split public webhook route from protected routes.
  - Add protected `POST /sms-agent/internal/process-pending`.
- Modify: `app/models/sms_agent.py`
  - Add job, decision, processing, eval, and archive models.
- Create: `app/db/sms_agent.py`
  - Repository for jobs, decisions, eval labels, and archive pointers.
- Modify: `app/services/sms_agent_service.py`
  - Keep outbound send behavior, add inbound job creation and processing orchestration.
- Create: `app/services/sms_reply_agent_service.py`
  - Resolve context, classify replies, call provider for drafts, validate policy, and write decisions.
- Modify: `app/services/inbound_sms_service.py`
  - Return richer inbound processing metadata and delegate reply-agent job enqueueing.
- Modify: `app/providers/textgrid.py`
  - Support `X-Twilio-Signature`, XML acknowledgement needs, and verified TextGrid payload fields.
- Create: `supabase/migrations/20260516090000_sms_reply_agent_runtime.sql`
  - Add hot operational reply-agent tables and indexes.
- Create: `scripts/sms_agent_archive_export.py`
  - Export redacted decisions/messages to Obsidian/JSONL.
- Create: `scripts/smoke/textgrid_sms_reply_agent_smoke.py`
  - Exercise signed webhook ingest, processing, and optional approved live send smoke.
- Modify: `trigger/src/marketing/smsReplyAgentProcessor.ts`
  - Add scheduled Trigger.dev processor for pending SMS-agent jobs.
- Modify: `trigger/src/marketing/runtime.ts`
  - Add payload/response types for SMS-agent processor if the file exists in current implementation context.
- Modify: `apps/mission-control/src/lib/api.ts`
  - Map SMS-agent decision fields into inbox detail.
- Modify: `apps/mission-control/src/pages/InboxPage.tsx`
  - Show intent/source-lane/draft/approval controls inside the existing inbox surface.
- Modify: `README.md`
  - Document envs, webhook URL, archive posture, and rollout gates.
- Modify: `CONTEXT.md`, `memory.md`
  - Keep branch scope and durable SMS-agent decisions indexed.

## Task 1: Verify TextGrid Webhook Contract and Public Route Shape

**Files:**
- Modify: `tests/api/test_sms_agent.py`
- Modify: `app/api/sms_agent.py`
- Modify: `app/main.py`
- Modify: `app/providers/textgrid.py`

- [ ] **Step 1: Write failing public-webhook auth/signature test**

Add this test to `tests/api/test_sms_agent.py`:

```python
import base64
import hashlib
import hmac


def _twilio_signature(secret: str, url: str, payload: dict[str, object]) -> str:
    signed = url + "".join(str(payload[key]) for key in sorted(payload))
    digest = hmac.new(secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_sms_agent_textgrid_inbound_webhook_accepts_signed_provider_without_runtime_bearer(monkeypatch) -> None:
    from app.api import sms_agent as sms_agent_api

    class StubInboundSmsService:
        def __init__(self) -> None:
            self.calls = []

        def handle_textgrid_webhook(self, payload, *, signature, request_url=None):
            self.calls.append((payload, signature, request_url))
            return {"status": "processed", "event_type": "inbound", "action": "qualify", "job_id": "smsjob_1"}

    stub = StubInboundSmsService()
    monkeypatch.setattr(sms_agent_api, "inbound_sms_service", stub)
    monkeypatch.setenv("TEXTGRID_WEBHOOK_SECRET", "whsec_123")

    client = TestClient(app)
    payload = {
        "MessageSid": "SM123",
        "From": "+15551234567",
        "To": "+13467725914",
        "Body": "Can you call me?",
    }
    signature = _twilio_signature("whsec_123", "http://testserver/sms-agent/webhooks/textgrid", payload)

    response = client.post(
        "/sms-agent/webhooks/textgrid",
        data=payload,
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "X-Twilio-Signature": signature,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert response.text == "<Response></Response>"
    assert stub.calls[0][0] == payload
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run pytest tests/api/test_sms_agent.py::test_sms_agent_textgrid_inbound_webhook_accepts_signed_provider_without_runtime_bearer -q
```

Expected: FAIL because the current `/sms-agent/webhooks/textgrid` route is mounted behind runtime bearer auth and returns JSON.

- [ ] **Step 3: Support both TextGrid and Twilio signature header names**

Change `handle_textgrid_sms_agent_webhook` in `app/api/sms_agent.py` to read both headers:

```python
x_twilio_signature: str | None = Header(default=None),
...
signature = x_textgrid_signature or x_twilio_signature
kwargs: dict[str, Any] = {"signature": signature}
```

- [ ] **Step 4: Split protected and public routers**

In `app/api/sms_agent.py`, keep `router = APIRouter(prefix="/sms-agent", tags=["sms-agent"])` for `/messages` and internal routes. Add:

```python
public_router = APIRouter(prefix="/sms-agent", tags=["sms-agent"])
```

Move only `@router.post("/webhooks/textgrid"...` to:

```python
@public_router.post("/webhooks/textgrid", include_in_schema=False)
```

Return a raw XML response for inbound/status acknowledgements:

```python
from fastapi import Response

...
result = handler(payload, **kwargs)
return Response(
    content="<Response></Response>",
    media_type="application/xml",
    headers={"X-Ares-Sms-Agent-Status": str(result.get("status", "processed"))},
)
```

- [ ] **Step 5: Mount the public router without protected dependencies**

In `app/main.py`, import both routers:

```python
from app.api.sms_agent import public_router as sms_agent_public_router
from app.api.sms_agent import router as sms_agent_router
```

Mount the public router before protected routes:

```python
app.include_router(sms_agent_public_router)
app.include_router(sms_agent_router, dependencies=protected_dependencies)
```

- [ ] **Step 6: Run focused API tests**

Run:

```bash
uv run pytest tests/api/test_sms_agent.py tests/api/test_runtime_auth.py -q
```

Expected: PASS. Runtime query-token auth must still be rejected for protected routes.

## Task 2: Add SMS Reply-Agent Settings

**Files:**
- Modify: `app/core/config.py`
- Modify: `tests/api/test_runtime_config_contract.py`

- [ ] **Step 1: Add config contract test**

Add assertions to `tests/api/test_runtime_config_contract.py`:

```python
def test_sms_agent_settings_default_to_draft_safe_mode() -> None:
    settings = Settings(_env_file=None)

    assert settings.sms_agent_mode == "draft_only"
    assert settings.sms_agent_auto_replies_enabled is False
    assert settings.sms_agent_process_batch_size == 25
    assert settings.sms_agent_max_attempts == 5
    assert settings.sms_agent_archive_enabled is False
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run pytest tests/api/test_runtime_config_contract.py::test_sms_agent_settings_default_to_draft_safe_mode -q
```

Expected: FAIL because the settings do not exist.

- [ ] **Step 3: Add settings**

Add to `Settings` in `app/core/config.py` near TextGrid config:

```python
    sms_agent_mode: Literal["record_only", "draft_only", "auto_ack"] = Field(
        default="draft_only",
        validation_alias=AliasChoices("sms_agent_mode", "SMS_AGENT_MODE"),
    )
    sms_agent_auto_replies_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("sms_agent_auto_replies_enabled", "SMS_AGENT_AUTO_REPLIES_ENABLED"),
    )
    sms_agent_allowed_from_numbers: str | None = Field(
        default=None,
        validation_alias=AliasChoices("sms_agent_allowed_from_numbers", "SMS_AGENT_ALLOWED_FROM_NUMBERS"),
    )
    sms_agent_process_batch_size: int = Field(
        default=25,
        validation_alias=AliasChoices("sms_agent_process_batch_size", "SMS_AGENT_PROCESS_BATCH_SIZE"),
    )
    sms_agent_max_attempts: int = Field(
        default=5,
        validation_alias=AliasChoices("sms_agent_max_attempts", "SMS_AGENT_MAX_ATTEMPTS"),
    )
    sms_agent_lock_seconds: int = Field(
        default=120,
        validation_alias=AliasChoices("sms_agent_lock_seconds", "SMS_AGENT_LOCK_SECONDS"),
    )
    sms_agent_retention_days: int = Field(
        default=90,
        validation_alias=AliasChoices("sms_agent_retention_days", "SMS_AGENT_RETENTION_DAYS"),
    )
    sms_agent_archive_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("sms_agent_archive_enabled", "SMS_AGENT_ARCHIVE_ENABLED"),
    )
    sms_agent_obsidian_archive_root: str | None = Field(
        default=None,
        validation_alias=AliasChoices("sms_agent_obsidian_archive_root", "SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT"),
    )
    sms_agent_prompt_version: str = Field(
        default="sms_reply_agent_v1",
        validation_alias=AliasChoices("sms_agent_prompt_version", "SMS_AGENT_PROMPT_VERSION"),
    )
```

- [ ] **Step 4: Run config contract test**

Run:

```bash
uv run pytest tests/api/test_runtime_config_contract.py::test_sms_agent_settings_default_to_draft_safe_mode -q
```

Expected: PASS.

## Task 3: Add Supabase Runtime Tables and Repository

**Files:**
- Create: `supabase/migrations/20260516090000_sms_reply_agent_runtime.sql`
- Create: `app/db/sms_agent.py`
- Modify: `app/db/__init__.py`
- Modify: `tests/services/test_sms_reply_agent_repository.py`

- [ ] **Step 1: Write repository tests**

Create `tests/services/test_sms_reply_agent_repository.py`:

```python
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.sms_agent import SmsAgentRepository
from app.models.sms_agent import SmsAgentJobCreate, SmsAgentReplyDecisionCreate


def test_sms_agent_repository_dedupes_jobs_by_webhook_receipt_and_message() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)

    first = repo.enqueue_job(
        SmsAgentJobCreate(
            business_id="limitless",
            environment="dev",
            provider_webhook_id="wh_1",
            message_id="msg_1",
            conversation_id="cnv_1",
            contact_id="lead_1",
            from_number="+15551234567",
            to_number="+13467725914",
        )
    )
    second = repo.enqueue_job(
        SmsAgentJobCreate(
            business_id="limitless",
            environment="dev",
            provider_webhook_id="wh_1",
            message_id="msg_1",
            conversation_id="cnv_1",
            contact_id="lead_1",
            from_number="+15551234567",
            to_number="+13467725914",
        )
    )

    assert second.id == first.id
    assert second.deduped is True


def test_sms_agent_repository_claims_pending_jobs_and_records_decision() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(
        SmsAgentJobCreate(
            business_id="limitless",
            environment="dev",
            provider_webhook_id="wh_1",
            message_id="msg_1",
            conversation_id="cnv_1",
            contact_id="lead_1",
            from_number="+15551234567",
            to_number="+13467725914",
        )
    )

    claimed = repo.claim_pending(limit=10, lock_seconds=120)
    assert [entry.id for entry in claimed] == [job.id]

    decision = repo.record_decision(
        SmsAgentReplyDecisionCreate(
            business_id="limitless",
            environment="dev",
            job_id=job.id,
            message_id="msg_1",
            conversation_id="cnv_1",
            contact_id="lead_1",
            intent="interested",
            source_lane="seller_direct",
            temperature="warm",
            urgency="normal",
            action="draft_only",
            suggested_body="Thanks. I will have a human review and follow up.",
            confidence=0.76,
            policy_reason="Draft-only default",
            prompt_version="sms_reply_agent_v1",
        )
    )
    repo.mark_completed(job.id, decision_id=decision.id)

    refreshed = repo.get_job(job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.decision_id == decision.id
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/services/test_sms_reply_agent_repository.py -q
```

Expected: FAIL because the repository/models do not exist.

- [ ] **Step 3: Add models**

In `app/models/sms_agent.py`, add strict Pydantic records:

```python
from datetime import datetime


class SmsAgentJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    provider_webhook_id: str | None = None
    message_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    from_number: str = Field(min_length=1)
    to_number: str = Field(min_length=1)
    payload_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsAgentJobRecord(SmsAgentJobCreate):
    id: str = Field(min_length=1)
    status: str = "pending"
    attempt_count: int = 0
    locked_until: datetime | None = None
    decision_id: str | None = None
    deduped: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SmsAgentReplyDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    message_id: str | None = None
    conversation_id: str | None = None
    contact_id: str | None = None
    intent: str = Field(min_length=1)
    source_lane: str = Field(min_length=1)
    temperature: str = Field(min_length=1)
    urgency: str = Field(min_length=1)
    action: str = Field(min_length=1)
    suggested_body: str | None = None
    confidence: float = Field(ge=0, le=1)
    policy_reason: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    provider_kind: str | None = None
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsAgentReplyDecisionRecord(SmsAgentReplyDecisionCreate):
    id: str = Field(min_length=1)
    created_at: datetime | None = None
```

- [ ] **Step 4: Add migration**

Create `supabase/migrations/20260516090000_sms_reply_agent_runtime.sql`:

```sql
begin;

create table if not exists public.sms_agent_jobs (
  id bigint generated by default as identity primary key,
  business_id bigint not null,
  environment text not null,
  provider_webhook_id bigint,
  message_id bigint,
  conversation_id bigint,
  contact_id bigint,
  from_number text not null,
  to_number text not null,
  payload_hash text,
  status text not null default 'pending',
  attempt_count integer not null default 0,
  locked_until timestamptz,
  decision_id bigint,
  last_error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint sms_agent_jobs_business_fkey
    foreign key (business_id, environment)
    references public.businesses (business_id, environment)
    on delete cascade,
  constraint sms_agent_jobs_status_check
    check (status in ('pending', 'processing', 'completed', 'blocked', 'failed_retryable', 'failed_terminal'))
);

create table if not exists public.sms_agent_decisions (
  id bigint generated by default as identity primary key,
  business_id bigint not null,
  environment text not null,
  job_id bigint not null references public.sms_agent_jobs(id) on delete cascade,
  message_id bigint,
  conversation_id bigint,
  contact_id bigint,
  intent text not null,
  source_lane text not null,
  temperature text not null,
  urgency text not null,
  action text not null,
  suggested_body text,
  confidence numeric not null default 0,
  policy_reason text not null,
  prompt_version text not null,
  provider_kind text,
  model text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint sms_agent_decisions_business_fkey
    foreign key (business_id, environment)
    references public.businesses (business_id, environment)
    on delete cascade,
  constraint sms_agent_decisions_confidence_check check (confidence >= 0 and confidence <= 1)
);

alter table public.sms_agent_jobs
  add constraint sms_agent_jobs_decision_fkey
  foreign key (decision_id)
  references public.sms_agent_decisions(id)
  on delete set null;

create table if not exists public.sms_agent_eval_labels (
  id bigint generated by default as identity primary key,
  business_id bigint not null,
  environment text not null,
  decision_id bigint not null references public.sms_agent_decisions(id) on delete cascade,
  label text not null,
  reviewer text,
  notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint sms_agent_eval_labels_business_fkey
    foreign key (business_id, environment)
    references public.businesses (business_id, environment)
    on delete cascade
);

create table if not exists public.sms_agent_archives (
  id bigint generated by default as identity primary key,
  business_id bigint not null,
  environment text not null,
  decision_id bigint references public.sms_agent_decisions(id) on delete set null,
  archive_uri text not null,
  content_sha256 text not null,
  redacted boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint sms_agent_archives_business_fkey
    foreign key (business_id, environment)
    references public.businesses (business_id, environment)
    on delete cascade
);

create unique index if not exists sms_agent_jobs_webhook_message_unique_idx
  on public.sms_agent_jobs (business_id, environment, coalesce(provider_webhook_id, 0), coalesce(message_id, 0), coalesce(payload_hash, ''));
create index if not exists sms_agent_jobs_pending_idx
  on public.sms_agent_jobs (business_id, environment, status, locked_until, created_at);
create index if not exists sms_agent_decisions_job_idx
  on public.sms_agent_decisions (business_id, environment, job_id, created_at desc);
create index if not exists sms_agent_eval_labels_decision_idx
  on public.sms_agent_eval_labels (business_id, environment, decision_id, created_at desc);

drop trigger if exists sms_agent_jobs_touch_updated_at on public.sms_agent_jobs;
create trigger sms_agent_jobs_touch_updated_at
before update on public.sms_agent_jobs
for each row execute function public.touch_updated_at();

alter table public.sms_agent_jobs enable row level security;
alter table public.sms_agent_decisions enable row level security;
alter table public.sms_agent_eval_labels enable row level security;
alter table public.sms_agent_archives enable row level security;

create policy sms_agent_jobs_tenant_isolation on public.sms_agent_jobs
for all
using (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment())
with check (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment());

create policy sms_agent_decisions_tenant_isolation on public.sms_agent_decisions
for all
using (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment())
with check (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment());

create policy sms_agent_eval_labels_tenant_isolation on public.sms_agent_eval_labels
for all
using (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment())
with check (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment());

create policy sms_agent_archives_tenant_isolation on public.sms_agent_archives
for all
using (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment())
with check (business_id = public.current_tenant_business_id() and environment = public.current_tenant_environment());

commit;
```

- [ ] **Step 5: Add memory repository implementation**

Implement `app/db/sms_agent.py` with memory first, then Supabase using existing `lead_machine_supabase.fetch_rows`, `insert_rows`, `patch_rows`, `resolve_tenant`, `external_id`, and `row_id_from_external_id` patterns.

The memory path must store:

```python
store.sms_agent_jobs: dict[str, SmsAgentJobRecord]
store.sms_agent_job_keys: dict[tuple[str, str, str | None, str | None, str | None], str]
store.sms_agent_decisions: dict[str, SmsAgentReplyDecisionRecord]
```

- [ ] **Step 6: Run repository tests**

Run:

```bash
uv run pytest tests/services/test_sms_reply_agent_repository.py -q
```

Expected: PASS.

## Task 4: Enqueue Reply Jobs From Inbound TextGrid Webhooks

**Files:**
- Modify: `app/services/inbound_sms_service.py`
- Modify: `app/services/sms_agent_service.py`
- Modify: `tests/services/test_inbound_sms_service.py`

- [ ] **Step 1: Add failing enqueue test**

Add to `tests/services/test_inbound_sms_service.py`:

```python
def test_inbound_sms_enqueues_sms_reply_agent_job_for_resolved_lead() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
        )
    )

    class RecordingSmsAgent:
        def __init__(self) -> None:
            self.calls = []

        def enqueue_inbound_reply_job(self, *, event, lead, provider_thread_id, receipt_id):
            self.calls.append((event, lead, provider_thread_id, receipt_id))
            return "smsjob_1"

    sms_agent = RecordingSmsAgent()
    service = InboundSmsService(
        textgrid_adapter=_StubTextgridAdapter(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="Can you call me?",
                from_number=lead.phone,
                to_number="+13467725914",
                external_id="sms_inbound_1",
                metadata={"business_id": lead.business_id, "environment": lead.environment},
            )
        ),
        contacts=contacts,
    )
    service.sms_agent_service = sms_agent

    result = service.handle_textgrid_webhook({}, signature=None)

    assert result["job_id"] == "smsjob_1"
    assert sms_agent.calls[0][1].id == lead.id
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run pytest tests/services/test_inbound_sms_service.py::test_inbound_sms_enqueues_sms_reply_agent_job_for_resolved_lead -q
```

Expected: FAIL because `sms_agent_service` is not wired.

- [ ] **Step 3: Add enqueue method to `SmsAgentService`**

Add:

```python
    def enqueue_inbound_reply_job(
        self,
        *,
        event: NormalizedSmsEvent,
        lead: MarketingLeadRecord | None,
        provider_thread_id: str | None,
        receipt_id: str | None,
    ) -> str | None:
        if event.event_type != "inbound":
            return None
        job = self.sms_agent_repository.enqueue_job(
            SmsAgentJobCreate(
                business_id=lead.business_id if lead else str((event.metadata or {}).get("business_id") or "unknown"),
                environment=lead.environment if lead else str((event.metadata or {}).get("environment") or "unknown"),
                provider_webhook_id=receipt_id,
                message_id=None,
                conversation_id=provider_thread_id,
                contact_id=lead.id if lead else None,
                from_number=event.from_number,
                to_number=event.to_number,
                metadata={"external_id": event.external_id, "body_preview": event.body[:160]},
            )
        )
        return job.id
```

Use the actual repository property name chosen in Task 3.

- [ ] **Step 4: Call enqueue after inbound message append**

In `InboundSmsService.handle_textgrid_webhook`, after appending/resolving inbound messages and before returning, call `self.sms_agent_service.enqueue_inbound_reply_job(...)` when `event.event_type == "inbound"`.

Return:

```python
return {"status": "processed", "event_type": event.event_type, "action": action, "job_id": job_id or ""}
```

- [ ] **Step 5: Run focused inbound SMS tests**

Run:

```bash
uv run pytest tests/services/test_inbound_sms_service.py -q
```

Expected: PASS.

## Task 5: Implement Deterministic Classifier and Policy Gate

**Files:**
- Create: `app/services/sms_reply_agent_service.py`
- Modify: `app/models/sms_agent.py`
- Create: `tests/services/test_sms_reply_agent_service.py`

- [ ] **Step 1: Write tests for STOP, ambiguous, and draft-only**

Create `tests/services/test_sms_reply_agent_service.py`:

```python
from app.core.config import Settings
from app.services.sms_reply_agent_service import SmsReplyAgentService, SmsReplyContext


def test_sms_reply_agent_stop_is_terminal_without_provider_call() -> None:
    calls = []
    service = SmsReplyAgentService(settings=Settings(_env_file=None), provider_complete=lambda request: calls.append(request))

    decision = service.decide(
        SmsReplyContext(
            business_id="limitless",
            environment="dev",
            job_id="smsjob_1",
            message_id="msg_1",
            contact_id="lead_1",
            from_number="+15551234567",
            to_number="+13467725914",
            body="stop texting me",
            resolved=True,
            ambiguous=False,
            sms_consent=True,
            suppressed=False,
            recent_messages=[],
            lead_context={},
        )
    )

    assert decision.intent == "stop"
    assert decision.action == "human_handoff"
    assert decision.suppress_contact is True
    assert calls == []


def test_sms_reply_agent_ambiguous_match_blocks_auto_send() -> None:
    service = SmsReplyAgentService(settings=Settings(_env_file=None, sms_agent_auto_replies_enabled=True, provider_live_sends_enabled=True))

    decision = service.decide(
        SmsReplyContext(
            business_id="limitless",
            environment="dev",
            job_id="smsjob_1",
            message_id="msg_1",
            contact_id=None,
            from_number="+15551234567",
            to_number="+13467725914",
            body="yes",
            resolved=False,
            ambiguous=True,
            sms_consent=False,
            suppressed=False,
            recent_messages=[],
            lead_context={},
        )
    )

    assert decision.action == "human_handoff"
    assert decision.policy_reason == "Ambiguous or unresolved sender"


def test_sms_reply_agent_defaults_to_draft_only_for_interested_reply() -> None:
    service = SmsReplyAgentService(settings=Settings(_env_file=None))

    decision = service.decide(
        SmsReplyContext(
            business_id="limitless",
            environment="dev",
            job_id="smsjob_1",
            message_id="msg_1",
            contact_id="lead_1",
            from_number="+15551234567",
            to_number="+13467725914",
            body="Yes I am interested",
            resolved=True,
            ambiguous=False,
            sms_consent=True,
            suppressed=False,
            recent_messages=[],
            lead_context={"source_lane": "outbound_probate"},
        )
    )

    assert decision.intent == "interested"
    assert decision.source_lane == "outbound_probate"
    assert decision.action == "draft_only"
    assert decision.suggested_body
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
uv run pytest tests/services/test_sms_reply_agent_service.py -q
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement strict context and decision models**

Add to `app/models/sms_agent.py` or the new service module:

```python
class SmsReplyContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str
    environment: str
    job_id: str
    message_id: str | None = None
    contact_id: str | None = None
    from_number: str
    to_number: str
    body: str
    resolved: bool
    ambiguous: bool
    sms_consent: bool
    suppressed: bool
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    lead_context: dict[str, Any] = Field(default_factory=dict)


class SmsReplyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str
    source_lane: str
    temperature: str
    urgency: str
    action: str
    suggested_body: str | None = None
    confidence: float = Field(ge=0, le=1)
    policy_reason: str
    suppress_contact: bool = False
    handoff_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Implement deterministic classifier**

Rules:

```python
STOP_TERMS = {"stop", "unsubscribe", "cancel", "remove me", "do not text", "dont text"}
WRONG_NUMBER_TERMS = {"wrong number", "wrong person", "not me"}
LEGAL_TERMS = {"attorney", "lawyer", "court", "sue", "probate court", "lawsuit", "legal advice", "tax advice"}
INTEREST_TERMS = {"yes", "interested", "call me", "tell me more", "offer", "how much", "cash"}
APPOINTMENT_TERMS = {"schedule", "appointment", "meet", "call tomorrow", "call today"}
```

Map source lane from `lead_context["source_lane"]` first, then text hints. Keep `outbound_probate` and `inbound_lease_option` separate.

- [ ] **Step 5: Implement policy gate**

`auto_ack` is allowed only when:

```python
settings.provider_live_sends_enabled
and settings.sms_agent_auto_replies_enabled
and context.resolved
and not context.ambiguous
and context.sms_consent
and not context.suppressed
and decision.intent in {"interested", "question", "appointment_request", "unknown"}
and decision.urgency != "urgent"
```

Otherwise return `draft_only`, `record_only`, or `human_handoff`.

- [ ] **Step 6: Run service tests**

Run:

```bash
uv run pytest tests/services/test_sms_reply_agent_service.py -q
```

Expected: PASS.

## Task 6: Process Pending Jobs and Write Decisions

**Files:**
- Modify: `app/services/sms_agent_service.py`
- Modify: `app/api/sms_agent.py`
- Create: `tests/services/test_sms_agent_processing.py`
- Modify: `tests/api/test_sms_agent.py`

- [ ] **Step 1: Write processing service test**

Create `tests/services/test_sms_agent_processing.py`:

```python
from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.sms_agent import SmsAgentRepository
from app.models.sms_agent import SmsAgentJobCreate
from app.services.sms_agent_service import SmsAgentService


def test_sms_agent_process_pending_records_draft_decision_without_sending() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    repo.enqueue_job(
        SmsAgentJobCreate(
            business_id="limitless",
            environment="dev",
            provider_webhook_id="wh_1",
            message_id="msg_1",
            conversation_id="cnv_1",
            contact_id="lead_1",
            from_number="+15551234567",
            to_number="+13467725914",
            metadata={"body": "yes I am interested", "sms_consent": True, "source_lane": "outbound_probate"},
        )
    )
    sent_requests = []
    service = SmsAgentService(
        settings=Settings(_env_file=None, provider_live_sends_enabled=False),
        sms_agent_repository=repo,
        request_sender=sent_requests.append,
    )

    result = service.process_pending(limit=10)

    assert result["processed_count"] == 1
    assert result["sent_count"] == 0
    assert sent_requests == []
    assert len(repo.list_decisions(business_id="limitless", environment="dev")) == 1
```

- [ ] **Step 2: Write internal API test**

Add to `tests/api/test_sms_agent.py`:

```python
def test_sms_agent_process_pending_requires_runtime_auth() -> None:
    client = TestClient(app)
    response = client.post("/sms-agent/internal/process-pending", json={"limit": 10})
    assert response.status_code == 401
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run pytest tests/services/test_sms_agent_processing.py tests/api/test_sms_agent.py::test_sms_agent_process_pending_requires_runtime_auth -q
```

Expected: service test FAIL and auth test PASS after route exists.

- [ ] **Step 4: Add request/response models**

In `app/models/sms_agent.py`:

```python
class SmsAgentProcessPendingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int | None = Field(default=None, ge=1, le=100)


class SmsAgentProcessPendingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    processed_count: int
    sent_count: int
    blocked_count: int
    failed_count: int
```

- [ ] **Step 5: Implement `SmsAgentService.process_pending`**

Use repository `claim_pending`, build `SmsReplyContext` from job metadata and loaded records, call `SmsReplyAgentService.decide`, record decision, and send only if `decision.action == "auto_ack"`.

If send fails, mark job `failed_retryable` until `sms_agent_max_attempts`, then `failed_terminal`.

- [ ] **Step 6: Add protected route**

In `app/api/sms_agent.py`:

```python
@router.post("/internal/process-pending", response_model=SmsAgentProcessPendingResponse)
def process_pending_sms_agent_jobs(
    request: SmsAgentProcessPendingRequest,
    service: SmsAgentService = Depends(sms_agent_service_dependency),
) -> SmsAgentProcessPendingResponse:
    return SmsAgentProcessPendingResponse(**service.process_pending(limit=request.limit))
```

- [ ] **Step 7: Run processing tests**

Run:

```bash
uv run pytest tests/services/test_sms_agent_processing.py tests/api/test_sms_agent.py -q
```

Expected: PASS.

## Task 7: Add Trigger.dev Always-On Processor

**Files:**
- Create: `trigger/src/marketing/smsReplyAgentProcessor.ts`
- Modify: `trigger/src/marketing/runtime.ts` if current exports require central type registration
- Create: `tests/api/test_trigger_contract_files.py` assertions if current test file validates Trigger task ids

- [ ] **Step 1: Add Trigger task**

Create `trigger/src/marketing/smsReplyAgentProcessor.ts`:

```ts
import { schedules } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";

export type SmsReplyAgentProcessResponse = {
  processed_count: number;
  sent_count: number;
  blocked_count: number;
  failed_count: number;
};

export const smsReplyAgentProcessor = schedules.task({
  id: "sms-agent-process-pending",
  cron: { pattern: "*/1 * * * *", timezone: "America/Chicago" },
  run: async () => {
    const limit = Number(process.env.SMS_AGENT_PROCESS_BATCH_SIZE ?? "25");
    return await invokeRuntimeApi<SmsReplyAgentProcessResponse, { limit: number }>(
      "/sms-agent/internal/process-pending",
      { limit }
    );
  },
});
```

- [ ] **Step 2: Run Trigger typecheck**

Run:

```bash
npm --prefix trigger run typecheck
```

Expected: PASS.

## Task 8: Add Mission Control Review Surface

**Files:**
- Modify: `app/services/mission_control_service.py`
- Modify: `app/models/mission_control.py`
- Modify: `apps/mission-control/src/lib/api.ts`
- Modify: `apps/mission-control/src/pages/InboxPage.tsx`
- Modify: `apps/mission-control/src/components/ConversationThread.tsx`
- Modify: `tests/services/test_mission_control_service.py`
- Modify: `apps/mission-control/src/pages/InboxPage.test.tsx`

- [ ] **Step 1: Backend test for SMS-agent decision in inbox detail**

Add to `tests/services/test_mission_control_service.py`:

```python
def test_get_inbox_includes_sms_agent_decision_summary() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    service = MissionControlService(client=client)
    base_time = datetime(2026, 5, 16, 14, 0, tzinfo=UTC)
    thread = MissionControlThreadRecord(
        business_id="limitless",
        environment="dev",
        channel="sms",
        status="open",
        unread_count=1,
        contact=MissionControlContactRecord(display_name="Maya Lead", phone="+15551234567"),
        messages=[
            MissionControlMessageRecord(
                direction="inbound",
                channel="sms",
                body="Can you call me?",
                created_at=base_time,
            )
        ],
        context={
            "reply_needs_review": True,
            "sms_agent": {
                "intent": "interested",
                "source_lane": "outbound_probate",
                "temperature": "warm",
                "urgency": "normal",
                "action": "draft_only",
                "suggested_body": "Thanks. I will have a human review and follow up.",
            },
        },
        created_at=base_time,
        updated_at=base_time,
    )
    service.upsert_thread_projection(thread)

    response = service.get_inbox(business_id="limitless", environment="dev", selected_thread_id=thread.id)

    detail = response.threads_by_id[thread.id]
    assert detail.sms_agent["intent"] == "interested"
    assert detail.sms_agent["action"] == "draft_only"
```

- [ ] **Step 2: Frontend test for decision display**

Add a fixture thread with `smsAgent` fields to `apps/mission-control/src/pages/InboxPage.test.tsx` and assert the page renders:

```tsx
expect(screen.getByText("interested")).toBeInTheDocument();
expect(screen.getByText("outbound_probate")).toBeInTheDocument();
expect(screen.getByText(/human review and follow up/i)).toBeInTheDocument();
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run pytest tests/services/test_mission_control_service.py::test_get_inbox_includes_sms_agent_decision_summary -q
npm --prefix apps/mission-control run test -- --run InboxPage
```

Expected: FAIL before model/API/UI mapping.

- [ ] **Step 4: Add model/API/UI mapping**

Add `sms_agent: dict[str, object] | None = None` to the selected inbox detail model. Map it in `apps/mission-control/src/lib/api.ts` as `smsAgent`. In `InboxPage.tsx`, render a compact decision block in the selected thread tools area.

Buttons for this slice:

- `Approve send`
- `Edit`
- `Suppress`
- `Assign callback`

Wire buttons to disabled placeholders with visible state until Task 9 adds API actions.

- [ ] **Step 5: Run backend and frontend tests**

Run:

```bash
uv run pytest tests/services/test_mission_control_service.py::test_get_inbox_includes_sms_agent_decision_summary -q
npm --prefix apps/mission-control run test -- --run InboxPage
```

Expected: PASS.

## Task 9: Add Operator Actions and Eval Labels

**Files:**
- Modify: `app/api/sms_agent.py`
- Modify: `app/services/sms_agent_service.py`
- Modify: `app/models/sms_agent.py`
- Modify: `app/db/sms_agent.py`
- Modify: `tests/api/test_sms_agent.py`

- [ ] **Step 1: Write API tests for labels and approval**

Add tests that:

- `POST /sms-agent/decisions/{decision_id}/labels` requires runtime auth and stores a label.
- `POST /sms-agent/decisions/{decision_id}/approve-send` requires runtime auth, requires `operator_approval=true`, and sends only through `SmsAgentService.send_message`.

Use an in-memory repository and stub sender. Assert no send occurs when `operator_approval=false`.

- [ ] **Step 2: Add models**

Add:

```python
class SmsAgentEvalLabelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    reviewer: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsAgentApproveSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_approval: bool = False
    edited_body: str | None = Field(default=None, min_length=1)
```

- [ ] **Step 3: Implement repository label storage**

Add `record_eval_label` and `list_eval_labels` to `SmsAgentRepository`.

- [ ] **Step 4: Implement approval send**

`approve_send(decision_id, request)` must:

- Load decision and job.
- Require `operator_approval is True`.
- Use `edited_body` or `decision.suggested_body`.
- Require a resolved `contact_id`.
- Call existing `send_message` with `sms_consent_confirmed=True` only if the stored decision/contact context supports SMS consent.
- Record send result in decision metadata or a follow-up decision row.

- [ ] **Step 5: Run API tests**

Run:

```bash
uv run pytest tests/api/test_sms_agent.py -q
```

Expected: PASS.

## Task 10: Add Obsidian/JSONL Archive Export

**Files:**
- Create: `scripts/sms_agent_archive_export.py`
- Create: `tests/scripts/test_sms_agent_archive_export.py`
- Modify: `README.md`

- [ ] **Step 1: Write redaction/export test**

Create `tests/scripts/test_sms_agent_archive_export.py`:

```python
from pathlib import Path

from scripts.sms_agent_archive_export import redact_entry, write_archive


def test_sms_agent_archive_redacts_phone_and_email(tmp_path: Path) -> None:
    entry = {
        "from_number": "+15551234567",
        "email": "owner@example.com",
        "body": "Call me at 555-123-4567",
        "intent": "interested",
    }

    redacted = redact_entry(entry)

    assert "+15551234567" not in str(redacted)
    assert "owner@example.com" not in str(redacted)
    assert "[phone]" in redacted["body"]
    assert redacted["intent"] == "interested"


def test_sms_agent_archive_writes_markdown_and_jsonl(tmp_path: Path) -> None:
    write_archive(
        root=tmp_path,
        date_key="2026-05-16",
        entries=[{"decision_id": "smsdec_1", "intent": "interested", "body": "Call me at [phone]"}],
    )

    assert (tmp_path / "2026" / "05" / "2026-05-16.md").exists()
    assert (tmp_path / "2026" / "05" / "2026-05-16.sms-agent-corpus.jsonl").exists()
```

- [ ] **Step 2: Implement export script**

Create a script with:

- `redact_entry(entry: dict[str, object]) -> dict[str, object]`
- `write_archive(root: Path, date_key: str, entries: list[dict[str, object]]) -> None`
- CLI args: `--root`, `--date`, `--business-id`, `--environment`, `--dry-run`

Default root should require an explicit `--root` or `SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT`; do not guess paths in production.

- [ ] **Step 3: Run script tests**

Run:

```bash
uv run pytest tests/scripts/test_sms_agent_archive_export.py -q
```

Expected: PASS.

## Task 11: Add Smoke and Provider Setup Runbook

**Files:**
- Create: `scripts/smoke/textgrid_sms_reply_agent_smoke.py`
- Modify: `README.md`
- Create: `docs/runbooks/textgrid-sms-reply-agent-activation.md`
- Create: `docs/qc/2026-05-16/textgrid-sms-reply-agent/REPORT.md`

- [ ] **Step 1: Create smoke script**

The smoke script should support:

```bash
uv run python scripts/smoke/textgrid_sms_reply_agent_smoke.py \
  --runtime-url http://localhost:8000 \
  --webhook-secret whsec_123 \
  --from +15551234567 \
  --to +13467725914 \
  --body "Can you call me?"
```

It should:

- Build Twilio-style signature.
- POST form payload to `/sms-agent/webhooks/textgrid` without bearer auth.
- Assert `200`.
- Call protected `/sms-agent/internal/process-pending` with bearer auth when `--runtime-api-key` is provided.
- Print sanitized JSON only.

- [ ] **Step 2: Document TextGrid dashboard setup**

In `docs/runbooks/textgrid-sms-reply-agent-activation.md`, include:

```markdown
# TextGrid SMS Reply Agent Activation

1. Set TextGrid number inbound webhook to `https://<ares-runtime>/sms-agent/webhooks/textgrid`.
2. Set TextGrid status callback to `https://<ares-runtime>/sms-agent/webhooks/textgrid`.
3. Confirm whether TextGrid sends `X-Twilio-Signature`, `X-TextGrid-Signature`, or both.
4. Keep `PROVIDER_LIVE_SENDS_ENABLED=false` and `SMS_AGENT_AUTO_REPLIES_ENABLED=false` for first ingest smoke.
5. Send one owned-number inbound SMS.
6. Verify provider webhook receipt, message row, SMS-agent job, decision, and Mission Control review item.
7. Only after Martin approves, enable one owned-number deterministic auto-ack smoke.
8. Poll/consume TextGrid delivery status before claiming delivery.
```

- [ ] **Step 3: Run focused smoke in local app context**

If a local server is already running, use it. If not, start it only for the smoke and shut it down after.

Run:

```bash
uv run pytest tests/api/test_sms_agent.py tests/services/test_sms_agent_processing.py tests/services/test_sms_reply_agent_service.py -q
git diff --check
```

Expected: PASS.

## Task 12: Final Verification Gate

**Files:**
- All changed files
- `docs/qc/2026-05-16/textgrid-sms-reply-agent/`

- [ ] **Step 1: Focused backend verification**

Run:

```bash
uv run pytest \
  tests/api/test_sms_agent.py \
  tests/services/test_sms_agent_service.py \
  tests/services/test_sms_agent_processing.py \
  tests/services/test_sms_reply_agent_service.py \
  tests/services/test_sms_reply_agent_repository.py \
  tests/services/test_inbound_sms_service.py \
  tests/scripts/test_sms_agent_archive_export.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Full backend verification**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 3: Frontend verification**

Run:

```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

Expected: PASS.

- [ ] **Step 4: Trigger verification**

Run:

```bash
npm --prefix trigger run typecheck
```

Expected: PASS.

- [ ] **Step 5: Diff hygiene**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intentional changed files.

- [ ] **Step 6: Commit**

Commit in small logical chunks:

```bash
git add app tests supabase trigger scripts docs README.md CONTEXT.md memory.md
git commit -m "Add TextGrid SMS reply agent runtime"
```

## Self-Review Checklist

- Spec coverage: webhook ingest, TextGrid contract verification, Supabase source of truth, Obsidian/cold archive, always-on processor, Mission Control review, live-send gates, tests, and activation runbook are covered.
- Placeholder scan: no planned implementation step relies on an unspecified component.
- Type consistency: job, decision, eval, and process names use the `SmsAgent...` prefix consistently.
- Safety: automatic replies stay disabled until `PROVIDER_LIVE_SENDS_ENABLED=true` and `SMS_AGENT_AUTO_REPLIES_ENABLED=true`.
- Provider callbacks: public webhook uses provider signature validation, not runtime query tokens.
