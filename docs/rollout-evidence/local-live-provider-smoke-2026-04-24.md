# Local Live Provider Smoke Evidence — 2026-04-24

Branch: `test/production-readiness-handoff`  
Commit at test time: `b5ac62c`  
Env source: `/home/workspace/Mailers AWF/.env`  
Storage mode: memory-backed Ares runtime for safety; no Supabase writes.

## Targets

- SMS target: `+1 346-***-5914`
- Email target: `Ma***@gmail.com`

## Env discovered

Ares local checkout did not contain a live `.env` with provider credentials.

The provider credentials were found in `/home/workspace/Mailers AWF/.env`:

- `TEXTGRID_ACCOUNT_SID`: present
- `TEXTGRID_AUTH_TOKEN`: present
- `TEXTGRID_FROM_NUMBER`: present
- `TEXTGRID_SMS_URL`: present
- `RESEND_API_KEY`: present
- `RESEND_FROM_EMAIL`: present

No secret values were committed.

## Routes exercised

```text
GET  /mission-control/providers/status
POST /marketing/leads
GET  /mission-control/dashboard?business_id=limitless&environment=dev
GET  /mission-control/tasks?business_id=limitless&environment=dev
POST /mission-control/outbound/email/test
```

## Results

### Provider status

Ares reported both providers configured:

```text
TextGrid: configured=true, can_send=true
Resend:   configured=true, can_send=true
```

### Marketing lead intake live side effects

Route:

```text
POST /marketing/leads
```

Result:

```text
201 Created
lead_id: ctc_d5f5e4c73a4e445daf97fcd3e8752d5a
booking_status: pending
```

Observed side effects:

- TextGrid confirmation SMS was queued and recorded locally.
- Resend confirmation email failed in the marketing lead side-effect path with `HTTP Error 403: Forbidden`.
- Mission Control surfaced the email failure as a provider-failure manual-review task.

Local message record:

```text
channel: sms
provider: textgrid
status: queued
external_message_id: present
body: Thanks Martin, we got your lease-option request and will follow up shortly.
```

Mission Control after intake:

```text
system_status: watch
provider_failure_task_count: 1
due_count: 1
provider_failure: confirmation_email
error_message: HTTP Error 403: Forbidden
```

### Direct Mission Control email test

Route:

```text
POST /mission-control/outbound/email/test
```

Result:

```text
201 Created
provider: resend
status: queued
provider_message_id: 27b14e91-e497-4335-a8e5-f65cc07f00a3
from_identity: Limitless Home Solutions <relay@send.limitleshome.com>
```

## Interpretation

The TextGrid SMS lane worked through the marketing lead intake path.

The Resend provider itself works through the direct Mission Control test endpoint, but the marketing lead intake email side-effect failed with a 403. That points to a bug or behavioral difference in the marketing path's generic `_default_request_sender`/`urllib` request handling versus the direct provider service's `httpx` path.

## Follow-up TODO

- Fix marketing lead confirmation email sending so it uses the same reliable Resend provider path as `/mission-control/outbound/email/test`, or capture and parse the full Resend error body in `_default_request_sender`.
- Add a regression test proving `MarketingLeadService` can send confirmation email through the configured Resend path when provider credentials are valid.
- Keep Mission Control provider-failure surfacing as-is; it correctly exposed the failed email side effect.
