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
- Origin-main hardening cleanup is active on `fix/origin-main-hardening-cleanup` in `/tmp/ares-hardening-cleanup`, rebased onto `origin/main` at `be76288`.
- Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf`; handoff docs landed at `9f30d2f`; env preflight landed at `a859fd2`; case-detail enrichment finishes the final high-value probate PRD gap.
- Trigger schedules default to live public probate source acquisition, public case-detail page enrichment, and public CAD/tax/land-record enrichment; backend live source/case-detail/CAD/tax/land flags also default on.
- Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and remains source of truth for eligibility, suppression, verification, approval, deal state, and mirror/send state; legacy `/crm/hubspot/*` live writes now also require `operator_approval=true`.
- Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deploys remain separate approval gates; GitHub Actions CI now runs backend, Mission Control, Trigger, and whitespace gates.
- VPS `100.74.177.6` live Ares is Docker/Caddy wired from `/opt/ares/docker-compose.yml`; server worktrees now sit at `be76288`, but running Docker images were built 2026-04-27 and still predate current probate/HubSpot routes.

## Current TODO
1. Before any production no-send deployment, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.
2. After production deployment, monitor no-send Trigger schedule reports for aggregate source-run/enrichment health.
3. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
4. Before VPS deployment, rebuild intentionally from the clean `be76288` deployment tree or a reviewed successor; do not treat the current VPS container image as current `origin/main`.

## Recent Change
- 2026-05-16: Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. Post-merge verification on `main`: full backend `942 passed`, Mission Control `25 files / 82 tests`, Mission Control typecheck/build passed, Trigger typecheck passed, `git diff --check` passed.
- 2026-05-16: Back Office Spine v0 implementation added canonical deal models/repository/services/API, Supabase runtime migration/persistence hydration, Mission Control Deal Desk read-only client/page, stricter no-send promotion invariant, stage document blockers, and QC at `docs/qc/2026-05-16/back-office-spine-v0/`. Pre-merge verification: focused backend `26 passed`, full backend `942 passed`, Mission Control `25 files / 82 tests`, Mission Control typecheck/build passed, Trigger typecheck passed, `git diff --check` passed, browser spot-check passed with no console errors.
- 2026-05-16: Hardening cleanup on `fix/origin-main-hardening-cleanup`: dynamic Montgomery PublicSearch land-record end date, live no-send smoke asserts case-detail calls, legacy HubSpot CRM live writes require `operator_approval=true`, and `.github/workflows/ci.yml` covers backend/Mission Control/Trigger gates.
- 2026-05-16: Read-only VPS refresh: `/opt/ares/Ares` and `/opt/ares/worktrees/ares-main` are at `be76288`; Caddy routes API paths to `127.0.0.1:8000` and UI to `127.0.0.1:8080`; `ares-api`/`ares-ui` still run older 2026-04-27 images; no server mutation/deploy.
- 2026-05-15: Added deterministic no-send probate case-detail enrichment on `fix/probate-case-detail-enrichment`: party/event/document extraction, capped contact-candidate packets, case-detail source-run lanes/artifacts, scheduled live case-detail approval gate, and URL allowlist before live fetches; QC `docs/qc/2026-05-15/probate-case-detail-enrichment/`.
- 2026-05-15: Added read-only env preflight `scripts/probate_autopilot_env_contract.py` with QC at `docs/qc/2026-05-15/probate-autopilot-env-preflight/`; no live county calls/provider mutations/deploy.
- 2026-05-15: Executed PRD as live no-send operational system and fast-forwarded implementation to `origin/main` at `9c256bf`; handoff docs landed at `9f30d2f`; deleted the finished `fix/probate-autopilot-enrichment-wiring` branch.
- 2026-05-15: Manual smoke hit real Harris + Montgomery public probate sources, real public CAD/tax/land-record clients, produced `47` source records / `8` keep-now enriched rows, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`; QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`.
- 2026-05-15: Added reusable smoke script `scripts/smoke/probate_autopilot_live_no_send_smoke.py`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
