# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/opt/ares/worktrees/ares-main`
- Active branch: `fix/montgomery-probate-odyssey-adapter`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Harris + Montgomery probate autopilot source-foundation/live-adapter activation is merged into `main` with local QC evidence at `docs/qc/2026-05-15/probate-autopilot-main-merge/`.
- Montgomery Odyssey adapter fix is active on `fix/montgomery-probate-odyssey-adapter`; QC evidence lives at `docs/qc/2026-05-15/montgomery-probate-odyssey-adapter/`.
- Ares remains source of truth; HubSpot is a mirror/operator surface; Instantly/Vapi/SMS/paid skiptrace stay gated/off unless explicitly approved.
- Live probate source calls require disabled-by-default env gates plus explicit no-send approval objects.
- Live CAD/tax/land-record enrichment lanes are injectable and disabled by default.

## Current TODO
1. Manual no-send pilot now proves both public county adapters read successfully: Harris `32` parsed / `8` keep-now and Montgomery `8` parsed / `0` keep-now with `partial_failures={}`.
2. Keep `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=false` until the Montgomery fix is reviewed/merged and Martin explicitly approves Ares-side scheduled live-source execution.
3. Keep HubSpot mirror writes, Instantly enrollment, SMS/Vapi, paid skiptrace, and deploy as separate explicit approval gates.

## Recent Change
- 2026-05-15: Fixed Montgomery Odyssey live probate adapter on `fix/montgomery-probate-odyssey-adapter`: direct adapter smoke parsed 8 Montgomery rows and manual no-send autopilot smoke was healthy with no provider side effects (`docs/qc/2026-05-15/montgomery-probate-odyssey-adapter/`).
- 2026-05-15: Main merge resolved conflicts between HubSpot/provider operating-spine work and `feature/probate-autopilot-source-foundation`; verification passed backend `897 passed`, Mission Control `79 passed`, Mission Control typecheck/build, Trigger typecheck, and diff checks.
- 2026-05-15: Feature branch added no-send live probate source adapters, live enrichment seams, Trigger schedule gates, operator runbook, and QC artifacts under `docs/qc/2026-05-15/probate-autopilot-live-adapter-activation/`.
- 2026-05-13: HubSpot live apply stayed blocked by invalid/insufficient HubSpot credentials; sanitized blocker evidence lives under `docs/qc/2026-05-13/hubspot-live-apply/`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
