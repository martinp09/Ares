# Diff Summary — Probate Production Readiness Wrap

## Code hardening

- `.env.example`
  - Clarifies that `LEAD_MACHINE_BACKEND=memory` is local-only and production no-send probate autopilot must override to `supabase`.
- `app/services/probate_source_adapter_service.py`
  - Preserves Harris `case_detail_postback_target` and `case_detail_source_url` as canonical normalized fields instead of only retaining them in raw row metadata.
- `app/services/probate_case_detail_enrichment_service.py`
  - Detects postback-only Harris detail targets from top-level, `raw`, `raw_export_row`, or `raw_live_row`.
  - Preserves explicit `incomplete_reason` for incomplete live-detail payloads.
- `app/services/probate_live_source_adapter_service.py`
  - Anchors Harris parser extraction to same-row `ListViewCases_ctrl{n}_btnSelect` anchors so page-level ASP.NET postbacks such as login links cannot be mis-associated with a probate row.

## Tests

- `tests/services/test_probate_case_detail_enrichment_service.py`
  - Adds nested raw-row Harris postback regression coverage.
- `tests/services/test_probate_live_source_adapter_service.py`
  - Adds same-row Harris postback parser regression coverage.
  - Adds normalized top-level postback-field preservation coverage.

## Docs / living context

- `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
  - Adds explicit Vapi outbound gate, production `LEAD_MACHINE_BACKEND=supabase` requirement, durable path ownership notes, and preflight activation blocker language.
- `CONTEXT.md`, `memory.md`
  - Refresh production env/preflight blocker and latest readiness state.

## QC artifacts

- `docs/qc/2026-05-16/probate-production-readiness-wrap/`
  - Captures focused/full backend tests, Trigger typecheck, env preflight status, changed-file index, and final wrap report.
