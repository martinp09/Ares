# QC Report — Probate Case-Detail Enrichment

- Date UTC: 2026-05-15
- Repo: `martinp09/Ares`
- Worktree: `/opt/ares/worktrees/ares-main`
- Branch: `fix/probate-case-detail-enrichment`
- Scope: final high-value PRD enrichment gap — no-send case-detail party/event/document/contact-candidate enrichment

## Scope

This slice finishes the last high-value PRD gap before provider/outbound activation: extracting case-detail context for Harris + Montgomery probate keep-now rows while keeping Ares as the no-send source of truth.

Implemented behavior:

- Case-detail enrichment runs inside the nightly probate source-pull path before property/tax/title enrichment.
- Harris and Montgomery live source adapters preserve public case-detail URLs when available.
- Case-detail source-run lanes are recorded as aggregate enrichment lanes:
  - `harris_probate_case_detail`
  - `montgomery_probate_case_detail`
- Case-detail source-run metadata is aggregate; operational artifact files contain normalized evidence at the configured artifact root and do not inflate source `new_record_count`.
- Contact candidates are capped and explicitly not treated as confirmed sellers:
  - `is_confirmed_seller=false`
  - `seller_authority_verified=false`
  - `skiptrace_status=not_requested`
  - `outbound_allowed=false`
- Scheduled Trigger payloads include separate no-send case-detail approval metadata.
- Live case-detail fetches are blocked unless the request has no-send approval and the URL is an HTTPS public county detail URL on the allowlist.

## Safety and no-send controls

Preserved / added controls:

- No Instantly enrollment.
- No email sends.
- No SMS sends.
- No Vapi calls.
- No paid skiptrace.
- No HubSpot batch mirror writes.
- No Slack/provider sends.
- No production deploy/promotion.
- No seller-authority claim from probate parties alone.
- No raw live probate case-detail rows, party identities, addresses, or raw HTML are committed in QC evidence.

Approved live case-detail URL allowlist:

- `https://www.cclerk.hctx.net/Applications/WebSearch/CaseDetail.aspx...`
- `https://cclerk.hctx.net/Applications/WebSearch/CaseDetail.aspx...`
- `https://odyssey.mctx.org/County/CaseDetail.aspx...`

## Verification

Captured outputs:

- `focused-output.txt`
- `full-output.txt`
- `git-diff-check-output.txt`
- `diff-summary.md`

Passed checks:

```bash
python -m py_compile app/services/probate_case_detail_enrichment_service.py app/services/nightly_lead_machine_service.py app/services/probate_live_source_adapter_service.py app/services/probate_source_adapter_service.py scripts/probate_autopilot_env_contract.py
uv run pytest tests/services/test_nightly_lead_machine_service.py tests/services/test_probate_case_detail_enrichment_service.py tests/services/test_probate_live_source_adapter_service.py tests/api/test_trigger_contract_files.py tests/scripts/test_probate_autopilot_env_contract.py -q
uv run pytest -q
npm --prefix trigger run typecheck
git diff --check
```

Results:

- Focused contracts: `47 passed`.
- Full backend suite: `916 passed`.
- Trigger typecheck: passed.
- `git diff --check`: passed.

## Side-effect audit

Executed:

- Local code/test/doc edits.
- Local test execution.
- Local QC evidence writes.

Not executed:

- no live county smoke in this follow-up;
- no production deploy/promotion;
- no provider sends or writes;
- no Instantly enrollment;
- no email sends;
- no SMS sends;
- no Vapi calls;
- no paid skiptrace;
- no HubSpot batch writes;
- no Slack/provider sends.

## Aggregate-only evidence posture

Committed QC is intentionally aggregate-only. The report does not contain raw public probate rows, party names, case-detail HTML, addresses, contact-candidate identities, or source artifacts.

The code path can persist normalized case-detail artifacts at the configured `LEAD_MACHINE_ARTIFACT_ROOT` during actual runtime, but those artifacts are operational data and are not committed to repo QC.

## Remaining gates

- Run the env preflight against the real production env before any production no-send deployment:
  - `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live`
- Configure durable state/artifact directories in deployment:
  - `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`
  - `LEAD_MACHINE_ARTIFACT_ROOT`
- Measure property-match lift from case-detail-derived party/address/context evidence.
- Keep HubSpot mirror writes, Instantly enrollment/sends, SMS/Vapi, paid skiptrace, Slack/provider sends, and production deploy as separate explicit approval gates.
