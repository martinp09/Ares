# Diff Summary — Probate Autopilot Live Operational PRD Execution

## Intent

Execute the Harris + Montgomery probate autopilot PRD as a live operational no-send system, not a scaffold: public source pulls and public CAD/tax/land-record enrichment are wired and default-on; only outbound/provider mutations remain blocked.

## Changed files

```text
M	.env.example
M	CONTEXT.md
M	README.md
M	TODO.md
M	app/core/config.py
M	app/services/nightly_lead_machine_service.py
M	app/services/probate_live_source_adapter_service.py
M	app/services/probate_property_tax_title_enrichment_service.py
M	app/services/probate_source_provider_service.py
M	docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md
M	memory.md
M	tests/api/test_nightly_lead_machine.py
M	tests/api/test_trigger_contract_files.py
M	tests/services/test_nightly_lead_machine_service.py
M	tests/services/test_probate_live_source_adapter_service.py
M	tests/services/test_probate_property_tax_title_enrichment_service.py
M	tests/services/test_probate_source_provider_service.py
M	trigger/src/lead-machine/nightlySourcePull.ts
M	trigger/src/lead-machine/probateAutopilotSchedules.ts
```

## Diff stat

```text
.env.example                                       |  11 +-
 CONTEXT.md                                         |  26 ++--
 README.md                                          |   3 +-
 TODO.md                                            |  36 ++----
 app/core/config.py                                 |   8 +-
 app/services/nightly_lead_machine_service.py       |  38 ++++--
 .../probate_live_source_adapter_service.py         |  12 +-
 ...robate_property_tax_title_enrichment_service.py |  42 +++++--
 app/services/probate_source_provider_service.py    |  15 ++-
 ...tgomery-probate-autopilot-no-send-activation.md | 131 +++++++++++----------
 memory.md                                          |  16 ++-
 tests/api/test_nightly_lead_machine.py             |   4 +-
 tests/api/test_trigger_contract_files.py           |   7 +-
 .../services/test_nightly_lead_machine_service.py  |   6 +-
 .../test_probate_live_source_adapter_service.py    |  12 +-
 ...robate_property_tax_title_enrichment_service.py |  82 +++++++++++++
 .../test_probate_source_provider_service.py        |   8 +-
 trigger/src/lead-machine/nightlySourcePull.ts      |   2 +-
 .../src/lead-machine/probateAutopilotSchedules.ts  |  30 ++++-
 19 files changed, 330 insertions(+), 159 deletions(-)
```

## Key behavior changes

- Backend source/CAD/tax/land live flags default on for the lead-machine autopilot.
- Trigger schedule payloads default to live source calls and live enrichment approval metadata.
- `run_nightly_source_pull` reports real `would_call_external_sources` / `live_source_calls_enabled` state and invokes enrichment inline for keep-now rows.
- Registered public enrichment clients cover Harris HCTax/Harris Clerk real-property metadata and Montgomery MCAD ArcGIS/ACT/PublicSearch metadata.
- Montgomery Odyssey source adapter is more robust: default-page priming, 6 bounded attempts, small backoff, and partial-read tolerance.
- Added reusable live no-send smoke script: `scripts/smoke/probate_autopilot_live_no_send_smoke.py`.
- Living docs, runbook, env example, TODO/CONTEXT/memory, QC report, and Obsidian PRD are updated to reflect operational no-send execution.

## Verification artifacts

- `py-compile-output.txt`
- `live-smoke-output.txt`
- `live-smoke-output.json`
- `focused-pytest-output.txt`
- `full-pytest-output.txt`
- `trigger-typecheck-output.txt`
- `git-diff-check-output.txt`

## Side-effect boundary

Still blocked by code/policy in this slice: Instantly enrollment/sends, SMS/Vapi sends, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deployment/promotion.
