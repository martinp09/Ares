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
- Back Office Spine v0 landed on `main` at `e898ee0` and the feature branch was deleted: canonical deal records, promotion from leads, lane-template tasks/document requirements/risk flags, stage blockers, fire-list read model, Supabase runtime persistence tables, and Mission Control Deal Desk read-only skeleton.
- The deal spine remains no-send: deal promotion rejects `no_send=false`, `provider_sends_enabled=false` by default, fire-list provider gate items are operator-review only, and the UI adds no send/enroll/provider action buttons.
- Origin-main hardening cleanup landed on GitHub `main`: `709f714` hardens runtime gates/CI and `be11aaa` tracks Docker deployment files; VPS edge/container hardening landed and deployed from `32a3f57`.
- Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf`; handoff docs landed at `9f30d2f`; env preflight landed at `a859fd2`; case-detail enrichment finishes the final high-value probate PRD gap.
- Trigger schedules default to live public probate source acquisition, public case-detail page enrichment, and public CAD/tax/land-record enrichment; backend live source/case-detail/CAD/tax/land flags also default on.
- Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and remains source of truth for eligibility, suppression, verification, approval, deal state, and mirror/send state; legacy `/crm/hubspot/*` live writes now also require `operator_approval=true`.
- Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deploys remain separate approval gates; GitHub Actions CI now runs backend, Mission Control, Trigger, Docker image, and whitespace gates.
- VPS `100.74.177.6` live Ares is deployed from `32a3f57`: `/opt/ares/Ares` is detached at `origin/main`, `ares-api` and `ares-ui` were rebuilt/recreated with non-root users and loopback-only Docker ports, Caddy binds only to `100.74.177.6:80` and loads the runtime bearer from root-only `/etc/caddy/ares-runtime.env`, `ares-edge-firewall.service` drops public `eth0` access to Caddy/Supabase dev ports, and Supabase migration `20260516011000_deal_spine_runtime` is applied. Post-deploy smoke: direct API `/deals` without auth `401`; tailnet `/health` 200, `/deal-desk` 200, `/deals` 200 in 327ms, `/deals/fire-list` 200 in 73ms, `/mission-control/probate-autopilot/health` 200; QC `docs/qc/2026-05-16/vps-edge-container-hardening/`.

## Current TODO
1. Monitor the next no-send probate scheduler runs after the 2026-05-16 window fix; the 07:10 CT temp-state replay now returns Harris `40` + Montgomery `8`, `sla_status=healthy`, and `partial_failures={}`.
2. Before any production no-send deployment, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.
3. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
4. Monitor VPS edge/firewall health after the `32a3f57` tailnet-only deployment; deal endpoints now use targeted Supabase reads and smoke at `/deals` 327ms / `/deals/fire-list` 73ms with no data.

## Recent Change
- 2026-05-16: Fixed Harris+Montgomery probate scheduler runtime error from the Saturday 07:10 CT run. Root cause: the background runner and Trigger schedule were using a current-day-only source window for morning catchup; current-day empty/unstable county pages caused adapter errors. Fix: 07:10 now pulls previous-day→current-day, 02:20 pulls 7 days, Sunday 03:15 pulls 30 days, and zero-row Harris/Montgomery result pages are valid non-errors. QC: `docs/qc/2026-05-16/probate-autopilot-scheduler-runtime-error/`; verification full backend `948 passed`, Trigger typecheck passed, temp-state 07:10 replay healthy with no provider side effects.
- 2026-05-16: VPS edge/container hardening deployed from `32a3f57`: Caddy now binds only to tailnet `100.74.177.6:80`, runtime bearer moved to root-only systemd env file, `ares-edge-firewall.service` drops public Caddy/Supabase-dev ports on `eth0`, Docker API/UI ports are loopback-only, containers run non-root with `no-new-privileges`/dropped caps, and targeted deal Supabase reads cut no-data `/deals` smoke from ~12s to 327ms and `/deals/fire-list` to 73ms. QC: `docs/qc/2026-05-16/vps-edge-container-hardening/`.
- 2026-05-16: Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. Post-merge verification on `main`: full backend `942 passed`, Mission Control `25 files / 82 tests`, Mission Control typecheck/build passed, Trigger typecheck passed, `git diff --check` passed.
- 2026-05-16: Back Office Spine v0 implementation added canonical deal models/repository/services/API, Supabase runtime migration/persistence hydration, Mission Control Deal Desk read-only client/page, stricter no-send promotion invariant, stage document blockers, and QC at `docs/qc/2026-05-16/back-office-spine-v0/`. Pre-merge verification: focused backend `26 passed`, full backend `942 passed`, Mission Control `25 files / 82 tests`, Mission Control typecheck/build passed, Trigger typecheck passed, `git diff --check` passed, browser spot-check passed with no console errors.
- 2026-05-16: Hardening cleanup pushed to GitHub `main`: `709f714` adds the dynamic Montgomery PublicSearch land-record end date, live no-send smoke case-detail assertion, HubSpot CRM `operator_approval=true` live-write gate, and CI; `be11aaa` tracks Docker deployment files and Docker CI.
- 2026-05-16: VPS rebuild completed on `100.74.177.6`: server worktrees at `be11aaa`, `ares-api`/`ares-ui` images rebuilt and healthy, Caddy backed up at `/etc/caddy/Caddyfile.bak.20260516T023712Z` before adding `/crm*`, `/deals*`, `/sms-agent*`, and `/voice*`, Supabase migration `20260516011000_deal_spine_runtime` applied, and verified `/health` 200, `/crm/hubspot/customization` GET 405, `/deals` 200, `/deals/fire-list` 200, `/mission-control/probate-autopilot/health` 200.
- 2026-05-15: Added deterministic no-send probate case-detail enrichment on `fix/probate-case-detail-enrichment`: party/event/document extraction, capped contact-candidate packets, case-detail source-run lanes/artifacts, scheduled live case-detail approval gate, and URL allowlist before live fetches; QC `docs/qc/2026-05-15/probate-case-detail-enrichment/`.
- 2026-05-15: Added read-only env preflight `scripts/probate_autopilot_env_contract.py` with QC at `docs/qc/2026-05-15/probate-autopilot-env-preflight/`; no live county calls/provider mutations/deploy.
- 2026-05-15: Executed PRD as live no-send operational system and fast-forwarded implementation to `origin/main` at `9c256bf`; handoff docs landed at `9f30d2f`; deleted the finished `fix/probate-autopilot-enrichment-wiring` branch.
- 2026-05-15: Manual smoke hit real Harris + Montgomery public probate sources, real public CAD/tax/land-record clients, produced `47` source records / `8` keep-now enriched rows, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`; QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`.
- 2026-05-15: Added reusable smoke script `scripts/smoke/probate_autopilot_live_no_send_smoke.py`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
