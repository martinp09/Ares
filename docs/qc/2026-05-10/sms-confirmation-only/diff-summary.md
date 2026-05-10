# Diff Summary

## Code

- `app/services/marketing_lead_service.py`
  - Added `_build_sms_confirmation_message()` for SMS-only confirmation copy.
  - TextGrid confirmation path now calls the SMS-only helper instead of the booking-link confirmation helper.
  - Email path remains on `_build_confirmation_message(..., booking_url=...)`.

## Tests

- `tests/api/test_marketing_leads.py`
  - Asserts SMS payload body has no `cal.com`/booking URL.
  - Asserts Resend email body keeps the booking URL.
- `tests/services/test_marketing_provider_notifications.py`
  - Renamed provider bundle test to confirmation-only SMS + booking-link email semantics.
  - Asserts SMS and email bodies intentionally differ by channel.

## Docs/QC

- `CONTEXT.md`, `TODO.md`, `memory.md`
  - Updated current source-of-truth messaging rule.
- `docs/activation-readiness-handoff.md`
  - Updated TextGrid delivery proof rules and confirmation-only SMS guidance.
- `docs/qc/2026-05-10/sms-confirmation-only/`
  - Added this report plus captured focused/full test output.
