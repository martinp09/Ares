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
- Origin-main hardening cleanup landed on GitHub `main`: `709f714` hardens runtime gates/CI and `be11aaa` tracks Docker deployment files; VPS edge/container hardening landed and deployed from `32a3f57`.
- Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf`; handoff docs landed at `9f30d2f`; env preflight landed at `a859fd2`; case-detail enrichment finishes the final high-value probate PRD gap.
- Probate autopilot dedupe/manual-isolation hardening is active: hashed source identities (`county_case_sha256_v1`), same-scope prior-run dedupe, same-packet duplicate exclusion, Trigger `source_run_scope=autonomous`, isolated Hermes manual-run state/environment, remote Supabase durable identity migration `20260516131500_probate_source_identity_dedupe.sql` applied on 2026-05-16, and the nightly service now reads/writes `public.probate_source_identities` when `LEAD_MACHINE_BACKEND=supabase`. QC: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`, `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`, and `docs/qc/2026-05-16/probate-source-identity-supabase-adapter/`.
- Trigger schedules default to live public probate source acquisition, public case-detail page enrichment, and public CAD/tax/land-record enrichment; backend live source/case-detail/CAD/tax/land flags also default on.
- Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and remains source of truth for eligibility, suppression, verification, approval, deal state, and mirror/send state; legacy `/crm/hubspot/*` live writes now also require `operator_approval=true`.
- Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deploys remain separate approval gates; GitHub Actions CI now runs backend, Mission Control, Trigger, Docker image, and whitespace gates.
- VPS `100.74.177.6` live Ares is now deployed from `fc99b75`: `/opt/ares/Ares` is detached at `origin/main`, `ares-api` and `ares-ui` were rebuilt/recreated with non-root users and loopback-only Docker ports, Caddy remains tailnet-bound, and `ares-api` has durable `/var/lib/ares/lead-machine` mounted for probate autopilot state/artifacts. Production probate no-send env preflight is healthy (`LEAD_MACHINE_BACKEND=supabase`, `limitless/prod`, explicit live intelligence gates true, explicit provider mutation gates false). Trigger cloud deploy is blocked by Trigger CLI login/auth, so Hermes no-agent cron `815e1261ab2e` is the active no-send CT scheduler/watchdog until Trigger auth is recovered. QC: `docs/qc/2026-05-16/vps-edge-container-hardening/` and `docs/qc/2026-05-16/probate-production-readiness-wrap/`.

## Current TODO
1. Watch the next Hermes no-agent CT scheduler window (or Trigger after auth recovery) for the first post-deploy `limitless/prod` autonomous morning brief; Mission Control currently reports `status=no_data` until that brief exists.
2. Recover Trigger.dev CLI auth and deploy `trigger/` from `fc99b75` or newer; once Trigger is authoritative, pause/retire Hermes autonomous scheduling to avoid duplicate source runs.
3. Add a Harris postback case-detail client if live Harris party/event/document detail completion is required; current postback-only rows are safely classified as incomplete, not blocked.
4. Continue monitoring autonomous scheduled runs for county coverage, duplicate-prior-run counts, Supabase identity-ledger recording, enrichment backlog, and no-send confirmation.
5. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.

## Recent Change
- 2026-05-16: Reconciled `feature/textgrid-sms-agent` with GitHub `origin/main` at `0fc3f80`; code merged cleanly, router-doc conflicts were resolved, and post-merge verification passed: focused backend `144 passed`, full backend `1052 passed`, Mission Control `83 passed` plus typecheck/build, Trigger typecheck, and `git diff --check`. Passworded VPS inspection found `source-runs.json` was `root:root 600`; repaired to UID/GID `999` mode `640`, and authenticated probate health now returns `200 healthy`, `no_send_ok=true`, `outbound_allowed=false`.
- 2026-05-16: Added TextGrid SMS reply-agent local runtime: signed TextGrid webhook ingest, queued reply jobs, Supabase/in-memory persistence, deterministic classifier, draft-only defaults, protected processor, Trigger schedule, Mission Control review/operator actions, redacted archive export, local smoke script, activation runbook, and QC artifacts. Independent QC caught non-E.164 phone output redaction; fixed with regression coverage. No live Supabase/TextGrid/provider mutation.
- 2026-05-16: Production-readiness wrap deployed `fc99b75` to the VPS Docker runtime, configured durable `/var/lib/ares/lead-machine` state/artifacts and `LEAD_MACHINE_BACKEND=supabase` for `limitless/prod`, and passed the read-only production env preflight with `status=healthy`, `no_send_ok=true`, `live_intelligence_ready=true`, `blockers=[]`. `ares-api` is healthy with the durable mount, `ares-ui` is running, tenant resolution for `limitless/prod` returns business PK `1`, and all provider/outbound mutation gates remain false. Trigger cloud deploy is blocked by Trigger CLI login/auth; Hermes no-agent cron `815e1261ab2e` remains the active no-send CT scheduler/watchdog until Trigger auth is recovered. QC: `docs/qc/2026-05-16/probate-production-readiness-wrap/`.
- 2026-05-16: Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. Post-merge verification on `main`: full backend `942 passed`, Mission Control `25 files / 82 tests`, Mission Control typecheck/build passed, Trigger typecheck passed, `git diff --check` passed.
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
