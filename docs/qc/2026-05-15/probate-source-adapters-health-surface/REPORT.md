# Probate source adapters + operator health surface QC report

- Timestamp UTC: `2026-05-15T10:22:53Z`
- Repo: `martinp09/Ares`
- Branch: `feature/probate-autopilot-source-foundation`
- Slice: continue PRD execution through additional no-send gates after durable ledger/file-adapter/doctor foundation.

## What changed

- Added a read-only probate source adapter contract for Harris and Montgomery export rows:
  - canonicalizes county export aliases such as `Case Number`, `Cause No.`, `Case Type`, `Type Description`, `Style of Case`, and filing dates.
  - stamps source rows with `source_adapter`, `source_adapter_version`, `source_row_id`, `source_uri`, `source_row_index`, and `raw_export_row` for raw-first artifacts.
- Extended the source-file CLI/service into a source-packet bridge:
  - accepts repeated `--source-file` inputs.
  - combines Harris and Montgomery local exports into one no-send nightly-source-pull payload.
  - preserves `county_scope` vs `expected_counties` and records `source_files` summaries.
- Added operator-useful duplicate-case detection:
  - internal run metadata/artifacts keep duplicate case details.
  - Mission Control-facing brief/health sections expose only aggregate duplicate counts by county.
  - operator next actions include duplicate dedupe when needed.
- Added doctor freshness/SLA support:
  - `scripts/probate_autopilot_doctor.py --max-brief-age-hours` can block a stale source-run ledger.
- Added read-only Mission Control health endpoint:
  - `GET /mission-control/probate-autopilot/health`
  - returns no-send status, SLA status, source quality, enrichment backlog, anomalies, and next actions.
- Added Mission Control frontend API client support for the health endpoint.
- Hardened brief redaction:
  - raw request metadata/source rows are no longer echoed into `MorningBrief.sections`.
  - safe source request metadata is allowlisted under `source_request`.

## Safety boundary

No live side effects were introduced or run:

- Live county scraping/source-provider pulls: no
- HubSpot/CRM writes: no
- Instantly enrollment/activation/send: no
- SMS/Vapi/direct mail: no
- Paid skiptrace: no
- Slack/provider/webhook dispatch: no

All new surfaces are file/export-backed or read-only health/reporting.

## QC review

A separate QC subagent initially found a blocker: duplicate case numbers could leak through Mission Control-facing brief/health sections. The blocker was fixed by keeping duplicate case numbers only in internal run metadata/artifacts and exposing aggregate counts in Mission Control. A second QC pass returned `PASS` with no blockers.

## Verification

Captured in `test-output.txt`:

- `python -m pytest -q` → `790 passed`
- `npm --prefix apps/mission-control test -- --run` → `23 passed`, `76 tests passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass
- `npm --prefix trigger run typecheck` → pass
- `git diff --check` → clean

## Remaining gates

- Real Harris source adapter/browser bridge remains unapproved/live-gated.
- Montgomery live source discovery/adapter remains unapproved/live-gated.
- CAD/property match execution remains a later no-send enrichment gate.
- Tax overlay execution remains a later no-send enrichment gate.
- Mission Control page-level rendering of the new health endpoint can be added after this API contract lands.
- HubSpot mirror and all outbound actions remain separate explicit approval gates.
