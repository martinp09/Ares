# Probate Source Identity Supabase Adapter QC

Date: 2026-05-16
Repo: `martinp09/Ares`
Branch during verification: `feature/probate-source-identity-supabase-adapter`
Slice: wire `public.probate_source_identities` into nightly probate source-run dedupe/persistence.

## Scope

This slice wires the already-applied Supabase identity table into the runtime path without changing outbound/provider gates:

- Added `app/db/probate_source_identities.py`.
- `NightlyLeadMachineService` now reads durable same-scope identity keys from `public.probate_source_identities` before probate manifest construction when `LEAD_MACHINE_BACKEND=supabase`.
- If the remote identity read fails, the nightly path continues with file-backed completed-run dedupe and records an aggregate warning instead of aborting.
- File-backed completed runs are still overlaid so current durable JSON state remains part of dedupe during transition.
- Completed Harris/Montgomery probate source runs now record normalized `source_identity_key` values back to Supabase through the adapter.
- The manifest metadata carries hashed source identity records, so Supabase recording can still work when artifact paths are logical/non-local.
- If the remote identity write fails after source-run completion, the nightly path persists a sanitized warning and still saves the morning brief/idempotency response.
- Manual isolated environments such as `<environment>-manual` skip remote tenant resolution, remote identity reads, and remote identity writes.

## Safety / side effects

No live outbound or provider actions were executed in this slice:

- No Instantly enrollment or sends.
- No SMS/Vapi calls.
- No paid skiptrace.
- No HubSpot writes.
- No Slack/provider sends.
- No live county scrape/smoke.
- No Vercel deploy.
- No Supabase schema mutation; the table migration was already applied in the prior approved migration slice.
- No raw probate-row QC artifact was written for this adapter slice.

## Verification commands

```bash
uv run pytest tests/db/test_probate_source_identity_repository.py tests/db/test_probate_source_identity_schema.py tests/services/test_probate_source_file_service.py tests/services/test_nightly_lead_machine_service.py -q
uv run pytest -q
npm --prefix trigger run typecheck
git diff --check
```

## Results

- Focused identity/nightly/source-file contracts: `43 passed`.
- Full backend: `961 passed`.
- Trigger typecheck: passed.
- `git diff --check`: passed.

## Evidence files

- `focused-test-output.txt`
- `full-backend-output.txt`
- `trigger-typecheck-output.txt`
- `git-diff-check-output.txt`
- `diff-summary.md`

## Review notes

A read-only review flagged two blocking resilience risks before finalization:

1. Remote identity write failure could abort the nightly path after the source run was already completed but before brief/idempotency save.
2. Remote identity recording depended only on reopening physical artifact files, which can be absent when artifact paths are logical.

Both were fixed before final verification: remote read/write failures now degrade to sanitized warnings, idempotency still saves, and hashed source identity records are carried in source-run metadata as a non-PII fallback for Supabase recording.

## Remaining operator follow-up

Superseded by post-adapter monitor QC: `docs/qc/2026-05-16/probate-post-adapter-live-no-send-monitor/`.

The first non-empty live no-send monitor after adapter wiring completed on a two-day window with `48` source rows and `8` keep-now rows; provider sends remained blocked (`no_send=true`, `provider_sends_enabled=false`). The monitor also found and corrected a Harris case-detail classification gap: live rows can expose postback-only detail targets, now recorded as incomplete (`case_detail_postback_only`) instead of unsafe blocked URLs.

Remaining follow-up: configure durable production env so the read-only preflight passes, then continue monitoring autonomous scheduled runs for same-scope duplicate counts and Supabase identity-ledger recording.
