# Probate Autopilot Enrichment Wiring QC

- Date UTC: 2026-05-15
- Branch: `fix/probate-autopilot-enrichment-wiring`
- Worktree: `/opt/ares/worktrees/ares-main`
- Scope: wire Harris + Montgomery probate nightly source-pull into property/CAD, tax-overlay, and land-record/title-friction enrichment for keep-now rows.

## What changed

The previous runtime had a no-send enrichment endpoint, but the scheduled/nightly probate source-pull path stopped after source rows and morning brief backlog counts. This slice wires the PRD path together:

1. `NightlyLeadMachineService.run_nightly_source_pull` now collects normalized keep-now source rows for probate-autopilot requests.
2. The same no-send nightly call invokes `ProbatePropertyTaxTitleEnrichmentService` using supplied local enrichment artifacts:
   - `property_tax_title_enrichment.hcad_candidates_by_case`
   - `property_tax_title_enrichment.tax_overlays_by_case`
   - `property_tax_title_enrichment.tax_overlays_by_account`
   - `property_tax_title_enrichment.land_record_rows_by_case`
3. The nightly call now emits internal zero-count enrichment source-run stages so source record counts are not inflated:
   - Harris: `harris_hcad_property_match`, `harris_hctax_overlay`, `harris_land_records`
   - Montgomery: `montgomery_cad_property_match`, `montgomery_act_tax_overlay`, `montgomery_land_records`
4. The morning brief `enrichment_backlog` now reports actual completed/pending counts instead of always treating all keep-now rows as pending.
5. Operator next action now distinguishes incomplete enrichment from completed enrichment review.

## Safety posture

- No Instantly enrollment.
- No email/SMS/Vapi sends.
- No HubSpot writes.
- No paid skiptrace.
- No live CAD/tax/land-record calls in this smoke; live enrichment clients remain explicit gated clients.
- Enrichment artifacts are internal source-run artifacts; Mission Control/morning brief surfaces aggregate status/counts only.

## Verification summary

- Focused service/enrichment tests: `25 passed`.
- Source/provider/API/Trigger contract regression set: `65 passed`.
- Lead-machine API/Trigger/nightly API regression set: `47 passed`.
- Full backend suite: `900 passed`.
- `git diff --check`: passed.
- Manual no-send local-artifact smoke:
  - source runs: 8
  - lanes include Harris/Montgomery probate + property/CAD + tax + land/title stages
  - enriched count: 2
  - property match completed: 2
  - tax overlay completed: 2
  - title friction completed: 2
  - enrichment artifacts: 6
  - no-send/provider sends remain false

## Remaining boundaries

- This wires the scheduled runtime to the enrichment pass and local artifact contract. It does not silently turn on public live tax/land-record scraping.
- Live CAD/tax/land-record clients still require registered clients plus explicit env and approval gates.
- HubSpot mirror, Instantly enrollment/send, SMS/Vapi, and paid skiptrace remain separate approval gates.
