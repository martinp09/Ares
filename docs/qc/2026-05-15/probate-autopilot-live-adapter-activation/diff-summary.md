# Diff Summary — Probate Autopilot Live Adapter Activation

Generated: 2026-05-15 final pre-commit refresh.

## Changed files

```text
M	.env.example
M	CONTEXT.md
M	TODO.md
M	app/api/lead_machine.py
M	app/core/config.py
M	app/services/probate_autopilot_manifest_service.py
M	app/services/probate_property_tax_title_enrichment_service.py
M	app/services/probate_source_provider_service.py
M	memory.md
M	tests/api/test_lead_machine.py
M	tests/api/test_trigger_contract_files.py
M	tests/services/test_probate_property_tax_title_enrichment_service.py
M	tests/services/test_probate_source_provider_service.py
M	trigger/src/lead-machine/probateAutopilotSchedules.ts
```

## Diff stat

```text
 .env.example                                       |   4 +
 CONTEXT.md                                         |   9 +-
 TODO.md                                            |  16 +-
 app/api/lead_machine.py                            |   2 +
 app/core/config.py                                 |  21 +++
 app/services/probate_autopilot_manifest_service.py |   1 +
 ...robate_property_tax_title_enrichment_service.py | 111 +++++++++++---
 app/services/probate_source_provider_service.py    | 108 ++++++++++++-
 memory.md                                          |  14 +-
 tests/api/test_lead_machine.py                     |   2 +-
 tests/api/test_trigger_contract_files.py           |   4 +-
 ...robate_property_tax_title_enrichment_service.py | 123 ++++++++++++++-
 .../test_probate_source_provider_service.py        | 169 ++++++++++++++++++++-
 .../src/lead-machine/probateAutopilotSchedules.ts  |  24 ++-
 14 files changed, 566 insertions(+), 42 deletions(-)
```

## Intent

- Activate Harris/Montgomery public probate source adapters behind disabled-by-default, explicit no-send gates.
- Add live enrichment seams for CAD/tax/land-record clients behind separate disabled-by-default approval gates.
- Keep Instantly/SMS/Vapi/paid skiptrace/HubSpot writes out of scope and blocked by default.
- Record fresh backend, Mission Control, Trigger, and whitespace QC artifacts.
