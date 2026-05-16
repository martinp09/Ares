# Diff Summary — Probate Post-Adapter Live No-Send Monitor

## Code changes

- `app/services/probate_live_source_adapter_service.py`
  - Preserves Harris ASP.NET `javascript:__doPostBack(...)` detail links as `case_detail_postback_target` + `case_detail_source_url` instead of treating them as URLs.
  - Keeps direct detail links as `case_detail_url` for Harris/Montgomery rows that expose normal URLs.
- `app/services/probate_case_detail_enrichment_service.py`
  - Allows both Harris `CaseDetail.aspx` and `CourtCaseDetail.aspx` direct HTTPS paths.
  - Classifies postback-only rows as incomplete with `case_detail_postback_only`, not blocked.
- `app/services/nightly_lead_machine_service.py`
  - Adds `case_detail_incomplete_count` to the aggregate enrichment backlog.
- `scripts/smoke/probate_autopilot_live_no_send_smoke.py`
  - Prints `case_detail_blocked_count` and `case_detail_incomplete_count` in aggregate smoke output.

## Test changes

- `tests/services/test_probate_live_source_adapter_service.py`
  - Covers Harris postback detail links from live search rows.
- `tests/services/test_probate_case_detail_enrichment_service.py`
  - Covers direct Harris `CourtCaseDetail.aspx` allowlist.
  - Covers postback-only case-detail rows being incomplete, not blocked.
- `tests/services/test_nightly_lead_machine_service.py`
  - Expects `case_detail_incomplete_count` in morning brief enrichment backlog.

## QC artifacts added

- `REPORT.md`
- `env-contract-output.json`
- `same-day-smoke-failure-output.txt`
- `live-no-send-smoke-output.json` — empty artifact from first strict same-day smoke attempt.
- `live-no-send-smoke-2026-05-15-to-2026-05-16-output.json`
- `live-no-send-smoke-2026-05-15-to-2026-05-16-after-case-detail-allowlist-output.json`
- `live-no-send-smoke-2026-05-15-to-2026-05-16-debug-artifacts-output.json`
- `live-no-send-smoke-2026-05-15-to-2026-05-16-after-postback-classification-output.json`
- `focused-test-output.txt`
- `full-backend-output.txt`
- `trigger-typecheck-output.txt`
- `git-diff-check-output.txt`

## Not added

- No raw source rows.
- No raw county HTML.
- No names/case numbers/addresses/contact data in QC reports.
- No provider/send artifacts.
- No secret values.

## Result

- Env contract remains blocked for production no-send deployment until durable state/artifact/business/environment env vars are configured.
- Same-day strict smoke is failed/inconclusive because the valid zero-row day produced no summary JSON.
- Two-day live no-send monitor passed with `48` source rows, `8` keep-now rows, `no_send=true`, and `provider_sends_enabled=false`.
- Harris case-detail rows are now accurately classified as postback-only incomplete rather than unsafe blocked URLs.
- Focused backend, full backend, Trigger typecheck, and diff check passed.
