# Probate Source Provider Bridge Gate QC Report

- Timestamp UTC: `2026-05-15T11:26:54Z`
- Repo: `martinp09/Ares`
- Branch: `feature/probate-autopilot-source-foundation`
- Slice: disabled-by-default Harris/Montgomery source-provider bridge gate

## Scope

Implemented the next no-send source-provider gate as scaffolding only.

This slice adds a bridge between scheduled probate source pulls and local Harris/Montgomery export files so engineering can wire future provider adapters behind an explicit gate without changing the source-run contract again.

## What Changed

- Added `app/services/probate_source_provider_service.py`.
- Added env/config gate: `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED`, default `false`.
- Replaced the hardcoded live-source rejection in `NightlyLeadMachineService` with a provider bridge rejection path.
- Added no-send local export hydration mode: `source_provider_bridge.mode = local_export_files`.
- Hydrated bridge exports into existing probate `source_rows` metadata so the already-hardened manifest/artifact/SLA pipeline is reused.
- Propagated only safe bridge metadata into source-run rows.
- Added tests covering:
  - local export hydration
  - default live-source rejection
  - nightly service local-export bridge execution without live calls
  - unsupported bridge mode rejection

## Safety Boundary

Preserved.

- Live source calls are still disabled by default.
- Even if `live_source_calls=true`, the service rejects before work unless the env gate and explicit approval exist.
- No registered live county network/browser adapters were added.
- The only bridge mode implemented is `local_export_files`.
- No HubSpot writes, Instantly enrollment/send, SMS, Vapi, skiptrace, direct mail, Slack, or provider mutation path was added.

## Redaction / Privacy Gate

Passed.

- Raw export rows remain in source-run artifacts/internal metadata paths used by the existing source-run pipeline.
- Public Mission Control health/panel surfaces remain aggregate-only.
- Source-run manifest bridge metadata carries safe operational fields only: version/mode/counties/export count/provider adapters/no-send flags.

## Verification

Captured in `test-output.txt`:

- `python -m pytest -q` → `794 passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control test -- --run` → `24 passed / 79 tests passed`
- `npm --prefix apps/mission-control run build` → pass
- `npm --prefix trigger run typecheck` → pass
- `git diff --check` → clean

## Delegated Review

Result: PASS / no blockers.

Review focus:

- live source calls remain disabled by default
- no network/browser/provider side effects
- only local export files are read
- no raw rows exposed in public health/panel surfaces
- tests cover disabled-live and local-export bridge paths

## Remaining Gates

Still not implemented and still require explicit approval:

1. Real Harris browser/API adapter execution.
2. Real Montgomery source discovery/browser/API adapter execution.
3. Property/CAD match execution.
4. Tax overlay execution.
5. Land-record/title-friction enrichment.
6. HubSpot mirror and outbound enrollment/send gates.
