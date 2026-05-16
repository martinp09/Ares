# Diff Summary

```text
.../probate_live_source_adapter_service.py         |  4 ++--
tests/api/test_trigger_contract_files.py           |  7 +++++-
.../test_probate_live_source_adapter_service.py    | 25 ++++++++++++++++++++++
.../src/lead-machine/probateAutopilotSchedules.ts  | 23 +++++++++++++++++++-
4 files changed, 55 insertions(+), 4 deletions(-)
```

## Files changed

- `app/services/probate_live_source_adapter_service.py`
  - Accepts valid zero-row Harris/Montgomery search result pages instead of promoting them to runtime failures.
- `tests/services/test_probate_live_source_adapter_service.py`
  - Adds zero-row parser/page contract tests.
- `trigger/src/lead-machine/probateAutopilotSchedules.ts`
  - Adds explicit scheduled source windows matching PRD cadence.
- `tests/api/test_trigger_contract_files.py`
  - Updates Trigger contract assertions to protect explicit date-window behavior.

## Live script changed outside repo

- `/root/.hermes/scripts/ares_probate_autopilot_no_send.py`
  - Adds run-kind date windows and 02:20/Sunday 03:15 schedule windows for the Hermes no-agent watchdog cron.
