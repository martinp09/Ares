# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/Users/solomartin/Projects/Ares/.worktrees/feature-textgrid-sms-agent`
- Release branch: `main`
- Active planning branch: `feature/textgrid-sms-agent`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- TextGrid SMS reply-agent planning branch is open. Spec: `docs/superpowers/specs/2026-05-16-textgrid-sms-reply-agent-design.md`; implementation plan: `docs/superpowers/plans/2026-05-16-textgrid-sms-reply-agent-implementation-plan.md`; concept note: `docs/mission-control-wiki/concepts/textgrid-sms-reply-agent.md`.
- Current decision: extend the existing `/sms-agent` scaffold into an always-on reply processor; Supabase stays the hot source of truth, while Obsidian/JSONL is a redacted cold eval archive, not the live runtime store.
- Back Office Spine v0 landed on `main` at `e898ee0` and the feature branch was deleted: canonical deal records, promotion from leads, lane-template tasks/document requirements/risk flags, stage blockers, fire-list read model, Supabase runtime persistence tables, and Mission Control Deal Desk read-only skeleton.
- The deal spine remains no-send: deal promotion rejects `no_send=false`, `provider_sends_enabled=false` by default, fire-list provider gate items are operator-review only, and the UI adds no send/enroll/provider action buttons.
- Origin-main hardening cleanup landed on GitHub `main`: `709f714` hardens runtime gates/CI and `be11aaa` tracks Docker deployment files.
- Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf`; handoff docs landed at `9f30d2f`; env preflight landed at `a859fd2`; case-detail enrichment finishes the final high-value probate PRD gap.
- Trigger schedules default to live public probate source acquisition, public case-detail page enrichment, and public CAD/tax/land-record enrichment; backend live source/case-detail/CAD/tax/land flags also default on.
- Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and remains source of truth for eligibility, suppression, verification, approval, deal state, and mirror/send state; legacy `/crm/hubspot/*` live writes now also require `operator_approval=true`.
- Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deploys remain separate approval gates; GitHub Actions CI now runs backend, Mission Control, Trigger, Docker image, and whitespace gates.
- VPS `100.74.177.6` live Ares was rebuilt from `be11aaa`: `/opt/ares/Ares` and `/opt/ares/worktrees/ares-main` are at `be11aaa`, Docker images were rebuilt 2026-05-16, Caddy routes include `/crm*`, `/deals*`, `/sms-agent*`, and `/voice*`, and Supabase migration `20260516011000_deal_spine_runtime` is applied.

## Current TODO
1. Before any production no-send deployment, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.
2. After production deployment, monitor no-send Trigger schedule reports for aggregate source-run/enrichment health.
3. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
4. Profile/control-plane-cache live deal endpoints before heavy operator use; after migration they are correct but hydrate Supabase in roughly 10-11s on the VPS.

## Recent Change
- 2026-05-16: Added TextGrid SMS reply-agent Task 11 local smoke/runbook/QC artifacts: `scripts/smoke/textgrid_sms_reply_agent_smoke.py`, focused smoke-script tests, README activation notes, provider activation runbook, and QC report. Independent QC caught non-E.164 phone output redaction; fixed with regression coverage. Verification passed: focused SMS-agent closeout `99 passed`, smoke-script tests `3 passed`, full backend `1030 passed`, Mission Control `83 passed`, Mission Control typecheck/build, Trigger typecheck, and `git diff --check`; no live Supabase/TextGrid/provider mutation.
- 2026-05-16: Fixed remaining TextGrid SMS reply-agent Task 9 blockers locally: SMS agent Supabase contact ids now serialize/hydrate as `ctc_*`, approve-send only accepts original `draft_only` decisions, duplicate operator-send requests use an atomic repository claim plus Supabase partial unique index, duplicate claims map to API `409`, and focused verification passed.
- 2026-05-16: Opened `feature/textgrid-sms-agent` from current `origin/main` and added Superpowers SMS reply-agent spec/plan docs. No production envs, Supabase, provider dashboards, sends, or runtime code were changed.
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
