# Phase 6 Vapi Call Layer Diff Summary

## Created

- `app/providers/vapi.py` — Vapi HTTP adapter, request builder, sanitized errors, webhook secret verification, webhook normalization.
- `app/models/calls.py` — typed outbound call/list/webhook request and response models.
- `app/services/vapi_call_service.py` — dry-run preview, gated dispatch, redacted live response summaries, provider-link write on returned call ID, webhook handling.
- `app/api/voice.py` — `/voice` routes for assistants, phone numbers, outbound calls, and Vapi webhook.
- `tests/providers/test_vapi.py` — adapter/header/repr/error/webhook helper fake tests, including configured-key sanitization assertions.
- `tests/services/test_vapi_call_service.py` — service dry-run/gate/fake-dispatch/link/error/webhook tests, including live success/skip/submitted-unlinked/error payload-redaction assertions and request-value error-message redaction regressions.
- `tests/api/test_voice.py` — API route, dry-run, gate, redacted fake dispatch, serialized error-response redaction, webhook-secret tests.
- `docs/qc/2026-05-14/vapi-call-layer/` — QC artifacts.

## Modified

- `app/core/config.py` — added Phase 6 Vapi env/settings and webhook signature gate.
- `.env.example` — documented active Phase 6 Vapi env names/default false gates.
- `app/main.py` — mounted the `/voice` router.
- `tests/conftest.py` — forced Vapi env and webhook gate defaults to safe/off during tests.
- `CONTEXT.md` — added recent Phase 6 note.
- `memory.md` — added Phase 6 changelog entry.
- `docs/superpowers/plans/2026-05-14-hubspot-operating-spine-agentic-company-plan.md` — corrected stale retired Vapi live-calls gate reference to `VAPI_PROVIDER_LIVE_SENDS_ENABLED`.

## Fix-lane changes

- Full Vapi payload is retained only for `dry_run=True` preview responses.
- Live dispatch, existing-link skip, submitted-unlinked, and provider-error responses expose only a redacted payload summary plus action/call IDs/provider link IDs/warnings/error.
- Sanitization paths now redact configured Vapi API/private key values from transport/provider errors.
- Outbound error responses now also redact current request/payload values (`to_number`, `from_number`, `customer_name`, assistant ID, phone number ID, scalar metadata values, `crm_record_id`, `opportunity_id`, `task_id`) before returning `error_message`.
- `git diff --check` passed.
