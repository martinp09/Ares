---
status: current
source_of_truth: true
last_verified: 2026-05-04
---

# Tracerfy Skiptrace Integration

Ares now uses Tracerfy as the current deterministic skiptrace provider for CRM record enrichment.

## Provider contract

- Base URL: `https://tracerfy.com/v1/api`
- Auth: `Authorization: Bearer <TRACERFY_API_KEY>`
- Config:
  - `TRACERFY_API_KEY`
  - `TRACERFY_BASE_URL=https://tracerfy.com/v1/api`

## Implemented in Ares

- Provider client: `app/providers/tracerfy.py`
- CRM enrichment service: `app/services/skiptrace_service.py`
- Mission Control endpoint: `POST /mission-control/records/{record_id}/skiptrace`
- Focused tests:
  - `tests/providers/test_tracerfy.py`
  - `tests/services/test_skiptrace_service.py`

## First supported lookup path

The first slice uses Tracerfy synchronous lookups so Mission Control can enrich one CRM record at a time without starting a batch queue:

1. If the CRM record has APN-style facts, Ares calls:
   - `POST /v1/api/trace/parcel/lookup/`
   - payload: `parcel_id`, `county`, `state`
2. Otherwise Ares calls:
   - `POST /v1/api/trace/lookup/`
   - payload: `address`, `city`, `state`, optional `zip`, `find_owner=true`
3. Ares stores the provider response under `record.raw_payload.tracerfy_skiptrace_response`.
4. Ares stores a compact evidence summary under `record.facts.skiptrace`.
5. If the record was `needs_skip_trace` and Tracerfy returns a phone or email, Ares moves it to `clean`.

## Tracerfy docs summary

From `https://tracerfy.com/skip-tracing-api-documentation/`:

- `POST /v1/api/trace/lookup/`
  - synchronous single-address skip trace
  - 5 credits per hit, 0 credits on miss
  - 500 RPM per user
  - `find_owner=true` finds property owner from address; `find_owner=false` requires first/last name
  - returns persons with phones, phone DNC status, carrier, rank, emails, deceased flag, property-owner flag, litigator flag, and mailing address
- `POST /v1/api/trace/parcel/lookup/`
  - synchronous APN/parcel skip trace
  - 5 credits per hit, 0 credits on miss
  - requires `parcel_id`, `county`, `state`
- `POST /v1/api/trace/`
  - async batch trace via CSV or JSON
  - normal trace: 1 credit/lead; advanced trace: 2 credits/lead
  - rate limit: 10 POST trace requests per 5-minute window
  - returns `queue_id`; results are available via queue/download URL
- `GET /v1/api/queues/` and `GET /v1/api/queue/:id`
  - batch queue list/detail
- Batch webhooks
  - Tracerfy POSTs completion payloads to `Account.webhook_url`; no registration endpoint needed
- `POST /v1/api/dnc/lookup/`
  - synchronous single-phone DNC check
  - 5 credits per lookup
- `POST /v1/api/dnc/scrub/`
  - async batch DNC scrub
  - 1 credit per phone checked
- `POST /v1/api/lead-builder/autocomplete/`
  - free address validation/preflight
  - 30 RPM per account
- `POST /v1/api/lead-builder/lookup/`
  - full property dossier + skip trace
  - 10 credits per property hit

## Safety / outreach boundary

Tracerfy enrichment only creates contact candidates and evidence. It does **not** enroll leads into Instantly/TextGrid, send outreach, call numbers, or bypass approval gates. Provider enrollment remains separate and approval-gated.

## Next slice

- Add batch queue submission/polling for HOT/WARM campaign exports once single-record enrichment is proven.
- Add Tracerfy webhook receiver if batch enrichment becomes the default path.
- Add DNC scrub workflow before SMS/calling workflows use Tracerfy phones at scale.
