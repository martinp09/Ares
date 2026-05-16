# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/opt/ares/worktrees/ares-main`
- Release branch: `main`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf`; handoff docs landed at `9f30d2f`; env preflight landed at `a859fd2`; case-detail enrichment finishes the final high-value PRD gap.
- Trigger schedules default to live public probate source acquisition, public case-detail page enrichment, and public CAD/tax/land-record enrichment; backend live source/case-detail/CAD/tax/land flags also default on.
- Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and remains source of truth for eligibility, suppression, verification, approval, and mirror/send state.
- Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deploys remain separate approval gates.

## Current TODO
1. Before any production no-send deployment, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.
2. After production deployment, monitor no-send Trigger schedule reports for aggregate source-run/enrichment health.
3. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
4. Verify property-match lift from case-detail-derived party/address/context evidence; keep provider/send gates blocked.

## Recent Change
- 2026-05-15: Added deterministic no-send probate case-detail enrichment on `fix/probate-case-detail-enrichment`: party/event/document extraction, capped contact-candidate packets, case-detail source-run lanes/artifacts, scheduled live case-detail approval gate, and URL allowlist before live fetches; QC `docs/qc/2026-05-15/probate-case-detail-enrichment/`.
- 2026-05-15: Added read-only env preflight `scripts/probate_autopilot_env_contract.py` with QC at `docs/qc/2026-05-15/probate-autopilot-env-preflight/`; no live county calls/provider mutations/deploy.
- 2026-05-15: Executed PRD as live no-send operational system and fast-forwarded implementation to `origin/main` at `9c256bf`; handoff docs landed at `9f30d2f`; deleted the finished `fix/probate-autopilot-enrichment-wiring` branch.
- 2026-05-15: Manual smoke hit real Harris + Montgomery public probate sources, real public CAD/tax/land-record clients, produced `47` source records / `8` keep-now enriched rows, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`; QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`.
- 2026-05-15: Added reusable smoke script `scripts/smoke/probate_autopilot_live_no_send_smoke.py`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
