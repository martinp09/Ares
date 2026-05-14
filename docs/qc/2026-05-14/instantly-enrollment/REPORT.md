# Instantly Enrollment Phase 5 QC Report

Date: 2026-05-14

## Scope

Phase 5 gated Instantly enrollment preview/apply backend slice, plus REQUEST_CHANGES hardening for enrollment reporting, idempotency, provider batch-result sanitization, request validation, and QC artifacts. Fake-client tests only.

## Result

PASS.

## Coverage

- Config gate remains: `INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=false` default.
- Mission Control endpoints:
  - `POST /mission-control/providers/instantly/enrollments/preview`
  - `POST /mission-control/providers/instantly/enrollments/apply`
- Preview is dry-run only: no provider calls, no provider-link writes, no token required.
- Apply gates before provider calls/link writes:
  1. operator approval
  2. `PROVIDER_LIVE_SENDS_ENABLED`
  3. `INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED`
  4. `INSTANTLY_API_KEY`
- Apply request validates exactly one Instantly provider target (`instantly_campaign_id` or `instantly_list_id`) and caps enrollment request records at 500.
- Eligibility covers missing email, suppressed/archived status, verification status allowlist, facts/raw payload fallback, explicit `allow_unverified`, existing-link idempotency, and no-eligible no-call behavior.
- Existing Instantly lead provider links now skip duplicate enrollment for the same Ares `crm_record` regardless of missing/changed `sync_hash`.
- Confirmed enrollment reporting now counts only records linked with a returned per-lead provider ID in `enrolled_count`; submitted-but-unlinked records use `action="submitted_unlinked"` and increment `submitted_count` without overclaiming confirmed enrollment.
- Provider links are written only when a per-lead provider ID is present in the fake/provider response.
- Provider batch result output is summary-only (`type`, top-level count fields/collection lengths, per-lead ID count, `omitted_raw_payload=true`) and does not expose raw echoed emails, phones, payloads, or provider internals.

## Commands

```bash
python -m pytest tests/services/test_instantly_enrollment_service.py tests/api/test_mission_control_instantly_enrollment.py tests/providers/test_instantly.py tests/services/test_lead_outbound_service.py tests/db/test_provider_links_repository.py -q
python -m pytest -q
git diff --check
```

## Results

- Focused Phase 5/provider-link/outbound suite: `38 passed in 1.34s`
- Full backend suite: `705 passed in 21.27s`
- Whitespace check: `git diff --check` passed with no output.

## Provider Safety

No live Instantly provider calls were made. Tests use fake/injected clients only. No secrets were added to code, tests, or QC artifacts.

## Artifact Tracking

This QC folder is currently untracked in the active checkout and should be added intentionally with the Phase 5 code changes if this work is committed later.
