# Phase 7 Nightly Lead Machine QC

## Scope

Implemented the no-live nightly source-run ledger and morning brief shell for Phase 7, then applied the fix lane for lifecycle contract fields, idempotency/replay safety, warning counts, and Mission Control response minimization.

## Safety notes

- No Harris County, HCAD, HCTax, land-record, provider, Slack, or external source calls were added or run.
- `live_source_calls=true` is rejected before any source-run records are created.
- Runtime responses expose `would_call_external_sources=false` and `live_source_calls_enabled=false`.
- Missing manifests record default fixture-like source definitions with zero counts and warnings only.
- Source lanes remain separate: `harris_county_probate`, `hcad_estate_of`, `hctax_delinquency_overlay`, and `harris_land_records`.
- Runtime accepts Trigger lifecycle fields (`run_id`, `command_id`, `idempotency_key`, `trigger_run_id`) without relaxing unknown-field rejection.
- Repeated nightly source pulls and morning briefs with the same `idempotency_key` are replayed per `business_id`/`environment` without appending duplicate runs or changing stable counts.
- Mission Control source-run/latest-brief responses are summary-oriented and do not echo raw run, artifact, or request metadata.

## Verification summary

- Focused Phase 7 suite: `29 passed`.
- Provider foundation regression subset: `54 passed`.
- Full backend suite: `755 passed`.
- Trigger typecheck: blocked locally because `tsc` is not installed under `trigger` dependencies.
- `git diff --check`: passed.
