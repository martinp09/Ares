# Probate Post-Adapter Live No-Send Monitor QC

Date UTC: 2026-05-16T15:04:38Z
Repo: `martinp09/Ares`
Worktree: `/opt/ares/worktrees/ares-main`
Branch: `main`
Slice: post-Supabase-identity-adapter live no-send monitor + Harris case-detail postback classification hardening.

## Scope

This slice monitored the probate autopilot after the Supabase source identity adapter landed and patched one live-read classification gap found during the monitor:

- Harris source rows can expose case-detail links as ASP.NET `javascript:__doPostBack(...)` targets rather than direct HTTPS detail URLs.
- Those postback-only rows are now preserved as `case_detail_postback_target` / `case_detail_source_url` and classified as case-detail `incomplete` with warning `case_detail_postback_only`, not as unsafe blocked URLs.
- Direct Harris `CaseDetail.aspx` and `CourtCaseDetail.aspx` URLs remain allowlisted for future/fixture detail rows.
- The smoke output now includes `case_detail_blocked_count` and `case_detail_incomplete_count` so blocked vs postback-only incomplete states are visible in aggregate QC.

No raw probate rows, names, case numbers, addresses, emails, phones, raw HTML, or provider payloads are included in this QC folder.

## Subagent lanes

Six parallel/read-only subagent lanes were used in two batches of three:

1. Backend verification lane: focused probate/source identity contracts and full backend suite passed before local patching.
2. Trigger/runtime lane: Trigger typecheck passed; scheduled probate payloads use `source_run_scope=autonomous`; no raw PII Trigger lifecycle artifact leakage found.
3. Docs/QC stale-state lane: identified stale adapter follow-up language and missing post-adapter monitor QC.
4. Case-detail smoke triage lane: found `case_detail_status=blocked` was caused by Harris postback-only detail links being treated as URLs.
5. Env preflight lane: identified production no-send deployment blockers and durable path/env requirements.
6. QC patch-plan lane: prepared the aggregate-only monitor report/doc update plan.

The parent session verified the final code and QC artifacts directly after applying the patch.

## Env contract result

Evidence: `env-contract-output.json`

Result: `status=blocked`

Blockers:

- `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` missing.
- `LEAD_MACHINE_ARTIFACT_ROOT` missing.
- `LEAD_MACHINE_BUSINESS_ID` missing.
- `LEAD_MACHINE_ENVIRONMENT` missing.

Safe gates:

- `no_send_ok=true`
- `created_files_or_directories=false`
- `live_source_calls=false`
- `provider_mutations=false`

Interpretation: production no-send deployment/activation remains blocked until durable source-run state, artifact root, business identity, and environment are explicitly configured. This does not indicate provider-send risk; outbound gates stayed disabled.

## Same-day smoke result

Evidence: `same-day-smoke-failure-output.txt` and empty `live-no-send-smoke-output.json`

Result: strict smoke failed/inconclusive because the 2026-05-16 same-day source window returned zero source records. That zero-row runtime behavior is valid after the scheduler correction, but the strict smoke command still expects `source_record_count > 0`, so it did not emit the normal aggregate JSON summary.

Interpretation: do not treat the same-day strict smoke as a pass. Use the two-day non-empty monitor below for live no-send source/enrichment evidence.

## Two-day live no-send monitor result

Initial post-adapter evidence: `live-no-send-smoke-2026-05-15-to-2026-05-16-output.json`

- `status=completed`
- Counties: Harris + Montgomery
- `source_record_count=48`
- `keep_now_count=8`
- `enriched_count=8`
- `source_run_count=6`
- `source_health_completed_runs=6`
- `source_health_failed_runs=0`
- `warnings_count=0`
- `sla_status=healthy`
- `no_send=true`
- `provider_sends_enabled=false`

Post-classification final evidence: `live-no-send-smoke-2026-05-15-to-2026-05-16-after-postback-classification-output.json`

- `status=completed`
- `source_record_count=48`
- `keep_now_count=8`
- `enriched_count=8`
- `case_detail_status=incomplete`
- `case_detail_completed_count=0`
- `case_detail_blocked_count=0`
- `case_detail_incomplete_count=8`
- `case_detail_pending_count=8`
- `live_case_detail_calls_attempted=true`
- `live_cad_calls_attempted=true`
- `live_tax_calls_attempted=true`
- `live_land_record_calls_attempted=true`
- `source_health_failed_runs=0`
- `warnings_count=0`
- `no_send=true`
- `provider_sends_enabled=false`

Interpretation: the live no-send source/CAD/tax/land path is operational for the two-day monitor window. Harris case-detail is not falsely blocked anymore; current live rows are postback-only, so detail completion remains a follow-up client capability rather than a direct URL fetch.

## Verification after patch

Evidence files:

- `focused-test-output.txt` — `69 passed`
- `full-backend-output.txt` — `963 passed`
- `trigger-typecheck-output.txt` — passed
- `git-diff-check-output.txt` — passed / empty output

Commands:

```bash
uv run pytest -q tests/services/test_probate_case_detail_enrichment_service.py tests/services/test_probate_live_source_adapter_service.py tests/services/test_nightly_lead_machine_service.py tests/db/test_probate_source_identity_repository.py tests/db/test_probate_source_identity_schema.py tests/api/test_lead_machine.py
uv run pytest -q
npm --prefix trigger run typecheck
git diff --check
```

## Side-effect audit

Performed:

- Read-only public Harris/Montgomery source/CAD/tax/land/case-detail attempts through the no-send smoke path.
- Local QC file writes under `docs/qc/2026-05-16/probate-post-adapter-live-no-send-monitor/`.

Not performed:

- No Instantly enrollment.
- No email sends.
- No SMS sends.
- No Vapi/calls.
- No paid skiptrace.
- No HubSpot writes.
- No Slack/provider sends.
- No Supabase schema mutation.
- No deploy.
- No raw PII committed.

## Remaining operator follow-up

1. Configure production no-send deployment env before activating scheduled production runtime:
   - `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`
   - `LEAD_MACHINE_ARTIFACT_ROOT`
   - `LEAD_MACHINE_BUSINESS_ID`
   - `LEAD_MACHINE_ENVIRONMENT`
   - explicit live intelligence gates.
2. Add a Harris postback case-detail client if case-detail completion is required from live Harris source rows; current rows expose postback targets, not direct HTTPS detail URLs.
3. Continue monitoring autonomous scheduled runs for county coverage, duplicate-prior-run counts, source identity recording, enrichment backlog, and no-send confirmation.
4. Keep all outbound/provider-send gates blocked until Martin approves exact recipients/campaigns.
