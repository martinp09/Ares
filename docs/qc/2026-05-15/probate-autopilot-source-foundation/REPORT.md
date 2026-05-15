# QC Report — Probate Autopilot Source Foundation

## Scope

Implemented the first no-send execution slice for the Harris + Montgomery probate autopilot PRD.

This slice is intentionally limited to the scheduled/source-run foundation:

- Adds Harris + Montgomery probate source-run lane support.
- Adds source-run metadata needed by the PRD: county, run kind, raw/parsed/source-reported/keep-now counts, and idempotency key.
- Adds a Phase 1 Harris/Montgomery probate autopilot manifest builder that records safe placeholder source runs when a Trigger schedule calls the existing nightly source-pull endpoint without live county artifacts yet.
- Adds morning brief sections for county counts, keep-now totals, source-count mismatches, blocked lanes, and explicit no-send confirmation.
- Adds Trigger.dev schedule wrappers for the PRD cadence: 07:10, 12:40, 17:40, 02:20 CT, and Sunday 03:15 CT.
- Extends Trigger TypeScript contracts for Montgomery probate and PRD source-run fields.
- Updates living docs (`CONTEXT.md`, `TODO.md`, `memory.md`) with the branch/QC path, safety boundary, and next gates.

## Safety posture

No live county scraping was added in this slice.

No provider side effects were added:

- no Instantly enrollment;
- no Instantly activation;
- no email/SMS/call sends;
- no Vapi dispatch;
- no HubSpot writes;
- no paid skiptrace;
- no direct-mail vendor submission.

The new scheduled wrapper calls only `/lead-machine/internal/nightly-source-pull` with `live_source_calls: false`, `no_send: true`, and `provider_sends_enabled: false` metadata. Server-side `live_source_calls: true` remains rejected by the nightly source-pull service.

## Review

A delegated code/QC review inspected the uncommitted diff, no-send/provider safety, idempotency behavior, Pydantic/TypeScript contract alignment, Trigger schedule wrapper, tests, and QC docs.

Review result:

- No Phase 1 blockers found.
- Non-blocking review follow-ups addressed before final verification:
  - boolean count values are now ignored instead of treated as integers;
  - Trigger schedule payload metadata now includes `window_end` so generated source keys are audit-useful instead of `unspecified-window`.
- Remaining non-blocking production hardening: durable source-run/idempotency persistence beyond the current in-memory repository path before real production scheduled source pulls.

## Files changed

See `diff-summary.md` for the file list and diff stat.

## Verification

Captured in `test-output.txt`:

- `python -m pytest tests/services/test_nightly_lead_machine_service.py tests/api/test_nightly_lead_machine.py tests/api/test_trigger_contract_files.py tests/services/test_harris_probate_intake_service.py tests/services/test_probate_write_path_service.py tests/services/test_tax_overlay_service.py -q`
  - Result: `41 passed`
- `npm --prefix trigger run typecheck`
  - Result: pass
- `git diff --check`
  - Result: clean

## Remaining gates

- Implement live Harris source adapter behind the existing `live_source_calls`/source-provider gate.
- Implement/discover Montgomery probate adapter with raw label → canonical keep-now bucket mapping.
- Add raw artifact writer for real county pulls under `/opt/ares/lead-data/probate_autopilot/<run_id>/`.
- Harden source-run/idempotency persistence beyond the in-memory repository before unattended production schedules rely on it.
- Add CAD/property matching and tax overlay execution in later phases.
- Add Mission Control review/QC surfaces for the new brief sections.
- Keep HubSpot mirror and all outbound/provider actions behind separate approvals.
