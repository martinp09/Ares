# Montgomery Probate Odyssey Adapter Fix QC

- Date: 2026-05-15
- Branch: `fix/montgomery-probate-odyssey-adapter`
- Scope: Fix the Montgomery County Odyssey public probate source adapter used by the no-send Harris+Montgomery probate autopilot.
- Safety posture: source reads only. No Instantly enrollment, email/SMS/Vapi sends, HubSpot writes, paid skiptrace, CAD/tax/land-record live enrichment, or provider mutations.

## Root cause

The Montgomery adapter treated the Odyssey session bootstrap as a raw `302` cookie capture and then tried to `GET /County/Search.aspx?ID=200` directly. Odyssey's public-access launch flow does not expose the Civil & Probate search form through that direct GET. The public landing page's JavaScript launches the case-search page with a `POST` containing:

- `NodeID=100,105,110,120,130,140,150,160,180`
- `NodeDesc=All County Courts`

The old adapter also did not persist the full redirect/cookie flow through a `HTTPCookieProcessor`, which made the session brittle and caused `HTTP Error 302: Found` before any Montgomery rows were published.

## Change summary

- Replaced the Montgomery custom cookie/no-redirect bootstrap with a normal cookie-jar opener that follows the Odyssey public-access login redirect.
- Added the required Odyssey node-launch POST before submitting date-filed search parameters.
- Added a Montgomery date-filed probate form builder that posts `SearchBy=6`, `SearchType=CASE`, `SearchMode=FILED`, `CaseCategories=PR`, and a matching `SearchParams` payload.
- Added bounded session retries for Odyssey redirect/session bounces.
- Added regression tests proving the adapter launches the search with the node POST and posts only the probate category.

## Verification

Captured in this folder:

- `test-output.txt`
  - `python -m py_compile app/services/probate_live_source_adapter_service.py tests/services/test_probate_live_source_adapter_service.py`
  - `python -m pytest tests/services/test_probate_live_source_adapter_service.py -q`
  - Result: `7 passed`
- `smoke-output.txt`
  - Direct Montgomery adapter live smoke: `raw_count=8`, `parsed_rows=8`, `warnings=[]`, `portal_record_count_before_probate_filter=10`
  - Manual no-send autopilot smoke: Harris `32` parsed / `8` keep-now; Montgomery `8` parsed / `0` keep-now; `partial_failures={}`; `sla_status=healthy`; `warning_count=0`; `no_send_ok=true`
- `diff-summary.md`
  - Changed files and rationale.

## No-send confirmation from smoke

The manual autopilot smoke reported:

- `no_send_ok=true`
- `outbound_allowed=false`
- `instantly_enrollment=false`
- `email_sms_vapi_sends=false`
- `hubspot_writes=false`
- `paid_skiptrace=false`
- `live_cad_calls_attempted=false`
- `live_tax_calls_attempted=false`
- `live_land_record_calls_attempted=false`

## Remaining risk / follow-up

- Montgomery rows parsed successfully, but none hit the current keep-now filter in this run. That is expected if today's Montgomery filings were not in the target probate/title-friction categories.
- The Odyssey portal can bounce sessions; the adapter now retries bounded clean sessions, but recurring monitoring should keep reporting aggregate source-run health and warnings.
- Leave Ares Trigger scheduled live-source activation gated until Martin explicitly approves Ares-side scheduled live-source execution. The Hermes no-send cron remains source-read-only and provider-write-disabled.
