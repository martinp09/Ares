# QC Report — Probate Autopilot Live Operational PRD Execution

- Date UTC: 2026-05-15
- Repo: `martinp09/Ares`
- Worktree: `/opt/ares/worktrees/ares-main`
- Branch at execution: `fix/probate-autopilot-enrichment-wiring`; merged to `origin/main` at `9c256bf`
- Obsidian PRD: `/root/obsidian-vault/03-Experiments/Harris Montgomery Probate Autopilot PRD.md`

## Scope

Martin clarified that the PRD should be executed as a fully working operational system, with only actual outbound email sending blocked. This slice therefore moved the probate autopilot from gated/scaffold-style readiness to live no-send operation:

- real Harris + Montgomery public probate source adapters;
- real public CAD/property, tax-overlay, and land-record enrichment clients;
- Trigger schedule payloads that default to live source + live enrichment no-send requests;
- backend default live source/CAD/tax/land flags on;
- reusable live smoke script;
- Instantly/email/SMS/Vapi/paid skiptrace/HubSpot batch writes still blocked.

## What changed

- `app/core/config.py`
  - Defaults live source/CAD/tax/land flags to `true`.
- `trigger/src/lead-machine/probateAutopilotSchedules.ts`
  - Defaults scheduled source and enrichment live no-send payloads on.
  - Adds no-send enrichment approval metadata for CAD/tax/land-record lanes.
- `app/services/probate_live_enrichment_clients.py`
  - New public read-only enrichment clients for Harris and Montgomery.
- `app/services/probate_property_tax_title_enrichment_service.py`
  - Registers public clients by default while preserving explicit no-send approval requirements.
- `app/services/probate_live_source_adapter_service.py`
  - Hardens Montgomery Odyssey session startup and retry behavior.
- `app/services/nightly_lead_machine_service.py`
  - Reports actual live-source state and keeps enrichment integrated in the nightly pull path.
- `scripts/smoke/probate_autopilot_live_no_send_smoke.py`
  - New live public-source no-send smoke harness.
- Tests/docs/runbooks/Obsidian PRD updated for the operational no-send contract.

## Live no-send smoke result

Command:

```bash
uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day 2026-05-15 --artifact-root docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/live-smoke-artifacts --idempotency-key live-operational-prd-execution-2026-05-15-final
```

Result summary from `live-smoke-output.txt`:

- `status=completed`
- counties: Harris + Montgomery
- `source_record_count=47`
- `keep_now_count=8`
- `enriched_count=8`
- `live_cad_calls_attempted=true`
- `live_tax_calls_attempted=true`
- `live_land_record_calls_attempted=true`
- `sla_status=healthy`
- `source_health_failed_runs=0`
- `warnings_count=0`
- `no_send=true`
- `provider_sends_enabled=false`

## Verification

Captured artifacts committed in this QC folder are aggregate-only:

- `py-compile-output.txt`
- `live-smoke-output.txt`
- `live-smoke-output.json`
- `focused-pytest-output.txt`
- `full-pytest-output.txt`
- `trigger-typecheck-output.txt`
- `git-diff-check-output.txt`
- `diff-summary.md`

The smoke wrote raw live source/enrichment artifacts to the local artifact root during execution; those raw files were removed from the committed QC folder to avoid committing public probate names/case rows.

Passed checks:

- Python compile: passed
- Live no-send public-source smoke: passed
- Focused backend/contracts: `75 passed`
- Full backend suite: `901 passed`
- Trigger typecheck: passed
- `git diff --check`: passed
- Post-merge `main` verification: `uv run pytest -q` => `901 passed`; `npm --prefix trigger run typecheck` => passed

## Side-effect audit

Executed side effects:

- Public read-only county/CAD/tax/land-record HTTP requests only.
- Local repo/QC artifact writes.
- Obsidian PRD update.

Not executed:

- no Instantly enrollment;
- no email sends;
- no SMS sends;
- no Vapi calls;
- no paid skiptrace;
- no HubSpot batch mirror writes;
- no Slack/provider sends;
- no deployment/promotion.

## Known data-quality result

The 2026-05-15 live keep-now rows did not carry enough property identifiers for CAD matches, so property match remained unmatched/pending for the 8 enriched rows. That is a data-quality/enrichment-depth follow-up, not a wiring gap: the smoke proved the live CAD/tax/land clients were called and the no-send runtime completed.

## Remaining gates

- Configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` and `LEAD_MACHINE_ARTIFACT_ROOT` before production deployment.
- Add stronger property matching once probate rows carry applicant/heir/property context.
- Keep outbound/provider-send controls blocked until Martin approves exact campaign/recipient/provider scope.
