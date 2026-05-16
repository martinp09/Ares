# Slack Notification Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add production-safe Slack notification routing for Ares source pulls, hot enriched leads, Instantly replies, lease-option website leads, inbound SMS replies, and incoming calls.

**Architecture:** Build one reusable Slack notification service with explicit route/channel config, durable dedupe, and safe failure recording. Wire existing runtime seams into that service without changing outbound prospecting gates or making Slack the source of truth.

**Tech Stack:** Python, FastAPI, Pydantic settings, Supabase/Postgres migrations, existing repository pattern, Trigger.dev runtime contracts, pytest.

---

## File Map

- Create: `app/models/slack_notifications.py`
  Defines route names, notification payload/result models, and safe message payloads.
- Create: `app/db/slack_notifications.py`
  Adds in-memory and Supabase-backed notification attempt persistence/dedupe.
- Create: `app/services/slack_notification_service.py`
  Resolves channels, formats messages, posts to Slack, records delivery status.
- Modify: `app/core/config.py`
  Adds `SLACK_NOTIFICATIONS_ENABLED` and route-specific channel env vars.
- Modify: `app/services/nightly_lead_machine_service.py`
  Sends source-run digest and hot-lead alerts after morning brief/enrichment.
- Modify: `app/models/source_runs.py`
  Adds `notifications: list[dict[str, Any]]` to `NightlySourcePullResponse`.
- Modify: `app/services/lead_webhook_service.py`
  Sends Instantly reply/status notifications after canonical event creation.
- Modify: `app/services/marketing_lead_service.py`
  Replaces lease-option-only Slack notifier with shared route service.
- Modify: `app/services/inbound_sms_service.py`
  Sends inbound SMS notifications.
- Modify: `app/services/vapi_call_service.py`
  Sends incoming/call-ended notifications for accepted Vapi webhooks.
- Create: `supabase/migrations/20260515093000_slack_notifications.sql`
  Adds durable Slack notification attempts.
- Create: `scripts/slack_notification_readiness.py`
  Validates env/channel readiness and renders dry-run examples.
- Modify: `scripts/activation_readiness.py`
  Includes the expanded Slack notification readiness gate.
- Modify: `README.md`, `.env.example`, `CONTEXT.md`, `memory.md`
  Documents env, routes, activation, and current status.
- Test: `tests/services/test_slack_notification_service.py`
- Test: `tests/db/test_slack_notifications_repository.py`
- Test: `tests/services/test_nightly_lead_machine_service.py`
- Test: `tests/services/test_probate_write_path_service.py`
- Test: `tests/services/test_marketing_provider_notifications.py`
- Test: `tests/services/test_inbound_sms_service.py`
- Test: `tests/services/test_vapi_call_service.py`
- Test: `tests/api/test_runtime_config_contract.py`

---

### Task 1: Config Contract

**Files:**
- Modify: `app/core/config.py`
- Modify: `tests/api/test_runtime_config_contract.py`
- Modify: `.env.example`

- [ ] **Step 1: Write failing config test**

Add this test to `tests/api/test_runtime_config_contract.py`:

```python
def test_slack_notification_route_settings_default_safe(monkeypatch) -> None:
    for name in (
        "SLACK_NOTIFICATIONS_ENABLED",
        "SLACK_CHANNEL_LEAD_RUNS",
        "SLACK_CHANNEL_INSTANTLY_REPLIES",
        "SLACK_CHANNEL_LEASE_OPTION_INBOUND",
        "SLACK_CHANNEL_SMS_CALLS",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.slack_notifications_enabled is False
    assert settings.slack_channel_lead_runs is None
    assert settings.slack_channel_instantly_replies is None
    assert settings.slack_channel_lease_option_inbound is None
    assert settings.slack_channel_sms_calls is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/api/test_runtime_config_contract.py::test_slack_notification_route_settings_default_safe -q
```

Expected: FAIL because `Settings` has no `slack_notifications_enabled`.

- [ ] **Step 3: Add settings fields**

Add to `Settings` near the existing Slack fields in `app/core/config.py`:

```python
    slack_notifications_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("slack_notifications_enabled", "SLACK_NOTIFICATIONS_ENABLED"),
    )
    slack_channel_lead_runs: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_lead_runs", "SLACK_CHANNEL_LEAD_RUNS"),
    )
    slack_channel_instantly_replies: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_instantly_replies", "SLACK_CHANNEL_INSTANTLY_REPLIES"),
    )
    slack_channel_lease_option_inbound: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_lease_option_inbound", "SLACK_CHANNEL_LEASE_OPTION_INBOUND"),
    )
    slack_channel_sms_calls: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_sms_calls", "SLACK_CHANNEL_SMS_CALLS"),
    )
```

- [ ] **Step 4: Document env defaults**

Add to `.env.example`:

```env
SLACK_NOTIFICATIONS_ENABLED=false
SLACK_BOT_TOKEN=
SLACK_CHANNEL_LEAD_RUNS=
SLACK_CHANNEL_HOT_LEADS=
SLACK_CHANNEL_INSTANTLY_REPLIES=
SLACK_CHANNEL_LEASE_OPTION_INBOUND=
SLACK_CHANNEL_SMS_CALLS=
SLACK_CHANNEL_ERRORS=
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
uv run pytest tests/api/test_runtime_config_contract.py::test_slack_notification_route_settings_default_safe -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/core/config.py tests/api/test_runtime_config_contract.py .env.example
git commit -m "Add Slack notification config"
```

### Task 2: Durable Slack Notification Repository

**Files:**
- Create: `app/models/slack_notifications.py`
- Create: `app/db/slack_notifications.py`
- Create: `supabase/migrations/20260515093000_slack_notifications.sql`
- Create: `tests/db/test_slack_notifications_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/db/test_slack_notifications_repository.py`:

```python
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.slack_notifications import SlackNotificationsRepository
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute


def test_repository_dedupes_by_scope_route_and_key() -> None:
    repo = SlackNotificationsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore()))
    attempt = SlackNotificationAttempt(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.HOT_LEADS,
        dedupe_key="hot:run_1",
        channel_id="CHOT",
        status="sent",
        slack_message_ts="171234.567",
    )

    first = repo.record_attempt(attempt)
    second = repo.record_attempt(attempt.model_copy(update={"slack_message_ts": "999.000"}))

    assert first.deduped is False
    assert second.deduped is True
    assert second.slack_message_ts == "171234.567"


def test_repository_records_failed_attempt() -> None:
    repo = SlackNotificationsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore()))
    attempt = SlackNotificationAttempt(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.INSTANTLY_REPLIES,
        dedupe_key="reply:evt_1",
        channel_id="CREPLIES",
        status="failed",
        error_message="channel_not_found",
    )

    recorded = repo.record_attempt(attempt)

    assert recorded.status == "failed"
    assert recorded.error_message == "channel_not_found"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/db/test_slack_notifications_repository.py -q
```

Expected: FAIL because the model/repository files do not exist.

- [ ] **Step 3: Add model**

Create `app/models/slack_notifications.py`:

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id, utc_now


class SlackNotificationRoute(StrEnum):
    LEAD_RUNS = "lead_runs"
    HOT_LEADS = "hot_leads"
    INSTANTLY_REPLIES = "instantly_replies"
    LEASE_OPTION_INBOUND = "lease_option_inbound"
    SMS_CALLS = "sms_calls"
    ERRORS = "errors"


SlackNotificationStatus = Literal["skipped", "sent", "failed"]


class SlackNotificationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("slack_notice"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    route: SlackNotificationRoute
    dedupe_key: str = Field(min_length=1)
    channel_id: str | None = None
    status: SlackNotificationStatus
    slack_message_ts: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    sent_at: str | None = None
    deduped: bool = False
```

- [ ] **Step 4: Add repository**

Create `app/db/slack_notifications.py` following the existing repository style:

```python
from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import InMemoryControlPlaneClient, control_plane_client
from app.db.supabase_rest import fetch_rows, insert_rows
from app.models.slack_notifications import SlackNotificationAttempt


class SlackNotificationsRepository:
    def __init__(
        self,
        client: InMemoryControlPlaneClient | None = None,
        *,
        settings: Settings | None = None,
        force_memory: bool = False,
    ) -> None:
        self.client = client or control_plane_client
        self.settings = settings or get_settings()
        self.force_memory = force_memory

    def _use_supabase(self) -> bool:
        return (
            not self.force_memory
            and self.settings.control_plane_backend == "supabase"
            and bool(self.settings.supabase_url and self.settings.supabase_service_role_key)
        )

    def record_attempt(self, attempt: SlackNotificationAttempt) -> SlackNotificationAttempt:
        if not self._use_supabase():
            store = self.client.store
            attempts: dict[str, SlackNotificationAttempt] = getattr(store, "slack_notifications", {})
            keys: dict[tuple[str, str, str, str], str] = getattr(store, "slack_notification_keys", {})
            setattr(store, "slack_notifications", attempts)
            setattr(store, "slack_notification_keys", keys)
            key = (attempt.business_id, attempt.environment, str(attempt.route), attempt.dedupe_key)
            existing_id = keys.get(key)
            if existing_id:
                return attempts[existing_id].model_copy(update={"deduped": True})
            attempts[attempt.id] = attempt
            keys[key] = attempt.id
            return attempt

        existing = fetch_rows(
            "slack_notifications",
            params={
                "select": "*",
                "business_id": f"eq.{attempt.business_id}",
                "environment": f"eq.{attempt.environment}",
                "route": f"eq.{attempt.route}",
                "dedupe_key": f"eq.{attempt.dedupe_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            return _from_row(existing[0]).model_copy(update={"deduped": True})
        row = insert_rows("slack_notifications", [_to_row(attempt)], select="*", settings=self.settings)[0]
        return _from_row(row)


def _to_row(attempt: SlackNotificationAttempt) -> dict[str, Any]:
    payload = attempt.model_dump(mode="json", exclude={"deduped"})
    payload["route"] = str(attempt.route)
    return payload


def _from_row(row: dict[str, Any]) -> SlackNotificationAttempt:
    return SlackNotificationAttempt.model_validate(row)
```

- [ ] **Step 5: Add migration**

Create `supabase/migrations/20260515093000_slack_notifications.sql`:

```sql
create table if not exists public.slack_notifications (
  id text primary key,
  business_id text not null,
  environment text not null,
  route text not null,
  dedupe_key text not null,
  channel_id text,
  status text not null check (status in ('skipped', 'sent', 'failed')),
  slack_message_ts text,
  payload jsonb not null default '{}'::jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  unique (business_id, environment, route, dedupe_key)
);

create index if not exists idx_slack_notifications_scope_route_created
  on public.slack_notifications (business_id, environment, route, created_at desc);

alter table public.slack_notifications enable row level security;
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/db/test_slack_notifications_repository.py tests/db/test_migrations.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/models/slack_notifications.py app/db/slack_notifications.py supabase/migrations/20260515093000_slack_notifications.sql tests/db/test_slack_notifications_repository.py
git commit -m "Add Slack notification persistence"
```

### Task 3: Slack Notification Service

**Files:**
- Create: `app/services/slack_notification_service.py`
- Create: `tests/services/test_slack_notification_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/services/test_slack_notification_service.py`:

```python
from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.slack_notifications import SlackNotificationsRepository
from app.models.slack_notifications import SlackNotificationRoute
from app.services.slack_notification_service import SlackNotificationService


def build_service(settings: Settings, sent: list[dict]) -> SlackNotificationService:
    repo = SlackNotificationsRepository(
        InMemoryControlPlaneClient(InMemoryControlPlaneStore()),
        settings=settings,
        force_memory=True,
    )

    def sender(request):
        sent.append(request)
        return {"ok": True, "channel": request["payload"]["channel"], "ts": "171234.567"}

    return SlackNotificationService(settings=settings, repository=repo, request_sender=sender)


def test_disabled_slack_notifications_skip_without_posting() -> None:
    sent = []
    service = build_service(Settings(_env_file=None, slack_notifications_enabled=False, slack_bot_token="xoxb"), sent)

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot:1",
        text="Hot lead",
        blocks=[],
    )

    assert result.status == "skipped"
    assert sent == []


def test_configured_route_posts_to_slack_and_records_ts() -> None:
    sent = []
    service = build_service(
        Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        sent,
    )

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot:1",
        text="Hot lead",
        blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "*Hot lead*"}}],
    )

    assert result.status == "sent"
    assert result.channel_id == "CHOT"
    assert result.slack_message_ts == "171234.567"
    assert sent[0]["headers"]["Authorization"] == "Bearer xoxb-test"


def test_duplicate_dedupe_key_skips_second_post() -> None:
    sent = []
    service = build_service(
        Settings(_env_file=None, slack_notifications_enabled=True, slack_bot_token="xoxb-test", slack_channel_hot_leads="CHOT"),
        sent,
    )

    service.notify(route=SlackNotificationRoute.HOT_LEADS, business_id="limitless", environment="prod", dedupe_key="hot:1", text="Hot lead", blocks=[])
    second = service.notify(route=SlackNotificationRoute.HOT_LEADS, business_id="limitless", environment="prod", dedupe_key="hot:1", text="Hot lead", blocks=[])

    assert second.deduped is True
    assert len(sent) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/services/test_slack_notification_service.py -q
```

Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement service**

Create `app/services/slack_notification_service.py`:

```python
from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request

from app.core.config import Settings, get_settings
from app.db.slack_notifications import SlackNotificationsRepository
from app.models.commands import utc_now
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute

RequestSender = Callable[[dict[str, Any]], dict[str, Any] | None]


class SlackNotificationService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        repository: SlackNotificationsRepository | None = None,
        request_sender: RequestSender | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or SlackNotificationsRepository(settings=self.settings)
        self.request_sender = request_sender or _default_sender

    def notify(
        self,
        *,
        route: SlackNotificationRoute,
        business_id: str,
        environment: str,
        dedupe_key: str,
        text: str,
        blocks: list[dict[str, Any]],
        payload: dict[str, Any] | None = None,
    ) -> SlackNotificationAttempt:
        channel_id = self._channel_for(route)
        base = SlackNotificationAttempt(
            business_id=business_id,
            environment=environment,
            route=route,
            dedupe_key=dedupe_key,
            channel_id=channel_id,
            status="skipped",
            payload=payload or {},
        )
        if not self.settings.slack_notifications_enabled or not self.settings.slack_bot_token or not channel_id:
            return self.repository.record_attempt(base)

        existing = self.repository.record_attempt(base)
        if existing.deduped:
            return existing
        try:
            response = self.request_sender(
                {
                    "endpoint": "https://slack.com/api/chat.postMessage",
                    "headers": {
                        "Authorization": f"Bearer {self.settings.slack_bot_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    "payload": {
                        "channel": channel_id,
                        "text": text,
                        "unfurl_links": False,
                        "unfurl_media": False,
                        "blocks": blocks,
                    },
                }
            ) or {}
            if response.get("ok") is False:
                raise RuntimeError(str(response.get("error") or "Slack notification failed"))
            return existing.model_copy(
                update={
                    "status": "sent",
                    "slack_message_ts": str(response.get("ts")) if response.get("ts") else None,
                    "sent_at": utc_now().isoformat(),
                }
            )
        except Exception as exc:
            return existing.model_copy(update={"status": "failed", "error_message": str(exc)})

    def _channel_for(self, route: SlackNotificationRoute) -> str | None:
        if route == SlackNotificationRoute.LEAD_RUNS:
            return self.settings.slack_channel_lead_runs or self.settings.slack_channel_leads
        if route == SlackNotificationRoute.HOT_LEADS:
            return self.settings.slack_channel_hot_leads
        if route == SlackNotificationRoute.INSTANTLY_REPLIES:
            return self.settings.slack_channel_instantly_replies
        if route == SlackNotificationRoute.LEASE_OPTION_INBOUND:
            return self.settings.slack_channel_lease_option_inbound or self.settings.slack_channel_intake
        if route == SlackNotificationRoute.SMS_CALLS:
            return self.settings.slack_channel_sms_calls
        return self.settings.slack_channel_errors


def _default_sender(outbound_request: dict[str, Any]) -> dict[str, Any] | None:
    body = json.dumps(outbound_request["payload"]).encode("utf-8")
    req = request.Request(outbound_request["endpoint"], data=body, headers=outbound_request["headers"], method="POST")
    with request.urlopen(req, timeout=10) as response:  # nosec B310
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else None


slack_notification_service = SlackNotificationService()
```

Before finishing this task, update the repository so sent/failed updates are persisted, not only returned. Add `update_attempt()` to the repository and call it after Slack response/failure.

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/services/test_slack_notification_service.py tests/db/test_slack_notifications_repository.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/slack_notification_service.py tests/services/test_slack_notification_service.py app/db/slack_notifications.py tests/db/test_slack_notifications_repository.py
git commit -m "Add Slack notification service"
```

### Task 4: Lead-Run Digest And Hot-Lead Alerts

**Files:**
- Modify: `app/models/source_runs.py`
- Modify: `app/services/nightly_lead_machine_service.py`
- Modify: `tests/services/test_nightly_lead_machine_service.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/services/test_nightly_lead_machine_service.py`:

```python
def test_nightly_source_pull_posts_lead_run_and_hot_lead_notifications(tmp_path):
    sent = []
    settings = Settings(
        _env_file=None,
        slack_notifications_enabled=True,
        slack_bot_token="xoxb-test",
        slack_channel_lead_runs="CRUNS",
        slack_channel_hot_leads="CHOT",
        lead_machine_artifact_root=str(tmp_path),
    )
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore())),
        settings=settings,
        slack_notifier=_stub_slack_notifier(sent),
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="limitless",
            environment="prod",
            idempotency_key="auto:1",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "source_rows": {
                    "harris": [
                        {
                            "case_number": "500001",
                            "filing_type": "PROBATE OF WILL (INDEPENDENT ADMINISTRATION)",
                            "keep_now": True,
                            "property_address": "123 Hot St",
                            "mailing_address": "123 Hot St",
                            "hcad_candidates": [{"account": "111", "site_address": "123 Hot St", "owner_name": "Estate Of Hot"}],
                        }
                    ]
                },
            },
        )
    )

    assert any(item["route"] == "lead_runs" for item in sent)
    assert any(item["route"] == "hot_leads" for item in sent)
    assert result.notifications
```

The helper `_stub_slack_notifier` should expose a `notify(...)` method and append route/channel payloads to `sent`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/services/test_nightly_lead_machine_service.py::test_nightly_source_pull_posts_lead_run_and_hot_lead_notifications -q
```

Expected: FAIL because `NightlyLeadMachineService` has no Slack notifier or response notifications.

- [ ] **Step 3: Add response notifications field**

Modify `NightlySourcePullResponse` in `app/models/source_runs.py`:

```python
    notifications: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 4: Wire notifier into service**

Modify `NightlyLeadMachineService.__init__`:

```python
from app.services.slack_notification_service import SlackNotificationService, slack_notification_service

...
        slack_notifier: SlackNotificationService | None = None,
...
        self.slack_notifier = slack_notifier or slack_notification_service
```

After the `MorningBrief` is saved, call helper methods:

```python
notifications = []
notifications.append(self._notify_source_run_digest(request=request, brief=brief, response_warnings=response_warnings + brief.warnings))
hot_records = _hot_records_from_enrichment(enrichment_result)
if hot_records:
    notifications.append(self._notify_hot_leads(request=request, hot_records=hot_records, brief=brief))
```

Update the `NightlySourcePullResponse(...)` construction:

```python
notifications=[item for item in notifications if item is not None],
```

- [ ] **Step 5: Implement message builders**

Add helpers in `nightly_lead_machine_service.py`:

```python
def _hot_records_from_enrichment(enrichment_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not enrichment_result:
        return []
    records = [dict(item) for item in enrichment_result.get("records") or [] if isinstance(item, dict)]
    hot = [record for record in records if float(record.get("lead_score") or 0) >= 70]
    return sorted(hot, key=lambda item: float(item.get("lead_score") or 0), reverse=True)
```

Message blocks should include counts, county/source lanes, score, case number, property address, owner/decedent when present, phone/email/contact candidates when present, and next action.

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/services/test_nightly_lead_machine_service.py tests/api/test_nightly_lead_machine.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/models/source_runs.py app/services/nightly_lead_machine_service.py tests/services/test_nightly_lead_machine_service.py tests/api/test_nightly_lead_machine.py
git commit -m "Route lead run Slack notifications"
```

### Task 5: Instantly Reply Channel

**Files:**
- Modify: `app/services/lead_webhook_service.py`
- Modify: `tests/services/test_probate_write_path_service.py`
- Modify: `tests/api/test_lead_machine.py`

- [ ] **Step 1: Write failing service test**

Add a test where an Instantly `reply_received` webhook appends a Slack event:

```python
def test_instantly_reply_posts_to_slack_reply_channel() -> None:
    sent = []
    service = _build_probate_write_path_service_with_slack(sent)
    payload = {
        "event_type": "reply_received",
        "timestamp": "2026-05-15T14:00:00Z",
        "campaign_id": "camp_123",
        "campaign_name": "Probate Wave",
        "lead_email": "lead@example.com",
        "email_id": "msg_reply_123",
        "reply_text": "Yes call me today",
    }

    result = service.handle_instantly_webhook(business_id="limitless", environment="prod", payload=payload)

    assert result["status"] == "processed"
    assert sent[0]["route"] == "instantly_replies"
    assert "Yes call me today" in sent[0]["text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/services/test_probate_write_path_service.py::test_instantly_reply_posts_to_slack_reply_channel -q
```

Expected: FAIL because `LeadWebhookService` does not notify Slack.

- [ ] **Step 3: Add notifier dependency and reply filter**

In `LeadWebhookService.__init__`, accept `slack_notifier`.

After `task = self.task_service.create_task_for_event(...)`, add:

```python
        self._notify_instantly_reply(
            business_id=business_id,
            environment=environment,
            event=event,
            lead=updated_lead,
            campaign=resolved_campaign,
            task_id=task.id if task is not None else None,
        )
```

Only notify for:

```python
_INSTANTLY_OPERATOR_EVENT_TYPES = {
    "lead.reply.received",
    "lead.reply.auto_received",
    "lead.status.interested",
    "lead.status.not_interested",
    "lead.suppressed.unsubscribe",
}
```

- [ ] **Step 4: Preserve dedupe**

Use:

```python
dedupe_key=f"instantly:{event.id or event.idempotency_key}"
```

The Slack service dedupes this key, while `ProviderWebhooksRepository` still dedupes provider retries before the notification path.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/services/test_probate_write_path_service.py tests/api/test_lead_machine.py::test_post_instantly_webhook_is_replay_safe -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/lead_webhook_service.py tests/services/test_probate_write_path_service.py tests/api/test_lead_machine.py
git commit -m "Route Instantly replies to Slack"
```

### Task 6: Lease-Option Website Inbound Channel

**Files:**
- Modify: `app/services/marketing_lead_service.py`
- Modify: `tests/services/test_marketing_provider_notifications.py`
- Modify: `tests/api/test_marketing_leads.py`

- [ ] **Step 1: Update failing tests for separate Slack gate**

Change the current Slack test so Slack posts when `SLACK_NOTIFICATIONS_ENABLED=true`, even if `PROVIDER_LIVE_SENDS_ENABLED=false`, while SMS/email remain skipped.

Expected side effects:

```python
assert side_effects["confirmation_sms"] == "skipped"
assert side_effects["confirmation_email"] == "skipped"
assert side_effects["operator_slack_notification"] == "queued"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/services/test_marketing_provider_notifications.py::test_lead_intake_skips_slack_when_live_sends_are_disabled_even_if_configured -q
```

Expected: FAIL under the new assertion because the existing Slack notifier is tied to `PROVIDER_LIVE_SENDS_ENABLED`.

- [ ] **Step 3: Replace one-off notifier with shared route**

Keep the public `operator_slack_notification` side effect name for API compatibility, but build it through `SlackNotificationService`:

```python
self.slack_notifier = slack_notifier or slack_notification_service
```

Send route:

```python
SlackNotificationRoute.LEASE_OPTION_INBOUND
```

Dedupe key:

```python
f"lease-option-inbound:{lead_id}"
```

Message text:

```python
f"New lease-option website lead: {lead_name} - {payload.property_address}"
```

- [ ] **Step 4: Remove old `_ConfiguredSlackOperatorNotifier`**

Delete the lease-option-specific Slack class and keep only the shared service call. Keep `_NoopOperatorNotifier` only if other tests still rely on the `OperatorNotifier` protocol; otherwise remove the protocol/classes cleanly.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/services/test_marketing_provider_notifications.py tests/api/test_marketing_leads.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/marketing_lead_service.py tests/services/test_marketing_provider_notifications.py tests/api/test_marketing_leads.py
git commit -m "Route lease-option inbound leads to Slack"
```

### Task 7: SMS Replies And Vapi Calls Channel

**Files:**
- Modify: `app/services/inbound_sms_service.py`
- Modify: `app/services/vapi_call_service.py`
- Modify: `tests/services/test_inbound_sms_service.py`
- Modify: `tests/services/test_vapi_call_service.py`
- Modify: `tests/api/test_sms_agent.py`
- Modify: `tests/api/test_voice.py`

- [ ] **Step 1: Write failing inbound SMS test**

Add:

```python
def test_inbound_sms_posts_to_slack_sms_calls_channel() -> None:
    sent = []
    service = build_inbound_sms_service_with_slack(sent)

    result = service.handle_textgrid_webhook(
        {"From": "+17135550100", "To": "+13465550199", "Body": "Call me", "MessageSid": "SM_REPLY_1"},
        signature=None,
        request_url="http://testserver/sms-agent/webhooks/textgrid",
    )

    assert result["event_type"] == "inbound"
    assert sent[0]["route"] == "sms_calls"
    assert "Call me" in sent[0]["text"]
```

- [ ] **Step 2: Write failing Vapi test**

Add:

```python
def test_vapi_call_ended_posts_to_slack_sms_calls_channel() -> None:
    sent = []
    service = build_vapi_service_with_slack(sent)

    result = service.handle_webhook(
        {"type": "call-ended", "call": {"id": "call_123", "status": "ended"}, "summary": "Seller asked for callback."},
        {"X-Vapi-Secret": "expected"},
    )

    assert result["accepted"] is True
    assert sent[0]["route"] == "sms_calls"
    assert "Seller asked for callback" in sent[0]["text"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
uv run pytest tests/services/test_inbound_sms_service.py::test_inbound_sms_posts_to_slack_sms_calls_channel tests/services/test_vapi_call_service.py::test_vapi_call_ended_posts_to_slack_sms_calls_channel -q
```

Expected: FAIL because services do not accept Slack notifier dependencies.

- [ ] **Step 4: Wire inbound SMS notifier**

In `InboundSmsService.__init__`, accept `slack_notifier`. After action resolution for inbound events, call:

```python
self._notify_inbound_sms(event=event, resolved=resolved, action=action)
```

Skip status callbacks:

```python
if event.event_type != "inbound":
    return None
```

Dedupe key:

```python
f"textgrid:{event.external_id or event.from_number + ':' + event.to_number + ':' + event.body.strip().casefold()}"
```

- [ ] **Step 5: Wire Vapi notifier**

In `VapiCallService.__init__`, accept `slack_notifier`. In `handle_webhook`, after the accepted normalized response is built, call Slack for event types:

```python
{"call-started", "call-ended", "end-of-call-report", "transcript", "status-update"}
```

Dedupe key:

```python
f"vapi:{normalized.get('message_id') or normalized.get('provider_call_id') or idempotency_key}:{normalized.get('event_type')}"
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest tests/services/test_inbound_sms_service.py tests/services/test_vapi_call_service.py tests/api/test_sms_agent.py tests/api/test_voice.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/inbound_sms_service.py app/services/vapi_call_service.py tests/services/test_inbound_sms_service.py tests/services/test_vapi_call_service.py tests/api/test_sms_agent.py tests/api/test_voice.py
git commit -m "Route SMS replies and calls to Slack"
```

### Task 8: Readiness Script And Docs

**Files:**
- Create: `scripts/slack_notification_readiness.py`
- Modify: `scripts/activation_readiness.py`
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`

- [ ] **Step 1: Write readiness test or smoke command**

Add a script test if script tests exist; otherwise verify with:

```bash
SLACK_NOTIFICATIONS_ENABLED=false uv run python scripts/slack_notification_readiness.py --json
```

Expected JSON:

```json
{
  "configured": false,
  "would_post": false,
  "missing": ["SLACK_NOTIFICATIONS_ENABLED=true", "SLACK_BOT_TOKEN"]
}
```

- [ ] **Step 2: Implement script**

Create `scripts/slack_notification_readiness.py` that:

- loads `Settings`
- reports each route channel as present/missing
- never prints bot token
- supports `--json`
- supports `--route lead_runs|hot_leads|instantly_replies|lease_option_inbound|sms_calls`
- supports `--render-sample` without posting

- [ ] **Step 3: Extend activation readiness**

Update `scripts/activation_readiness.py` so Slack readiness requires:

- `SLACK_NOTIFICATIONS_ENABLED=true`
- `SLACK_BOT_TOKEN`
- all requested route channels

Keep the old `SLACK_CHANNEL_INTAKE`/`SLACK_CHANNEL_LEADS` compatibility in the report, but mark the route-specific vars as preferred.

- [ ] **Step 4: Document activation**

Add README section:

```markdown
### Slack operator notifications

Slack notifications are disabled by default and independent from prospect-facing send gates.
Set `SLACK_NOTIFICATIONS_ENABLED=true`, invite the Ares Slack bot to each target channel, and configure:
`SLACK_CHANNEL_LEAD_RUNS`, `SLACK_CHANNEL_HOT_LEADS`, `SLACK_CHANNEL_INSTANTLY_REPLIES`,
`SLACK_CHANNEL_LEASE_OPTION_INBOUND`, and `SLACK_CHANNEL_SMS_CALLS`.
```

- [ ] **Step 5: Update router docs**

Keep `CONTEXT.md` under 50 lines. Add current scope and follow-up entries that the Slack notification plan is on `feature/slack-notification-routing` and not yet deployed.

Add a `memory.md` change-log entry with exact branch, spec path, plan path, and no-provider-send/no-VPS-mutation status.

- [ ] **Step 6: Commit**

```bash
git add scripts/slack_notification_readiness.py scripts/activation_readiness.py README.md CONTEXT.md memory.md
git commit -m "Document Slack notification activation"
```

### Task 9: Full Verification And Deployment Prep

**Files:**
- No code edits unless verification fails.

- [ ] **Step 1: Run focused backend tests**

```bash
uv run pytest \
  tests/services/test_slack_notification_service.py \
  tests/db/test_slack_notifications_repository.py \
  tests/services/test_nightly_lead_machine_service.py \
  tests/services/test_probate_write_path_service.py \
  tests/services/test_marketing_provider_notifications.py \
  tests/services/test_inbound_sms_service.py \
  tests/services/test_vapi_call_service.py \
  tests/api/test_lead_machine.py \
  tests/api/test_marketing_leads.py \
  tests/api/test_sms_agent.py \
  tests/api/test_voice.py \
  tests/api/test_runtime_config_contract.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run broader backend suite**

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run Trigger typecheck**

```bash
npm --prefix trigger run typecheck
```

Expected: PASS.

- [ ] **Step 4: Run formatting/whitespace gate**

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 5: Push branch**

```bash
git push -u origin feature/slack-notification-routing
```

- [ ] **Step 6: VPS activation after merge**

After merge to `main`, SSH to `root@100.74.177.6` and apply only env/config changes needed for Slack:

```bash
cd /opt/ares/worktrees/ares-main
git fetch origin --prune
git checkout main
git pull --ff-only origin main
uv run python scripts/slack_notification_readiness.py --json
```

Do not enable `SLACK_NOTIFICATIONS_ENABLED=true` until channel IDs are confirmed and the bot is invited to each channel.

## Self-Review

- Spec coverage: all requested channels are covered by route-specific env vars and producer hooks.
- Placeholder scan: no implementation task depends on an unspecified file or ambiguous route.
- Type consistency: route names match `SlackNotificationRoute` values and env names match `Settings` fields.
- Safety: Slack notifications are independent from prospect-facing send gates and do not enable Instantly, SMS, Vapi, HubSpot, paid skiptrace, or deploy side effects.
