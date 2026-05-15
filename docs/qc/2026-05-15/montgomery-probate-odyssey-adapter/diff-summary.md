# Diff Summary

## Changed files

- `app/services/probate_live_source_adapter_service.py`
  - Replaced the brittle Montgomery no-redirect cookie bootstrap with a cookie-jar opener.
  - Added Odyssey public-access node-launch POST before requesting the Civil & Probate search form.
  - Added a deterministic Montgomery date-filed probate form builder with `SearchBy=6`, `SearchMode=FILED`, `CaseCategories=PR`, and matching `SearchParams`.
  - Added bounded session retries for Odyssey redirect/session bounces.
  - Kept the adapter read-only: no CRM writes, sends, enrollment, skiptrace, CAD/tax/land calls, or provider mutation paths.

- `tests/services/test_probate_live_source_adapter_service.py`
  - Added a regression test for the Montgomery form payload so non-probate categories are removed and `CaseCategories=PR` is posted.
  - Added a regression test proving the live adapter launches Odyssey search via node POST before submitting date-filed search parameters.

- `docs/qc/2026-05-15/montgomery-probate-odyssey-adapter/`
  - Added durable QC evidence for focused tests, direct live adapter smoke, manual no-send autopilot smoke, and this report.

- `CONTEXT.md`, `TODO.md`, `memory.md`
  - Updated living docs with the active fix branch, root-cause/fix summary, manual no-send pilot results, and remaining gates.

## Verification commands

- `python -m py_compile app/services/probate_live_source_adapter_service.py tests/services/test_probate_live_source_adapter_service.py`
- `python -m pytest tests/services/test_probate_live_source_adapter_service.py -q`
- Direct Montgomery adapter live smoke for 2026-05-15
- `/root/.hermes/scripts/ares_probate_autopilot_no_send.py --force-now --json`
- `git diff --check`
