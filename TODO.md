---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-18T16:43:35Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/worktrees/ares-chief-of-staff-v0"
target_branch: "feature/ares-chief-of-staff-v0"
back_office_spine_commit: "e898ee0"
previous_handoff_commit: "9f30d2f"
implementation_commit: "9c256bf"
supabase_migration_commit: "5228ef5"
supabase_migration_qc_commit: "d0e3fb7"
production_readiness_commit: "fc99b75"
supabase_identity_adapter_commit: "6cd2d88"
---

# Ares TODO / Handoff

## Current status

Ares Chief of Staff v3 is implemented on `feature/ares-chief-of-staff-v0` for review/merge. It is now a runtime-schedulable, Slack-first read-only lead desk employee: current Ares leads are bucketed into hot/contact-ready/research/skiptrace/blocked queues, artifacts are written as Markdown/JSON/CSV, Slack delivery uses the dedicated opt-in route `chief_of_staff_digest` / `SLACK_CHANNEL_CHIEF_OF_STAFF`, the report includes employee identity/worklog/priorities/blockers/approval requests/read-only lead-machine health and stable `approve/deny cos_action_...` manager action items, and the new protected runtime endpoint `POST /ares-chief-of-staff/internal/check-in` returns a Trigger-safe `ares_chief_of_staff_check_in_v1` summary with queue counts, safety flags, and artifact path map when artifacts are written for the new Trigger tasks `chief-of-staff-check-in` and daily `chief-of-staff-check-in-0815-ct`. Slack text/blocks/payload and Trigger responses omit lead names, contact details, property addresses, case numbers, raw lead IDs, and lead-machine operator action reasons; exact record details remain in local artifacts. Safety boundaries remain hard: no seller outreach, paid skiptrace, Instantly enrollment, HubSpot/provider writes, SMS/email/Vapi sends, live county/source pulls, manager approval execution, Slack live post, Supabase remote migration, VPS deploy, or Telegram delivery occurred in this slice. Verification: focused Chief of Staff/Slack/Trigger suite `61 passed`, Trigger typecheck passed, protected API smoke `200` with Slack blocked by `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=false`, full backend `1148 passed`. QC: `docs/qc/2026-05-18/ares-chief-of-staff-trigger-check-in/`.

Mission Control operator UI refresh is also implemented on the same branch. The visible dashboard is now a real-estate operator cockpit inspired by the external Mission Control visual direction and the `builderz-labs/marketing-dashboard` analytics layout: the default overview uses a segmented KPI strip, graph-style lane performance panel, contact-mix donut, acquisition funnel, blocker chart, and segment cards for acquisition lanes/follow-up/deal movement. Backend/admin surfaces are hidden from the primary desk behind the deliberate command/search unlock `backstage`; provider operations no longer render on the primary dashboard. The latest record-navigation continuation adds a richer real-estate left rail, replaces `Organization scope` with `Operator scope` / lane filters, and exposes Records / Property Cards / Owner Cards / Skip Trace / Tax-Title pages with selected-record property-owner detail cards. Verification: Mission Control typecheck passed, `25` test files / `85` tests passed, Vite build passed, browser-harness click sweep covered `15` nav clicks with `0` failed clicks, browser smoke had `0` console/JS errors, and `git diff --check` passed. QC: `docs/qc/2026-05-18/ares-mission-control-operator-ui-refresh/`, `docs/qc/2026-05-18/ares-dashboard-analytics-segmentation/`, and `docs/qc/2026-05-18/ares-mission-control-record-segmentation/`.

Ares Appointment Setter v0 / Conversation Desk is now implemented on the same branch as the seller-facing first-step acquisitions ISA. The SMS reply decision layer now produces a qualification snapshot (`stage`, `lead_bucket`, score, missing fields, next action, appointment/nurture/disqualify flags), blocks prompt-injection and sensitive-info requests into human handoff, and enforces both `manual_control` and `appointment_setter_paused` before any `auto_ack` path. Mission Control Inbox is now labeled as a Chatwoot-inspired Conversation Desk with owner/acquisition-route/tags context, Appointment Setter score/action/risk/missing-field review, and disabled placeholder controls for takeover, reply approval, calendar-slot request, nurture, and disqualification until backend command contracts exist. Config adds `APPOINTMENT_SETTER_*` gates and `SLACK_CHANNEL_APPOINTMENT_SETTER`; Ares still owns TextGrid sends, Slack, calendar/Cal.com/Google actions, audit, policy, and kill switches. No seller sends, Slack posts, calendar writes, provider writes, paid skiptrace, or global auto-replies were executed. Verification: focused backend `48 passed`, full backend `1158 passed`, Mission Control typecheck, `25` test files / `85` tests, Vite build, `git diff --check`, and a fresh QC PASS review. QC: `docs/qc/2026-05-18/ares-appointment-setter-conversation-desk/`.

Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. This slice turns qualified leads into canonical deal records with lane-aware task/document/risk templates, stage transition blockers, fire-list read models, Supabase runtime persistence, and a read-only Mission Control Deal Desk page.

The Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf` as an operational no-send system; handoff docs landed at `9f30d2f`, env preflight landed at `a859fd2`, and production readiness/deploy wrap landed at `fc99b75`. VPS `/opt/ares/Ares` is now deployed from `619ae77` (live-source zero-row status fix); Docker `ares-api` was rebuilt/recreated from that commit, Docker `ares-api` has durable `/var/lib/ares/lead-machine` mounted, and production no-send env preflight is healthy for `limitless/prod` with `LEAD_MACHINE_BACKEND=supabase`, live intelligence gates true, and outbound/provider mutation gates false. Trigger schedules default to live public probate source acquisition, live public case-detail page enrichment, and live public CAD/tax/land-record enrichment. Trigger cloud is now promoted: Hermes Trigger CLI auth is recovered, prod version `20260516.4` is deployed, Trigger prod env points at the current Ares API through Tailscale Funnel `https://ares.tail485fd9.ts.net`, `ARES_TRIGGER_SCHEDULES_ENABLED=true`, and deployed probate schedules are exactly `07:10`, `12:40`, and `17:40` America/Chicago. Controlled Trigger lead run `run_cmp8tvbii55lq0hmz6qca6n5i` completed, generated latest brief `morning_brief_f27f1679d1884a149cf5f3d53fc09f76`, posted the lead-run digest to Slack, and protected probate health still reports `healthy/no_send_ok=true/outbound_allowed=false`. Hermes no-agent cron `815e1261ab2e` is paused and should stay paused unless intentionally rolling back Trigger authority. Backend defaults those live intelligence lanes on, but Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and keeps every outbound path blocked. Dedupe/manual-isolation hardening adds hashed probate source identities, same-scope prior-run dedupe, same-packet duplicate exclusion, `source_run_scope=autonomous` scheduled payloads, isolated manual Hermes runner state, remote Supabase durable identity schema `20260516131500_probate_source_identity_dedupe.sql` applied on 2026-05-16, and a production Supabase identity-ledger adapter used when `LEAD_MACHINE_BACKEND=supabase`; the post-adapter live no-send monitor then found Harris rows expose postback-only detail targets, now safely classified as incomplete (`case_detail_postback_only`) rather than blocked unsafe URLs. QC includes `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/`, `docs/qc/2026-05-16/probate-production-readiness-wrap/`, and the existing probate dedupe/source identity artifacts.

Origin-main hardening cleanup landed on GitHub `main`: `709f714` adds the dynamic Montgomery PublicSearch land-record end date, live no-send smoke case-detail assertion, legacy `/crm/hubspot/*` `operator_approval=true` live-write gate, and CI; `be11aaa` tracks Docker deployment files and Docker CI.

VPS edge/container hardening is complete and production probate runtime was advanced again to `619ae77` after the live-source zero-row status fix. `/opt/ares/Ares` is detached at `619ae77`; `ares-api` was rebuilt/recreated with non-root users, `no-new-privileges`, dropped caps, and loopback-only Docker API port (`127.0.0.1:8000`). `ares-ui` remains healthy from the prior rebuild and loopback-only (`127.0.0.1:8080`). Caddy remains bound only to tailnet `100.74.177.6:80`, the runtime bearer lives in root-only `/etc/caddy/ares-runtime.env`, and `ares-edge-firewall.service` drops public `eth0` traffic to Caddy/Supabase dev ports. Tailscale Funnel exposes only the FastAPI runtime at `https://ares.tail485fd9.ts.net` -> `127.0.0.1:8000` for Trigger/cloud callbacks; protected routes still return `401` without bearer and protected probate health returns `200 healthy` with the runtime key. `ares-api` has durable `/var/lib/ares/lead-machine` mounted read-write, production env preflight is healthy for `limitless/prod`, `/health` / UI local smokes pass, SMS processing is draft-only/no-auto-reply, and Slack notifications are configured. QC: `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/`, `docs/qc/2026-05-16/vps-edge-container-hardening/`, and `docs/qc/2026-05-16/probate-production-readiness-wrap/`.

Historical VPS rebuild before later hardening: `/opt/ares/Ares` and `/opt/ares/worktrees/ares-main` were at `be11aaa`; `ares-api` and `ares-ui` images were rebuilt and healthy; Caddy backup was `/etc/caddy/Caddyfile.bak.20260516T023712Z`; Caddy routes included `/crm*`, `/deals*`, `/sms-agent*`, and `/voice*`; Supabase migration `20260516011000_deal_spine_runtime` was applied. Current deployment state is `619ae77` as described above.

Latest manual live no-send smoke (`docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/live-smoke-output.txt`) completed with Harris + Montgomery counties, `47` live public probate source records, `8` keep-now rows enriched, live CAD/tax/land-record calls attempted, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`.

Back Office Spine v0 verification passed pre-merge and post-merge: focused backend/deal/Supabase contracts => `26 passed`; full backend => `942 passed`; Mission Control => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` => passed; browser spot-check rendered Deal Desk with no console errors.

Cleanup verification on the `be76288` baseline passed: focused backend => `44 passed`; full backend => `945 passed`; Mission Control tests => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` and smoke/script py-compile => passed. GitHub Actions CI passed on `709f714` and `be11aaa`.

- Before the Trigger promotion slice, no HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, live smoke, Vercel deploys, or Supabase schema changes were executed by the prior adapter slice. The later Trigger promotion slice intentionally posted controlled Slack operational notifications only; no campaign/provider sends were enabled.

## Primary handoff artifacts

- Back Office Spine v0 RPD: `/root/obsidian-vault/03-Experiments/Ares Real Estate Operating System RPD.md`
- Back Office Spine v0 QC: `docs/qc/2026-05-16/back-office-spine-v0/`
- Case-detail enrichment QC: `docs/qc/2026-05-15/probate-case-detail-enrichment/`
- Env preflight QC: `docs/qc/2026-05-15/probate-autopilot-env-preflight/`
- Env preflight command: `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live`
- Live operational PRD execution QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`
- Live no-send smoke command: `uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day YYYY-MM-DD`
- Probate dedupe/isolation QC: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`
- Supabase probate source identity migration: `supabase/migrations/20260516131500_probate_source_identity_dedupe.sql` (applied remotely 2026-05-16)
- Remote Supabase probate source identity migration QC: `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`
- Supabase probate source identity adapter QC: `docs/qc/2026-05-16/probate-source-identity-supabase-adapter/`
- Probate no-send activation runbook: `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- Probate production readiness wrap QC: `docs/qc/2026-05-16/probate-production-readiness-wrap/`
- Trigger scheduler promotion + Slack/SMS readiness QC: `docs/qc/2026-05-16/trigger-promotion-slack-sms-live/`
- Live-source zero-row status fix QC: `docs/qc/2026-05-16/live-source-zero-row-status-fix/`
- HubSpot operating-spine QC index: `docs/qc/2026-05-14/README.md`

## Immediate next actions

1. Review and merge `feature/ares-chief-of-staff-v0`; after deploy, apply `supabase/migrations/20260518130327_chief_of_staff_slack_route.sql`, configure/create/invite `SLACK_CHANNEL_CHIEF_OF_STAFF`, and keep `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=false` until readiness passes.
2. For Appointment Setter, keep `SMS_AGENT_AUTO_REPLIES_ENABLED=false` and Mission Control controls disabled until a production approval slice adds real takeover/approve/slots/nurture/disqualify command endpoints, configures `SLACK_CHANNEL_APPOINTMENT_SETTER`, and proves `manual_control` / `appointment_setter_paused` gates against live TextGrid sends.
3. For SMS, review `docs/runbooks/sms-vapi-style-contextual-reply-agent.md` and `docs/runbooks/ares-appointment-setter-conversation-desk.md`: the branch now has a Vapi-style SMS context loop with deterministic safety policy plus optional LLM copy rewriting behind `SMS_AGENT_LLM_REPLIES_ENABLED=false` by default. Do not enable global SMS auto-replies; owned-number smoke still requires `SMS_AGENT_ALLOWED_FROM_NUMBERS` and explicit approval.
4. Run `uv run python scripts/slack_notification_readiness.py --json --render-sample --route chief_of_staff_digest` before any live Chief of Staff Slack post, then enable `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=true` only for the scheduled 08:15 CT employee check-in if Martin approves live Slack reporting.
5. Review the Herrington/Browne email-marketing prep artifacts: `docs/marketing/campaigns/2026-05-18-curative-title-soft-finder-email-campaign.md`, `docs/marketing/exports/email-marketing-herrington-browne-2026-05-18/`, and sanitized QC `docs/qc/2026-05-18/email-marketing-herrington-browne-prep/`. Raw verification/contact evidence is local-only under `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/`.
6. Before any email launch, approve exact contacts, copy, Instantly draft/create/upload behavior, daily cap, and sender. Current state is no upload / no activation / no seller email send.
7. Watch the temporary owned-number SMS smoke watcher only for Martin's approved number; do not enable global SMS auto-replies. If promoting this into production behavior, add a scoped approval/receiver and max-turn/expiry gates.
8. Next employee feature: add a Slack reply inbox / decision journal for `approve cos_action_...` and `deny cos_action_...` that records manager intent only and does not call the generic approval executor or provider/send paths.
9. Watch the next automatic Trigger CT windows (`07:10`, `12:40`, `17:40` America/Chicago) for the next `limitless/prod` autonomous morning briefs and Slack lead-run digests. One-shot Hermes watcher `9ed644afbc4a` is scheduled at `2026-05-16T22:50:00Z` to verify the next `17:40 CT` Trigger run without moving production schedules.
10. Keep Hermes cron `815e1261ab2e` paused while Trigger remains authoritative; resume it only as an intentional rollback.
11. Monitor the Funnel API edge (`/health`, protected probate health with bearer, protected routes `401` without bearer) and keep Tailscale Funnel limited to the API loopback proxy.
12. Add a Harris postback case-detail client if live Harris party/event/document detail completion is required; current postback-only rows are safely incomplete, not blocked.
13. Keep Instantly enrollment/send, SMS/Vapi dispatch, paid skiptrace, and HubSpot batch mirror writes gated until separately approved.
14. Prepare the marketing launch manifest next: source-approved contacts, suppression/verification, exact copy, exact recipient limits, and approval before Instantly/SMS/email sends.

## Open product follow-ups

- Back Office Spine v0 follow-up: add operator actions for task completion/document review only after backend command contracts and approval gates are defined; current Deal Desk page is read-only.
- Add Mission Control read/approval endpoints and frontend review page for Ares offer/copy assets and Harris probate campaign launch.
- Use case-detail-derived party/address/context evidence to improve deterministic property matching; current case-detail layer records contact candidates and keeps seller-authority verification false until separate evidence.
- Reacher/SMTP-capable email verification cannot run recipient-MX mailbox probes from the current Hetzner VPS while outbound port 25 is blocked; request unblock, move verifier sidecar, or use DNS/MX/disposable-only checks until egress is available.
- Enrich Harris probate exports with email/phone via Tracerfy only after Martin explicitly approves skiptrace spend.
- Activate/upgrade the keyed Instantly workspace to a paid plan before real-account campaign sync/enrollment.
- Capture stronger primary Alen Sultanic source material and update `docs/copywriting-wiki/`.
- Add production monitoring/alerts for provider callback failures.

## Hard rules

- Do not make Mission Control frontend call Supabase directly.
- Do not run live SMS/email/calls/provider mutations without explicit approved recipients and gates.
- Do not use fixture-backed UI success as production proof.
- Do not promote a commit different from the evidenced commit.
- Do not rewrite already-applied baseline migrations in place.
- Never print secrets into QC evidence, logs, reports, or chat.

## Minimum verification before future deploy/promotion

```bash
uv run pytest -q
npm --prefix apps/mission-control ci
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
npm --prefix trigger ci
npm --prefix trigger run typecheck
git diff --check
git diff --cached --check
```
