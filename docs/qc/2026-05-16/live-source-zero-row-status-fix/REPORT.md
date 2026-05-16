# Live source zero-row status fix

## Scope

Martin asked to make the lead-machine run fully live after Slack showed: `live county scraping is deferred`.

Preflight confirmed both sides were already gated live for read-only intelligence:

- Trigger prod env:
  - `ARES_TRIGGER_SCHEDULES_ENABLED=true`
  - `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=true`
  - `LEAD_MACHINE_SCHEDULED_LIVE_CASE_DETAIL_CALLS_ENABLED=true`
  - `LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED=true`
  - runtime URL points at `https://ares.tail485fd9.ts.net`
- VPS env preflight:
  - `status=healthy`
  - `no_send_ok=true`
  - `live_intelligence_ready=true`
  - provider/outbound mutation gates false

## Finding

A manual live no-send runtime pull was fired before the patch. It completed and posted to Slack, but both counties returned zero rows for the narrow same-day window. Because `source_rows[county]` was an empty list, the manifest builder fell back to the old placeholder path and emitted the stale warning:

`probate autopilot Phase 1 records source-run placeholders only; live county scraping is deferred`

The runtime still reported `would_call_external_sources=true` / `live_source_calls_enabled=true`; the issue was the zero-row source-run classification and Slack warning, not missing live gates.

## Fix

The manifest builder now treats declared live adapter/local export results as real source results even when row count is zero. Successful zero-row live adapter runs now produce normal source-run artifacts and `live_source_adapter_status=live_source_adapter` instead of placeholder/deferred status.

## Verification before deploy

Captured in `test-output.txt`:

- `uv run pytest -q tests/services/test_probate_source_provider_service.py tests/services/test_nightly_lead_machine_service.py tests/api/test_trigger_contract_files.py` → `52 passed`
- `git diff --check` → passed

## Deployment

- Code commit: `619ae77` / `619ae77560028fc624d4c91bc27efe8af95c4e0b`
- Pushed to `origin/main`.
- VPS checkout `/opt/ares/Ares` advanced to `619ae77`.
- Rebuilt/recreated `ares-api` with `/opt/ares/docker-compose.yml`.
- `ares-api` health: `running healthy`.

## Post-deploy live no-send verification

Captured in:

- `post-deploy-verification.json`
- `source-ledger-post-deploy-summary.json`

Manual live no-send pull after deploy:

- Brief: `morning_brief_68c3ab1c99bf490391c3018ec7befb98`
- Slack `lead_runs` notification: `sent`, ts `1778968001.525219`
- `would_call_external_sources=true`
- `live_source_calls_enabled=true`
- Harris source run: `live_source_adapter_status=live_source_adapter`, `network_calls_attempted=true`, artifacts `raw_source_rows`, `normalized_source_rows`, `keep_now_rows`
- Montgomery source run: `live_source_adapter_status=live_source_adapter`, `network_calls_attempted=true`, artifacts `raw_source_rows`, `normalized_source_rows`, `keep_now_rows`
- Same-day narrow window returned `0` new / `0` hot / `0` warm records.
- `contains_deferred_warning=false`
- Latest brief warnings: `[]`
- Probate health: `healthy`, `no_send_ok=true`, `outbound_allowed=false`

## Watchdog

Created one-shot Hermes watcher `9ed644afbc4a` for `2026-05-16T22:50:00Z` to check the next real Trigger schedule after the `17:40 CT` window and report back to Telegram.

## No-send boundary

No outbound campaign sends were enabled by this patch. SMS/email/Instantly/Vapi/HubSpot provider mutations remain blocked until a separate launch manifest approves exact recipients, copy, limits, and gates.
