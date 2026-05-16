# Probate Autopilot Scheduler Runtime Error

Date: 2026-05-16
Scope: Harris + Montgomery probate no-send background scraper/scheduler

## Symptom

The Hermes no-agent cron job `815e1261ab2e` emitted a blocked 07:10 CT run:

- Harris: `RuntimeError: Harris probate live source did not return the expected search-results page`
- Montgomery: `RuntimeError: Montgomery Odyssey live source failed after session retries ... search-results page missing Record Count/CaseDetail markers`
- Parsed public rows: `0`
- SLA status: `blocked`
- No-send provider side effects remained false.

## Root cause

The background runner was querying only the current calendar day for `morning_catchup`. On Saturday 2026-05-16, the current-day county windows were empty / unstable:

- Harris returned an empty `ListViewCases` search result with no `btnSelect` links. The adapter treated "zero rows" as a runtime error.
- Montgomery's single-day 2026-05-16 query bounced through Odyssey's public session flow instead of returning a stable result table.

The PRD schedule says 07:10 CT should cover prior evening through current morning. At date granularity, the correct 07:10 source window is previous day through current day. A live diagnostic for `2026-05-15` → `2026-05-16` returned Harris `40` rows and Montgomery `8` rows with no county failures.

## Fix applied

Repo changes:

- `trigger/src/lead-machine/probateAutopilotSchedules.ts`
  - Scheduled payloads now include explicit `window_start` + `window_end` date keys.
  - 07:10 CT: previous day → current day.
  - 02:20 CT: previous 7 days → current day.
  - Sunday 03:15 CT: previous 30 days → current day.
- `app/services/probate_live_source_adapter_service.py`
  - Harris zero-row result pages are accepted as valid source responses instead of runtime errors.
  - Montgomery `Record Count: 0` result pages without case links are accepted as valid zero-row responses.
- `tests/services/test_probate_live_source_adapter_service.py`
  - Added zero-row result contract coverage.
- `tests/api/test_trigger_contract_files.py`
  - Updated Trigger schedule contract checks for explicit source windows.

Live Hermes cron script change:

- `/root/.hermes/scripts/ares_probate_autopilot_no_send.py`
  - Uses source date windows by run kind.
  - Adds 02:20 daily reconciliation and Sunday 03:15 weekly reconciliation windows.
  - 07:10 morning catchup now pulls previous day through current day.

## Verification

- Focused adapter contracts: `uv run pytest tests/services/test_probate_live_source_adapter_service.py -q` → `9 passed`.
- Full backend: `uv run pytest -q` → `948 passed`.
- Trigger typecheck: `npm --prefix trigger run typecheck` → passed.
- Whitespace: `git diff --check` → passed.
- Live adapter diagnostic:
  - Harris current-day zero-row page now returns `ok=true`, `raw=0`, warning `harris_live_source_returned_no_rows_for_window`.
  - Harris 2026-05-15→2026-05-16 returns `40` rows.
  - Montgomery 2026-05-15→2026-05-16 returns `8` rows.
- Temp-state scheduler replay for 2026-05-16 07:10 CT:
  - status `completed`
  - SLA `healthy`
  - partial failures `{}`
  - Harris `40` parsed / `8` keep-now
  - Montgomery `8` parsed / `0` keep-now
  - no-send ok `true`

## Safety boundary

No Instantly enrollment, email/SMS/Vapi sends, HubSpot writes, Slack/provider sends, paid skiptrace, or CRM/provider mutations were executed. The scheduler replay used temp state/artifacts and aggregate-only output.
