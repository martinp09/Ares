# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/opt/ares/worktrees/ares-main`
- Active branch: `fix/probate-autopilot-enrichment-wiring`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Harris + Montgomery probate autopilot PRD is now implemented as a live, operational, no-send system on this branch.
- Trigger schedules default to live public probate source acquisition and live public CAD/tax/land-record enrichment; backend live source/CAD/tax/land flags also default on.
- Ares still requires explicit no-send approval metadata for live source/enrichment runtime requests and remains source of truth for eligibility, suppression, verification, approval, and mirror/send state.
- Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deploys remain separate approval gates.

## Current TODO
1. Finalize docs/QC, commit, push, and merge `fix/probate-autopilot-enrichment-wiring` intentionally.
2. If production deployment is requested, configure durable state/artifact paths first: `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` and `LEAD_MACHINE_ARTIFACT_ROOT`.
3. Monitor no-send cron reports after deployment for aggregate source-run/enrichment health.
4. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.

## Recent Change
- 2026-05-15: Executed PRD as live no-send operational system. Manual smoke hit real Harris + Montgomery public probate sources, real public CAD/tax/land-record clients, produced `47` source records / `8` keep-now enriched rows, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`; QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`.
- 2026-05-15: Added reusable smoke script `scripts/smoke/probate_autopilot_live_no_send_smoke.py`.
- 2026-05-15: Hardened Montgomery Odyssey session launch/retry behavior and wired public enrichment clients by default.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
