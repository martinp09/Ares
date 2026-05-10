# SMS Confirmation-Only Intake Copy — 2026-05-10

## Scope

Martin clarified that the landing page already redirects sellers to Cal.com after form submit. Ares should therefore keep TextGrid SMS as confirmation-only, with no booking/Cal.com link in SMS. Email can keep the booking-link fallback.

## Changed

- `app/services/marketing_lead_service.py`
  - TextGrid SMS now uses a dedicated SMS-only confirmation body:
    - `Thanks {first_name}, we received your request. We'll follow up shortly. Reply STOP to opt out.`
  - Resend email continues using the booking-link confirmation copy.
- `tests/api/test_marketing_leads.py`
  - Regression coverage now asserts SMS excludes `cal.com` and the booking URL while email includes the booking URL.
- `tests/services/test_marketing_provider_notifications.py`
  - Updated speed-to-lead provider test to the same channel split.
- Living docs updated: `CONTEXT.md`, `TODO.md`, `memory.md`, `docs/activation-readiness-handoff.md`.

## Why

This lowers SMS content-filter/compliance risk after the live TextGrid diagnostic showed provider-side content filtering. The intended seller flow is:

1. Form submit.
2. Landing page redirects to Cal.com.
3. SMS only confirms receipt.
4. Email may include the booking link fallback.

## Verification

- RED: `tests/api/test_marketing_leads.py::test_marketing_lead_service_dispatches_configured_provider_requests` failed before code change because SMS still included the booking URL.
- Focused: `uv run pytest tests/api/test_marketing_leads.py tests/services/test_marketing_provider_notifications.py -q` → `19 passed`.
- Full backend: `uv run pytest -q` → `654 passed`.
- No live sends were run in this slice.

## Remaining gap

Before broad live launch, run an explicitly approved TextGrid live smoke of the final confirmation-only SMS and poll final TextGrid status/callbacks before claiming delivery.
