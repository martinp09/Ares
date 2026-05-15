# Memory

> This is the master memory file. Keep it indexed and durable. Do not load the whole file by default.

## How To Use This File

- Start in `CONTEXT.md`
- Read only the sections referenced there unless the task clearly requires more
- Record durable architecture decisions, environment notes, open work, and major change history here

## Memory Index

- Current priorities:
  - `## Current Direction`
  - `## Open Work`
- Repo conventions:
  - `## Repo Conventions`
- Environment and infra:
  - `## Environment Notes`
- Architecture:
  - `## Runtime Architecture`
  - `## Hermes Integration`
- Migration:
  - `## Migration Strategy`
- Recent work:
  - latest entry in `## Change Log`

## Current Direction

- `/opt/ares/worktrees/probate-autopilot-source-foundation` on `feature/probate-autopilot-source-foundation` is the active implementation checkout for the Harris+Montgomery probate autopilot PRD Phase 1 source-run foundation; based on `origin/feature/copywriting-brain-offer-engine`.
- Probate autopilot source-run foundation is implemented locally/pushed and now has the PRD activation layer staged: source-run lanes/fields support Harris+Montgomery probate; no-send autopilot manifests; morning brief county/keep-now/mismatch/source-quality/enrichment-backlog/operator-action/SLA/anomaly sections; Trigger.dev CT schedule wrappers; optional file-backed source-run/idempotency state (`LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`); optional source-row JSONL artifact root (`LEAD_MACHINE_ARTIFACT_ROOT`); safe local source-file payload adapter/CLI (`scripts/probate_source_file_payload.py`); read-only Harris+Montgomery export adapter contract; repeatable source-packet CLI inputs; duplicate-case aggregate anomalies; read-only doctor CLI (`scripts/probate_autopilot_doctor.py`) with freshness SLA; Mission Control health API/client (`GET /mission-control/probate-autopilot/health`); page-level Mission Control Autopilot health panel; disabled-by-default source-provider bridge gate (`source_provider_bridge.mode=local_export_files`, `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=false` default); real Harris/Montgomery public probate source adapters behind explicit approval + env gates; optional scheduled live-source activation behind `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED`; injectable CAD/tax/land enrichment behind separate live-enrichment gates; and `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`. No live county pulls or provider side effects were executed.
- HubSpot operating spine / agentic company Phases 1-9 are complete with final QC index/readiness artifacts and runbooks under `docs/qc/2026-05-14/` and `docs/runbooks/`.
- HubSpot portal customization itself was live-applied after operator instruction; HubSpot now has Ares property groups/properties and all 12 Ares stages in the existing single `Sales Pipeline` (`docs/qc/2026-05-14/hubspot-live-buildout/`).
- First synthetic HubSpot record-sync canary is complete after remote provider-links migration: contact `486079925950`, deal `325110558439`, provider links verified (`docs/qc/2026-05-14/hubspot-record-sync-canary/`).
- First real HubSpot-only lead sync is complete: hand-selected Harris probate lead `lead_341` / case `543678` created contact `485815102172` and deal `325123310274`, provider links `plink_3`/`plink_4`; rich-field correction syncs applicant/heir/probate/mailing/tax-overlay data and visibility correction fills standard HubSpot contact address fields; sync hash `hubspot-real-lead-lead_341-visible-v4`; no Instantly/Reacher/Vapi/batch/deploy side effects (`docs/qc/2026-05-14/hubspot-real-lead-sync/`, `docs/qc/2026-05-14/hubspot-rich-probate-fields/`, `docs/qc/2026-05-14/hubspot-contact-visibility-correction/`).
- Reacher/SMTP mailbox probes are blocked from the current Hetzner VPS because outbound port 25 to public MX hosts times out while 443/587 connect (`docs/qc/2026-05-14/reacher-smtp-egress/`).
- CRM control-plane work has been merged to `origin/main`.
- CRM control-plane draft spec: `docs/superpowers/specs/2026-04-25-ares-crm-control-plane-design.md`.
- CRM control-plane roadmap: `docs/superpowers/plans/2026-04-25-ares-crm-control-plane-roadmap.md`.
- CRM source research: `docs/mission-control-wiki/raw/articles/2026-04-25-ghl-datasift-crm-research.md`.
- CRM concept note: `docs/mission-control-wiki/concepts/ares-crm-control-plane.md`.
- Ares production runtime is deployed at `https://production-readiness-afternoon.vercel.app`.
- Mission Control is deployed at `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`.
- Trigger project `proj_puouljyhwiraonjkpiki` has worker version `20260425.6` deployed to prod with runtime callback env vars targeting production Ares.
- Ares is production-ready for a controlled live operator rollout; remaining work is dashboard polish and optional native `pg_dump` backup hardening.
- Approved dashboard theme direction is `docs/design/ares-dashboard-theme-2026-04-25.md`.
- `feature/ares-full-stack-cohesion-clean` completed the full-stack cohesion implementation and merged to `origin/main` at `0c14769`.
- Production-readiness handoff: `docs/production-readiness-handoff.md`.
- Production-readiness execution plan: `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`.
- `fix/origin-main-supabase-persistence-wiring` remains preserved as dirty local persistence work in `/Users/solomartin/Projects/Ares` and must be reconciled intentionally before any hosted rollout if still relevant.
- Hermes is the current primary control shell and browser-capable driver
- This repo should become the reusable real-estate operating runtime those drivers call into
- Generalist runtime first, lanes and strategies second
- Real estate is the first optimization target
- Marketing control plane is the first execution domain
- Ares North Star: self-hosted operating system for distressed real-estate lead management
- Source-of-truth implementation plan for phased Ares scope: `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md`
- Current full-stack cohesion plan: `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`
- Current full-stack cohesion spec gate: `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md`
- Combined Mission Control + enterprise backlog execution plan: `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md`
- Mission Control orchestration plan remains a live source input: `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- Enterprise agent platform plan remains a live source input: `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
- Phase 1 county baseline stays explicit: Harris, Tarrant, Montgomery, Dallas, Travis
- Phase 1 lead rule stays explicit: probate-first with tax-delinquency overlay
- Current acquisitions buy-box doctrine: exclude mobile/manufactured-home records; prioritize SFR/1–4 unit properties; tax/title core value band is roughly $150k to county median; $500k+ routes to longer-cycle creative-finance lanes. Canonical note: `docs/lead-scoring/buy-box-filters.md`.
- Curative-title source-lane wiki started at `docs/curative-title-wiki/`; bankruptcy records/PACER are an additional lane to keep in mind, not a pivot, for compressed-timeline messy-title situations including automatic stay, stacked liens, old unreleased mortgages, avoidable-judgment questions, and relief-from-stay timing.
- Phase 1 outreach rule stays explicit: drafts require human approval before send
- The runtime must cover data gathering, prospecting, acquisitions, transaction coordination, title, and dispo
- Source lanes, strategy lanes, and operational stages must stay separate concepts
- The current MVP path is a two-lane cut:
  - outbound probate as source lane with cold email as outbound method
  - inbound lease-option marketing as a separate first-class lane
- Supabase should be the canonical backend for both live MVP lanes
- The runtime should preserve a thin contract-to-close skeleton even while the MVP stays focused on lead intake, outreach, replies, and operator handoff
- Mission Control now has CRM Records, saved views, row/bulk actions, promotion, Pipeline config/stage history, and stage movement UI/API. Records prefer canonical CRM rows and fall back to live lead-machine leads when no canonical records exist.
- The host-adapter/skill seam is now in-memory and additive, with trigger_dev as the default enabled adapter; dispatch requires published revisions and preserves per-revision host adapter config
- Phase-0 docs now lock the product model: agents are the product unit, skills are reusable procedures, host runtimes are adapters, and Mission Control is the operator cockpit

## Repo Conventions

- `memory.md` is the master memory
- `CONTEXT.md` stays short and points into this file
- `WAT_Architecture.md` defines the operating model
- Keep hard guarantees in code, not in prompts

## Environment Notes

- Revenue-critical freelance capability: VPS `root@100.74.177.6` has GitHub CLI authenticated as `martinp09`, `gh auth setup-git` configured, and HTTPS Git operations verified against `martinp09/Ares`. Hermes and Ares should assume GitHub CLI is available for paid/freelance repo work unless a future `gh auth status` check fails.
- Fresh Supabase project created for Hermes Central Command
- Local `.env` should be ported from the validated `Mailers AWF` environment as needed
- GitHub owner: `martinp09`
- Planned local path: `/Users/solomartin/Projects/Hermes Central Command`
- Trigger.dev CLI login is configured on this machine
- `TRIGGER_SECRET_KEY` is present in the local `.env`
- Trigger.dev local worker boot verified against project `proj_puouljyhwiraonjkpiki`
- Local `.env` already includes `Cal.com`, `TextGrid`, and `Resend` credentials needed for the lease-option MVP
- Local development defaults `SITE_EVENTS_BACKEND=memory` unless a Supabase persistence slice is explicitly enabled.
- The active landing page lives at `/Users/solomartin/Business/website/lease-options-landing`
- The landing page currently persists form submissions and redirects to `Cal.com`, but still hands automation off to `n8n`
- A proven `TextGrid` adapter exists in `/Users/solomartin/Projects/Phone System/api/_lib/providers/textgrid.js`

## Runtime Architecture

- FastAPI runtime for typed commands and policy
- Trigger.dev for durable jobs
- Supabase for canonical state and audit
- Hermes-facing tool/API surface

## Current Runtime Surface

- FastAPI routes currently mounted:
  - `GET /health`
  - `POST /commands`
  - `POST /approvals/{approval_id}/approve`
  - `GET /runs/{run_id}`
  - `POST /replays/{run_id}`
  - `GET /hermes/tools`
  - `POST /hermes/tools/{tool_name}/invoke`
  - `POST /skills`
  - `GET /skills`
  - `GET /skills/{skill_id}`
  - `POST /agents`
  - `GET /agents/{agent_id}`
  - `POST /agents/{agent_id}/revisions/{revision_id}/publish`
  - `POST /agents/{agent_id}/revisions/{revision_id}/archive`
  - `POST /agents/{agent_id}/revisions/{revision_id}/clone`
  - `POST /organizations`
  - `GET /organizations`
  - `GET /organizations/{org_id}`
  - `POST /memberships`
  - `GET /memberships`
  - `GET /memberships/{membership_id}`
  - `POST /sessions`
  - `GET /sessions/{session_id}`
  - `POST /sessions/{session_id}/events`
  - `POST /permissions`
  - `GET /permissions/{agent_revision_id}`
  - `POST /outcomes`
  - `POST /agent-assets`
  - `GET /agent-assets/{asset_id}`
  - `POST /agent-assets/{asset_id}/bind`
  - `GET /mission-control/dashboard`
  - `GET /mission-control/lead-machine`
  - `GET /mission-control/inbox`
  - `GET /mission-control/tasks`
  - `GET /mission-control/runs`
  - `POST /marketing/webhooks/calcom`
  - `POST /marketing/webhooks/textgrid`
  - `POST /marketing/internal/non-booker-check`
  - `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
  - `POST /ares/run`
  - `POST /site-events`
  - `POST /trigger/callbacks/runs/{run_id}/started`
  - `POST /trigger/callbacks/runs/{run_id}/completed`
  - `POST /trigger/callbacks/runs/{run_id}/failed`
  - `POST /trigger/callbacks/runs/{run_id}/artifacts`
- Current storage mode:
  - hybrid mode:
    - Supabase-backed adapters for marketing, lead-machine, opportunities, and shared command/run lifecycle records (`commands`, `approvals`, `runs`, `events`, `artifacts`) when enabled
    - the remaining shared control-plane runtime now uses a Supabase-backed hydrated transaction store for:
      - agents / revisions
      - sessions / memory summaries
      - turns / turn events
      - permissions / RBAC / secrets
      - audit / usage / outcomes
      - agent assets / Mission Control threads / skills / host adapter dispatches
    - in-memory fallback still remains for tests and local fixture-first work
- Current workflow coverage:
  - marketing command classification
  - Hermes tool contract with permission-aware tool gating
  - replay safety API
  - Trigger marketing worker chain scaffold
  - landing-page site-event forwarding contract
  - managed-agent revision/session/outcome/asset scaffolding without live Supabase wiring
  - in-memory organization directory + org membership scaffolding for dogfood tenancy
  - probate intake -> scoring -> bridge -> enqueue -> webhook -> suppression/task loop
  - lease-option submit -> booking webhook -> SMS/manual-call loop
  - additive Mission Control workspaces for `Lead Machine`, `Marketing`, and `Pipeline`

## Hermes Integration

- Hermes handles chat, approvals, coordination, and operator UX
- Hermes should not be treated as the source of truth
- Every Hermes action should map to a typed runtime command

## Migration Strategy

- Start fresh on new Supabase and new runtime repo
- Build marketing control plane first
- Defer seller-ops migration off `n8n` until runtime backbone exists

## Open Work

1. review/merge the probate-autopilot source-foundation branch intentionally against `origin/main`; it is not done until committed, pushed, merged, and cleaned up
2. probate autopilot next source-provider phase: run a controlled no-send live-source pilot after durable state/artifact paths are configured; both schedule/backend source gates plus explicit approval are required, and Mission Control must remain aggregate-only
3. keep the Mission Control Autopilot page read-only and sourced from `GET /mission-control/probate-autopilot/health`; do not add provider mutation buttons until separate approval gates exist
4. activate/upgrade the newly keyed Instantly workspace to a paid plan, then rerun real-account sync from `docs/marketing/exports/instantly-campaign-backups-2026-05-02/`; current preflight is blocked by HTTP 402 / workspace has no active paid plan
5. capture stronger primary Alen Sultanic source material and update `docs/copywriting-wiki/`; current YouTube transcript access is blocked from this environment
6. add Mission Control read/approval endpoints for Ares offer/copy assets
7. add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract
8. enrich Harris probate campaign exports with email/phone via Tracerfy only after Martin explicitly approves skiptrace spend; single-record CRM skiptrace endpoint is wired, batch export enrichment remains unapproved
9. consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary; current Records bulk UI fans out through real single-record command callbacks
10. defer owner/property graph, research cockpit, and map UI until Records and stage model are stable
11. preserve production evidence files as the handoff source of truth
12. optionally replace the REST rollback bundle with native pg_dump once Supabase CLI container DNS is fixed
13. add production monitoring/alerts for provider callback failures
14. keep browser acquisition and ambiguous research in Hermes or other driver agents, not inside Ares

## Completed Branch Work

- `feature/probate-intake-supabase-wiring` rebuilt the stale `origin/feature/lead-machine-probate-intake` title-packet slice onto current `origin/main` and landed on main as `1bdd260`.
- Added first-class `TitlePacketRecord`, `TitlePacketsRepository`, `POST /mission-control/lead-machine/title-packets/import`, and migration `20260425182943_title_packets_lead_machine_wiring.sql`.
- Title-packet imports normalize old `"source": "manual"` payloads into `probate_intake` leads so Mission Control's current lead-machine projection surfaces the generated manual-review task.
- `TasksRepository` now treats `lead_machine_backend=supabase` as a Supabase-backed task path so title-packet review tasks persist with lead-machine records.

## Change Log

### 2026-05-15 Probate Autopilot No-Send Live Adapter Activation Layer

- Added real Harris Clerk WebSearch and Montgomery Odyssey probate source adapters behind `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED`, `source_provider_bridge.mode=live_source_adapters`, and explicit `source_provider_approval` with no-send/provider-disabled constraints.
- Added optional schedule activation through `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED`; schedules still default to no live county calls and include no-send approval metadata only when enabled.
- Added injectable CAD/tax/land-record enrichment client gates (`LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED`, `LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED`, `LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED`) requiring `enrichment_approval.approved=true`; enrichment responses preserve `no_send=true`, `provider_sends_enabled=false`, and `outbound_allowed=false`.
- Added operator runbook `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md` and `.env.example` gate docs. No live county pulls, HubSpot batch writes, Instantly enrollment/send, SMS, Vapi, paid skiptrace, Slack, direct mail, or deploy side effects were executed.
- Focused/final verification: backend `819 passed`, Mission Control `79 passed`, Mission Control typecheck/build, Trigger typecheck, `git diff --check`, and delegated QC PASS. Evidence: `docs/qc/2026-05-15/probate-autopilot-live-adapter-activation/`.

### 2026-05-15 Probate Source Provider Bridge Gate

- Added disabled-by-default probate source-provider bridge scaffolding: `app/services/probate_source_provider_service.py`, `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=false` by default, and `source_provider_bridge.mode=local_export_files` hydration into the existing `source_rows` manifest pipeline.
- `NightlyLeadMachineService` now delegates `live_source_calls` rejection to the bridge; no live Harris/Montgomery browser/API adapter is registered, so live requests still reject before work unless a future explicit approval + adapter implementation exists.
- Safe bridge metadata is carried into source runs without raw rows/case maps; public Mission Control health/panel surfaces remain aggregate-only.
- QC captured full backend tests (`794 passed`), Mission Control tests (`79 passed`), Mission Control typecheck/build, Trigger typecheck, `git diff --check`, and delegated QC review. Evidence: `docs/qc/2026-05-15/probate-source-provider-bridge-gate/`. No live county scraping or provider side effects.

### 2026-05-15 Probate Autopilot Mission Control Health Panel

- Added page-level Mission Control `Autopilot` view under the Lead Machine workspace backed by `GET /mission-control/probate-autopilot/health`.
- UI surfaces SLA status, freshness, no-send confirmation, source quality, aggregate duplicate-case counts by county, enrichment backlog, anomaly watch, and operator next actions without any provider mutation buttons.
- Frontend API mapping intentionally drops raw source rows, owner names, raw duplicate-case-number maps, and arbitrary payload fields; optional health fallback no longer downgrades the whole shell data-source badge.
- QC captured full backend tests (`790 passed`), Mission Control tests (`79 passed`), Mission Control typecheck/build, Trigger typecheck, `git diff --check`, and delegated QC review. Evidence: `docs/qc/2026-05-15/probate-autopilot-mission-control-health-panel/`. No live county scraping or provider side effects.

### 2026-05-15 Probate Autopilot Source Adapters + Health Surface

- Added no-send Harris+Montgomery probate export adapter contract, repeatable source-packet CLI inputs, duplicate-case aggregate anomaly detection, doctor freshness SLA, and read-only Mission Control health API/client (`GET /mission-control/probate-autopilot/health`).
- Redaction rule: raw duplicate case details remain in internal source-run metadata/artifacts only; Mission Control brief/health surfaces expose aggregate duplicate counts by county and safe source-request metadata only.
- QC captured full backend tests (`790 passed`), Mission Control tests (`76 passed`), Mission Control typecheck/build, Trigger typecheck, `git diff --check`, and two delegated review passes. Evidence: `docs/qc/2026-05-15/probate-source-adapters-health-surface/`. No live county scraping or provider side effects.

### 2026-05-14 HubSpot Contact Visibility Correction

- Root-caused Martin's HubSpot UI complaint: Ares custom fields were populated, but standard HubSpot contact address fields were still blank, and HubSpot does not automatically pin custom Ares fields to the visible record card.
- Ares contact sync now maps best-contact/mailing/applicant address strings into standard HubSpot `address/city/state/zip/country` fields when parsable.
- Live-updated existing `lead_341` contact `485815102172` and deal `325123310274` through provider links `plink_3`/`plink_4`; sync hash is now `hubspot-real-lead-lead_341-visible-v4`. Readback confirmed standard contact address fields: `1614 Royal Grantham Ct`, `Houston`, `TX`, `77073`, `United States`.
- Email/phone/mobile and property/HCAD remain true data gaps. Custom Ares field visibility still needs HubSpot UI record customization. Evidence: `docs/qc/2026-05-14/hubspot-contact-visibility-correction/`.

### 2026-05-14 HubSpot Rich Probate Fields Correction

- Expanded HubSpot/Ares CRM fields beyond the first generic real-lead sync: contacts/deals now carry probate case/court/file/status/filing metadata, best contact/applicant details, mailing/contact address, heir candidate summary/status/confidence/next gate, party/event counts, tax-overlay status, and property/HCAD placeholders.
- Live-applied missing HubSpot custom properties via the gated customization path, then updated existing `lead_341` contact `485815102172` and deal `325123310274` through provider links `plink_3`/`plink_4`; sync hash is now `hubspot-real-lead-lead_341-rich-v3`.
- Readback confirmed applicant `Brittany C Edwards`, applicant/mailing address, five heir/contact candidates, probate case `543678`, decedent `TANGIE RENEE WILLIAMS`, party/event counts, and tax-overlay status are now in HubSpot. Property address/HCAD remain blank because current Ares data has no property match for this lead.
- Evidence: `docs/qc/2026-05-14/hubspot-rich-probate-fields/`. No new HubSpot records, batch sync, Instantly/Reacher/Vapi/source-provider/Slack/deploy side effects.

### 2026-05-14 HubSpot Real Lead Sync

- Ran the first real HubSpot-only sync after preview for hand-selected `limitless/prod` Harris probate lead `lead_341` / case `543678` (`APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP`, score `95`).
- Created HubSpot contact `485815102172` and HubSpot deal `325123310274`; provider links `plink_3`/`plink_4` verified with sync hash `hubspot-real-lead-lead_341-v1`.
- Lead remains `skiptrace_status=needed` and `outreach_status=not_ready` because it has no email/phone; no Instantly enrollment/send, Reacher call, Vapi call, source-provider pull, Slack send, batch sync, deploy, or code change occurred.
- Evidence: `docs/qc/2026-05-14/hubspot-real-lead-sync/`. Future Instantly test requires warmed inboxes plus copy approval first.

### 2026-05-14 Reacher SMTP Egress Check

- Port 25 probes to Gmail/Google/Outlook/Yahoo MX hosts timed out from the Hetzner VPS; local firewall was not the blocker (`ufw` inactive, `iptables OUTPUT ACCEPT`).
- Control ports worked: `google.com:443` and `smtp.gmail.com:587` connected. This confirms general outbound works and points to provider/network-level SMTP egress blocking for recipient-MX port 25.
- Evidence: `docs/qc/2026-05-14/reacher-smtp-egress/`. No mail was sent and no Reacher config was changed.

### 2026-05-14 HubSpot Record Sync Canary

- Committed and pushed operating-spine bundle: `8c19c26` (`feat: add Ares provider operating spine`) on `feature/copywriting-brain-offer-engine`.
- Set local ignored `.env` defaults: `HUBSPOT_DEFAULT_PIPELINE_ID=default`, `HUBSPOT_DEFAULT_DEAL_STAGE_ID=3668226794`, live gates false. Backup: `/opt/ares/Ares/.env.bak.hubspot-defaults-20260514T113913Z`.
- Applied remote Supabase migration `20260514090000_provider_object_links.sql`; migration list shows local/remote both applied.
- Ran first synthetic HubSpot record-sync canary through gated Ares service: contact `486079925950`, deal `325110558439`, provider links `plink_1`/`plink_2`, sync hash `hubspot-canary-20260514-v1`.
- Evidence: `docs/qc/2026-05-14/hubspot-record-sync-canary/`. No real record batch sync, Instantly, Vapi, source-provider, Slack, or deploy side effects.

### 2026-05-14 HubSpot Live Portal Buildout

- After operator instruction, live-applied HubSpot CRM customization from Ares using the gated `HubSpotMirrorService.apply_customization` path.
- Read-only preflight passed for owners, contact/company/deal properties, and deal pipelines. Initial pipeline create failed with HubSpot `API_LIMIT` because the portal allows only one deal pipeline.
- Hardened the HubSpot customization apply path to reuse the existing single deal pipeline and add missing Ares stages instead of trying to create a second pipeline.
- Successful live apply result: 3 Ares property groups skipped/present, 36 Ares properties skipped/present, 11 missing Ares stages created, 1 existing `Closed Won` stage skipped, and the existing `Sales Pipeline`/`default` reused.
- Post-apply read-only verification found contacts `12/12`, deals `20/20`, companies `4/4` Ares properties and `12/12` Ares stages present. QC: `docs/qc/2026-05-14/hubspot-live-buildout/`.
- No HubSpot record sync, Instantly enrollment/send, Vapi call, source-provider/county pull, Slack send, deploy, audit/fix, or commit was executed in this live-buildout slice.

### 2026-05-14 Operating Spine Final Readiness Phase 9

- Added top-level QC index at `docs/qc/2026-05-14/README.md` mapping Phases 1-9, supporting HubSpot setup/smoke evidence, live-side-effect posture, and remaining gates.
- Added final readiness artifacts at `docs/qc/2026-05-14/operating-spine-final-readiness/` and runbooks at `docs/runbooks/agentic-company-operating-cadence.md` and `docs/runbooks/provider-sync-and-recovery.md`.
- Updated living docs (`CONTEXT.md`, `TODO.md`, `README.md`, and the 2026-05-14 master plan) to mark Phases 1-9 complete in the dirty working tree and to point to the QC index/runbooks.
- Final local verification for Phase 9 captured backend pytest, Mission Control tests/typecheck/build, Trigger typecheck, and `git diff --check`; no live HubSpot/Instantly/Vapi/county/Slack/provider calls, no audit/fix, and no commits.

### 2026-05-14 Mission Control Provider Ops Phase 8

- Added no-live Mission Control provider ops surface: typed read/preview API client methods for HubSpot, Instantly, Vapi dry-run, morning brief, and source runs; Dashboard renders a fixture-backed provider ops panel with no live action buttons.
- Expanded Hermes tool catalog/policy with safe preview/read provider tool names and approval-required live/apply/dispatch names; Vapi preview schema advertises `dry_run=true`.
- Safety boundary: UI and Hermes catalog expose preview/read/status only; no provider apply/enroll/send/dispatch/call execution was wired. QC: `docs/qc/2026-05-14/mission-control-provider-ops/`.
- Fix lane: aligned frontend preview request types/examples with backend `extra="forbid"` models by removing unsupported `business_id`/`environment` from HubSpot customization and Instantly enrollment preview calls; Vapi preview continues forcing `dry_run=true`; QC now includes frontend install note, `756 passed` full backend evidence, and empty `git diff --check` raw result.

### 2026-05-14 Nightly Lead Machine Phase 7

- Added no-live nightly source-pull ledger with typed source run/artifact/morning brief models, an in-memory tenant-scoped repository, and `NightlyLeadMachineService` for manifest/fixture-backed source-run orchestration.
- Runtime endpoints now include `POST /lead-machine/internal/nightly-source-pull`, `POST /lead-machine/internal/morning-brief`, `GET /mission-control/morning-brief/latest`, and `GET /mission-control/source-runs`.
- Trigger contracts now include `nightly-source-pull` and `morning-brief` wrappers through `invokeLeadMachineRuntimeApi` endpoint-map keys only; no schedules were deployed.
- Fix lane: nightly source-pull and morning-brief request models accept optional Trigger lifecycle fields (`run_id`, `command_id`, `idempotency_key`, `trigger_run_id`) while preserving `extra="forbid"`; repeated `idempotency_key` calls replay per `business_id`/`environment` without appending duplicate source runs or changing stable morning-brief counts.
- Fix lane: manifest warning counts are de-duplicated, and Mission Control latest-brief/source-runs endpoints return sanitized summary models that preserve source lane/count/status info but do not echo arbitrary run/artifact/request metadata.
- Safety boundary: Phase 7 records supplied artifacts/default fixture manifests only, sets `would_call_external_sources=false`, keeps `live_source_calls_enabled=false`, rejects `live_source_calls=true` before work, and keeps Harris probate, HCAD estate-of, HCTax delinquency overlay, and Harris land-record lanes separate. No Harris/HCAD/HCTax/source/provider/Slack calls.
- QC: `docs/qc/2026-05-14/nightly-lead-machine/`; focused Phase 7 suite passed (`29 passed`), full backend suite passed (`755 passed`), Trigger typecheck was blocked by missing local `tsc`, and `git diff --check` passed.

### 2026-05-14 Vapi Call Layer Phase 6

- Added Vapi voice-call integration scaffold with `app/providers/vapi.py`, typed call models, `VapiCallService`, and `/voice` API routes for config-only assistant/phone-number previews, outbound call dry-runs/dispatch, and Vapi webhooks.
- Live Vapi outbound dispatch is fully gated before provider calls or provider-link writes: explicit operator approval, `PROVIDER_LIVE_SENDS_ENABLED`, `VAPI_PROVIDER_LIVE_SENDS_ENABLED`, API key/private key, assistant ID, phone number ID, and `to_number`.
- Dispatch uses fake/injected clients in tests; on returned provider call IDs it writes provider links with `provider='vapi'` and `provider_object_type='call'`; missing call IDs return `submitted_unlinked` without link writes.
- Webhook first pass supports `X-Vapi-Secret == VAPI_WEBHOOK_SECRET` when `PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true`; otherwise accepted responses are marked `unverified_accepted` rather than verified.
- QC: `docs/qc/2026-05-14/vapi-call-layer/`; focused Vapi suite passed (`24 passed`), focused HubSpot/Instantly/provider-link regression suite passed (`46 passed`), full backend suite passed (`729 passed`), and `git diff --check` passed. No live Vapi calls or secrets.

### 2026-05-14 Instantly Enrollment Phase 5

- Added gated Instantly enrollment preview/apply endpoints at `POST /mission-control/providers/instantly/enrollments/preview` and `/apply`.
- `InstantlyEnrollmentService` accepts explicit CRM record payloads, previews dry-run eligibility without provider calls/token/link writes, and applies only after ordered gates: operator approval, `PROVIDER_LIVE_SENDS_ENABLED`, `INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED`, and `INSTANTLY_API_KEY`.
- Eligibility requires email, excludes suppressed/archived records, requires verified/deliverable/valid email verification by default from `verification_status`, `facts.email_verification_status`, or `raw_payload.email_verification_status`, and supports explicit `allow_unverified` override.
- Apply batches eligible records through fake/injected `bulk_add_leads`, requires exactly one explicit Instantly campaign/list provider ID, skips any existing Instantly lead provider link for the same Ares `crm_record` regardless of missing/changed `sync_hash`, writes provider links only when a per-lead provider ID is present, counts only linked records in `enrolled_count`, reports accepted-but-unlinked records as `submitted_unlinked`, and returns summary-only provider batch output.
- QC: `docs/qc/2026-05-14/instantly-enrollment/`; focused Phase 5/provider-link/outbound suite passed (`38 passed`), full backend suite passed (`705 passed`), and `git diff --check` passed. No live provider calls or secrets.

### 2026-05-14 HubSpot CRM Record Sync Phase 4

- Added gated HubSpot record apply sync at `POST /mission-control/providers/hubspot/records/apply-sync`; request requires `operator_approval`, `business_id`, `environment`, and typed record sync items.
- `HubSpotMirrorService.apply_record_sync` now gates in order before any provider call/link write: operator approval, global provider live sends, HubSpot live writes, token.
- Record apply uses provider links for create/update decisions: contacts/companies link CRM records, deals link opportunities when `opportunity_id` is present, otherwise CRM records; new creates upsert links with provider object IDs and sync hash when supplied.
- Fix lane: existing provider links with the same non-empty incoming `sync_hash` skip HubSpot update and provider-link mutation; live-capable record sync result errors are sanitized before return; no-email/phone warnings are contact-only; preflight wording now names HubSpot live writes/record sync.
- Extended HubSpot client with `update_object` (`PATCH /crm/v3/objects/{objectType}/{recordId}`); Phase 4 tests use fake clients only. No live HubSpot calls/writes.
- QC: `docs/qc/2026-05-14/hubspot-crm-sync/`; fix-lane required focused suite passed (`52 passed`), full backend suite passed (`684 passed`), and `git diff --check` passed.

### 2026-05-14 HubSpot Customization Apply Phase 3

- Added a gated Mission Control HubSpot customization apply command at `POST /mission-control/providers/hubspot/customization/apply` with explicit `operator_approval` plus global/provider/token preflight gates.
- Added safe/idempotent HubSpot customization apply service logic: create missing property groups/properties, create the Ares Acquisitions pipeline when absent, and add only missing stages by label when the pipeline already exists; no deletes/replacements.
- Extended the HubSpot client with property-group read/create and pipeline-stage create helpers; all Phase 3 write behavior is covered by fake-client tests only.
- QC: `docs/qc/2026-05-14/hubspot-customization-apply/`; focused suites passed (29 HubSpot mirror/provider tests, 21 provider-link DB tests) and full backend suite passed (`670 passed`). Follow-up retry-delay polish passed provider (`8 passed`) and focused HubSpot (`30 passed`) suites; lowercase `retry-after` is now honored case-insensitively. No live HubSpot writes or real provider tokens used.

### 2026-05-14 Provider Object Links / Sync State Phase 2

- Added Phase 2 provider mirror state: Supabase migration `20260514090000_provider_object_links.sql`, Pydantic models, and `ProviderLinksRepository` for provider object links, sync cursors, and sync runs.
- Provider links are a canonical Ares-to-provider ID index only: Ares object IDs stay canonical, provider IDs remain mirrors, and conflicting provider/Ares repoints raise deterministic `ValueError` instead of silently moving links.
- Added in-memory store/reset support plus Supabase row mapping with external ID prefixes `plink_`, `pscur_`, and `psrun_`.
- Focused Phase 2 tests passed (`13 passed`), HubSpot mirror regression tests passed (`19 passed`), and full backend suite passed (`652 passed`). No live provider calls or writes.
- QC: `docs/qc/2026-05-14/provider-object-links/`.

### 2026-05-14 HubSpot Mirror Preview

- Added Phase 1 HubSpot dry-run mirror preview slice: `app/providers/hubspot.py`, `app/services/hubspot_mirror_service.py`, Mission Control preview routes, settings, schemas, and tests.
- Preview endpoints build customization payloads and contact/deal/company sync payloads without provider calls; dry-run defaults to true and does not require a token.
- Live mutation attempts fail before provider calls unless HubSpot live writes are enabled and a token is configured. No live HubSpot writes were performed.
- Final Phase 1 security pass sanitizes HubSpot `ProviderTransportError` headers/messages before re-raise: raw `Authorization`/cookie/content headers are dropped, injected transport errors are re-wrapped, and only safe retry metadata (`Retry-After`, `X-RateLimit-*`) is preserved.
- QC: `docs/qc/2026-05-14/hubspot-mirror-preview/`; final focused security suite passed: 19 tests.

### 2026-05-14 HubSpot Service Key Smoke

- Configured local ignored `.env` with HubSpot Service Key as `HUBSPOT_ACCESS_TOKEN`; backup `.env.before-hubspot-service-key-20260514T025025Z` created and `.env` kept `0600`.
- HubSpot Service Key docs confirmed beta REST-only bearer-token behavior; it does not replace app features such as webhooks or UI extensions.
- Sanitized read-only probes returned HTTP 200 for owners, contacts/companies/deals object reads, contact/company/deal properties, and deal pipelines on both `/crm/v3/pipelines/deals` and `/crm/pipelines/2026-03/deals`.
- `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`; no HubSpot creates/updates/deletes or provider sends occurred. QC: `docs/qc/2026-05-14/hubspot-service-key-smoke/`.

### 2026-05-11 Revenue-Critical GitHub CLI Auth Signal

- Marked VPS GitHub CLI auth as a revenue-critical freelance-work capability for Hermes/Ares.
- Current verified state: `gh` authenticated as `martinp09`, `gh auth setup-git` configured, and HTTPS Git access to `martinp09/Ares` works.

### 2026-05-06 Tracerfy Local Key Configuration

- Configured local `.env` with the supplied `TRACERFY_API_KEY` and `TRACERFY_BASE_URL=https://tracerfy.com/v1/api`; backup created as `.env.before-tracerfy-api-key-20260506T015317Z`.
- No Tracerfy API calls, skiptrace lookups, batch jobs, DNC checks, outreach enrollment, sends, or lead uploads were run.
- Operator rule: ask Martin for explicit approval before any Tracerfy credit-spending action; current scope is basic phone/email skiptracing only.

### 2026-05-04 Tracerfy Skiptrace Provider Slice

- Added Tracerfy as the current Ares skiptrace provider with `TRACERFY_API_KEY` / `TRACERFY_BASE_URL` config.
- Added `app/providers/tracerfy.py` for synchronous address lookup, APN lookup, DNC lookup, queues, and address autocomplete request contracts.
- Added `app/services/skiptrace_service.py` to enrich canonical CRM records, store compact skiptrace facts, preserve raw Tracerfy response evidence, and move `needs_skip_trace` records to `clean` when contact data is returned.
- Added Mission Control endpoint `POST /mission-control/records/{record_id}/skiptrace` for one-record-at-a-time operator enrichment.
- Docs: `docs/integrations/tracerfy-skiptrace.md`.
- Focused/provider/API/repository tests pass: `uv run pytest tests/services/test_skiptrace_service.py tests/providers/test_tracerfy.py tests/api/test_mission_control.py tests/db/test_crm_records_repository.py -q` (`46 passed`).
- Full backend test suite passes after test-environment isolation hardening: `uv run pytest -q` (`620 passed`). QC: `docs/qc/2026-05-04/tracerfy-skiptrace-provider/`.

### 2026-05-03 Instantly Real Account Sync Attempt

- Updated local `.env` so `INSTANTLY_API_KEY` uses the newly supplied real-account key; backup created as `.env.before-instantly-real-account-20260503T215318Z`.
- Safe read-only preflight through `InstantlyClient.list_campaigns(limit=100)` reached Instantly but failed with HTTP 402 / `Workspace does not have an active paid plan`.
- No campaigns, subsequences, leads, sends, or activations were created on the newly keyed account.
- Existing campaign/subsequence backups remain ready under `docs/marketing/exports/instantly-campaign-backups-2026-05-02/`; rerun sync after the workspace has an active paid plan.
- QC: `docs/qc/2026-05-03/instantly-real-account-sync/`.

### 2026-05-02 Instantly Campaign Nurture Upload

- Added Ares Instantly client support for campaign subsequences: create/list/get/pause/resume methods, with focused request-construction coverage.
- Created two Instantly long-nurture subsequences from the local campaign docs:
  - Probate: `Long Nurture | Probate | 2026-05`, ID `7db2176c-2ce5-4633-a2e9-346fdc8fff43`, parent campaign `9b306264-b8d6-4ca3-8628-8d0e10f84d9c`.
  - Tax/title-friction: `Long Nurture | Tax + Title Friction | 2026-05`, ID `494fd6b6-6456-46ea-a79d-0547a172ca95`, parent campaign `70c5b447-2a72-431c-a63d-1fe8fb67c1fe`.
- Both trigger on Instantly `lead_activity: [91]` / campaign completed without reply, have 6 nurture email steps through Day 300, and use a 31-day first pre-delay after the active campaign completes.
- No leads were uploaded, no campaigns were activated, and no sends were triggered.
- Generated provider payload/response/readback backups under `docs/marketing/exports/instantly-campaign-backups-2026-05-02/` and QC under `docs/qc/2026-05-02/instantly-campaign-nurture-upload/`.

### 2026-05-02 Instantly Campaign Draft Upload

- Uploaded two Instantly draft campaigns from local campaign backups:
  - Probate: `Email | Probate | Inherited Property Relief Plan | Texas | 2026-05`, ID `9b306264-b8d6-4ca3-8628-8d0e10f84d9c`.
  - Tax/title-friction: `Email | Tax + Title Friction | Property Situation Review | Texas | 2026-05`, ID `70c5b447-2a72-431c-a63d-1fe8fb67c1fe`.
- Both campaigns have 4 active email steps, 2 subject variants per step, weekday 09:00-17:00 `America/Chicago` schedule, `stop_on_reply: true`, and `open_tracking: false`.
- No leads were uploaded, no campaigns were activated, and no sends were triggered.
- Generated provider payload/response/readback backups under `docs/marketing/exports/instantly-campaign-backups-2026-05-02/` and QC under `docs/qc/2026-05-02/instantly-campaign-draft-upload/`.

### 2026-05-02 Instantly Client Fingerprint Patch

- Patched Ares Instantly request headers to include `Accept: application/json` and `User-Agent: Mozilla/5.0 Ares/1.0 InstantlyClient`.
- Root cause narrowed to Cloudflare rejecting the default Python urllib fingerprint with HTTP 403 / `error code: 1010`, not a missing API key.
- Live patched preflight `InstantlyClient.list_campaigns(limit=1)` returned 200 with `items: []`; no campaign creation, lead upload, send, activation, or provider mutation was performed.
- Verification/QC: `docs/qc/2026-05-02/instantly-client-fingerprint-patch/`; focused tests passed `6 passed`.

### 2026-05-02 Cold Email Campaign Packets

- Created professional-service-style cold email campaign packets for probate and tax/title-friction leads under `docs/marketing/campaigns/`.
- Added local Instantly backups under `docs/marketing/exports/instantly-campaign-backups-2026-05-02/` with JSON and CSV sequence exports.
- Campaigns include high-level positioning, 4-step active cadences, long nurture through day 300 and quarterly thereafter, reply handling, compliance footer, and no-live-send guardrails.
- Instantly API preflight found `INSTANTLY_API_KEY` configured but provider returned HTTP 403 / `error code: 1010`; no campaigns, leads, sends, or activations were created from this host.
- QC: `docs/qc/2026-05-02/cold-email-campaign-packets/`.

### 2026-05-02 Ares Copywriting Brain Sultanic Formula Addendum

- Added user-provided Alen Sultanic source notes for high-response email formula and offer-code/Rosetta Stone extraction under `docs/copywriting-wiki/raw/transcripts/`.
- Added concept pages `high-response-email-formula` and `offer-code-rosetta-stone`; wiki index now tracks 15 pages.
- Extended generated offer/copy assets with recency/relevance/personalization signals, give-CTA metadata, offer-code insights, and infusion directives.
- Updated Harris probate email copy to sell the mechanism/outcome — a quick as-is review — rather than directly pitching the product; CTA gives a useful read instead of asking for a call.
- Verification/QC: `docs/qc/2026-05-01/copywriting-brain-offer-engine/`; focused suite passed `15 passed`.

### 2026-05-01 Ares Copywriting Brain Offer Engine Slice

- Initialized repo-local copywriting LLM Wiki at `docs/copywriting-wiki/` with schema, index, log, raw source notes, Hormozi/Sultanic entity pages, offer/copy concepts, and Harris probate examples.
- Added typed `OfferAsset` and `CopyAsset` models plus `CopyOfferService` and `CopyAssetService` for the Harris probate `Inherited Property Exit Option`.
- Upgraded `AresCopyService` so lead briefs/drafts use offer-first, pain-first copy with explicit human approval before provider enrollment.
- Verification/QC: `docs/qc/2026-05-01/copywriting-brain-offer-engine/`; focused service tests passed `6 passed`.
- Limitation: Alen Sultanic YouTube transcript was blocked by cloud IP / Cloudflare transcript mirror, so detailed Sultanic tactics are flagged as interpretation until stronger primary source capture.

### 2026-04-30 Harris Probate Campaign Launch Slice

- Added backend campaign-launch preview/approval API for the Harris probate HOT/WARM/COLD campaign.
- Generated no-send-before-approval CSV exports under `docs/marketing/exports/harris-probate-2026-04-30/` from `/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/hot_warm_ranked_enriched.csv`.
- Current artifact exports 464 direct-mail-ready rows and 0 email/SMS-ready rows, so enrichment is required before Instantly/TextGrid enrollment.
- Added copywriting domain-expertise plan at `docs/marketing/copywriting-domain-expertise-plan.md` and QC under `docs/qc/2026-04-30/harris-probate-campaign-launch/`.

### 2026-04-29 Full-Screen CRM Shell

- Converted Mission Control Pipeline from an inner polished panel into the default full-screen CRM surface.
- Added a CRM shell mode that uses a compact left rail, hides the legacy workspace header/context frame, and lets the Pipeline command center own the first viewport.
- Set local Mission Control to boot directly into the Pipeline workspace and tightened CRM responsive breakpoints so command metrics stay dashboard-like on desktop-width browser windows.
- Verified in browser against `http://127.0.0.1:5173/`: Pipeline opens by default and shows 482 records plus 8 opportunities from the live Supabase-backed local API after load.
- Verification passed: Mission Control shell/Pipeline/Records/API tests, frontend typecheck, frontend build, and `git diff --check`.

### 2026-04-29 Polished CRM Concept Surface

- Reworked the live Pipeline board visuals toward the generated enterprise CRM concept: light/charcoal cockpit surface, portfolio metrics, source-lane filters, full pipeline stage lanes including empty stages, polished cards, and a high-contrast opportunity drawer.
- Kept the surface wired to live Records and Opportunities data; browser verification showed 482 records, 8 opportunities, full stage lanes, lane filters, and stage-move controls loaded.
- Verification passed: Mission Control Pipeline/Records/API tests, frontend typecheck, and frontend build.

### 2026-04-29 Enterprise CRM Pipeline UI

- Added `GET /mission-control/opportunities` for scoped Pipeline opportunity rows.
- Rebuilt the Mission Control Pipeline page into an enterprise CRM board with stage columns, opportunity cards, command metrics, a selected-opportunity detail drawer, and real stage-move controls.
- Frontend now loads opportunities alongside dashboard/records and refreshes dashboard, records, and opportunities after a stage move.
- Verified against the live local Supabase-backed server: Pipeline shows 8 opportunities and Records shows 482 live records.
- Verification passed: focused backend opportunity tests, Mission Control Pipeline/Records/API tests, frontend typecheck, and frontend build.

### 2026-04-29 Remote CRM Supabase Live Data

- Applied remote Supabase migrations `20260429180000_crm_records_registry.sql`, `20260429183000_opportunity_pipeline_config.sql`, and `20260429184500_crm_record_saved_views.sql` to project `awmsrjeawcxndfnggoxw`.
- Fixed Mission Control lead-machine projection to use repositories instead of the in-memory store, so `LEAD_MACHINE_BACKEND=supabase` projects live lead-machine records into Records and dashboard summaries.
- Added `CampaignMembershipsRepository.list()` for scoped repository-backed lead-machine projections.
- Verified local API with `LEAD_MACHINE_BACKEND=supabase`: unscoped Records returns 482 live leads, dashboard record inventory returns 482 records, and Pipeline board returns 8 opportunities.
- The 482 live leads are split across `business_id=1`: 467 in `prod` and 15 in `dev`; the UI must stay on "All environments" to show the full set.

### 2026-04-29 Pipeline Stage UI

- Wired Mission Control Pipeline page to the real opportunity stage movement API.
- Added an operator form for opportunity ID, target stage, and reason; submit is disabled until an opportunity ID is present.
- Added frontend API client response mapping for updated opportunity plus stage history.
- Added focused Pipeline page/API client tests, frontend typecheck/build, and backend stage API regression evidence in `docs/qc/2026-04-29/pipeline-stage-ui/`.

### 2026-04-29 Opportunity Stage API

- Added Mission Control API endpoints for opportunity stage movement and stage-history readback.
- Stage moves use the existing configured-pipeline `OpportunityService.advance_stage` rules, including backward-move rejection and persisted stage history.
- Added API regressions for successful forward movement and rejected backward movement; evidence lives under `docs/qc/2026-04-29/opportunity-stage-api/`.

### 2026-04-29 CRM Supabase Validation

- Validated CRM Records import, saved views, status updates, promotion, opportunity pipeline config, and stage history against a local Supabase stack with the latest CRM migrations applied.
- Found and fixed a persistence boundary bug where `CrmRecordsRepository` silently forced memory mode when `MissionControlService` supplied the shared memory-backed control-plane client, even with `LEAD_MACHINE_BACKEND=supabase` enabled.
- Confirmed local Supabase row creation across CRM records/source records/saved views/status history/promotions/opportunities/pipeline configs/stage history; evidence lives under `docs/qc/2026-04-29/crm-supabase-validation/`.

### 2026-04-29 Records Promotion UI

- Exposed source lead/contact identity on canonical Mission Control Records rows from record facts, raw payload, or CRM source memberships.
- Stored imported source identity in both canonical record facts and source-membership metadata so promotion eligibility survives read-model rebuilds.
- Enabled Mission Control `Promote` row actions only for non-promoted records with source identity; identity-less rows remain disabled as `Promote gated`.
- Wired promote-from-record UI through the existing backend record promotion endpoint and refreshed Records/dashboard state after success.
- Verified Mission Control typecheck, App/Records/API frontend regressions, backend Mission Control/CRM repository tests, and `git diff --check`; evidence lives under `docs/qc/2026-04-29/records-promotion-ui/`.

### 2026-04-29 Records Action UI

- Wired Mission Control Records row actions to the real CRM command API for status updates and suppression, with optimistic record replacement and Records/dashboard refetch after each command.
- Added frontend API client methods for record status, suppression, and promotion endpoints; promotion remains UI-gated until canonical Records rows expose source lead/contact identity required by the backend contract.
- Updated Records page tests to assert real action controls exist while bare promote remains unavailable.
- Verified Mission Control typecheck, App/Records/API frontend regressions, backend Mission Control regression tests, and `git diff --check`; evidence lives under `docs/qc/2026-04-29/records-action-ui/`.

### 2026-04-29 Records Saved Views + 422 Warning Cleanup

- Added persisted CRM record saved views scoped by business/environment/slug, including repository support, Supabase migration `20260429184500_crm_record_saved_views.sql`, and Mission Control API endpoint `POST /mission-control/records/saved-views`.
- Wired `/mission-control/records` to return saved views, with default operator views when none are persisted, and added a Mission Control saved-view rail that applies saved-view filters before operator tabs.
- Removed deprecated FastAPI `HTTP_422_UNPROCESSABLE_ENTITY` usage and added a JSON-safe request validation handler so backend tests pass under `-W error::DeprecationWarning`.
- Verified with focused saved-view tests, validation-handler regression tests, full backend suite, compileall, Mission Control typecheck, and Records page tests; evidence lives under `docs/qc/2026-04-29/records-saved-views/`.

### 2026-04-29 Opportunity Pipeline Config

- Added configurable opportunity pipeline configs scoped by business/environment/source lane with ordered stage definitions.
- Added stage history persistence for opportunity stage transitions and wired `OpportunityService.advance_stage` to use configured stage order/terminal semantics.
- Added Supabase migration and repository/service/schema regression tests for pipeline config and stage history.

### 2026-04-29 Records Action API

- Added Mission Control Records action endpoints for canonical record import, status update, suppression, and promotion into opportunities.
- Added service methods that preserve source records/source memberships, write status history, create/link opportunities, and mark promoted records through `crm_record_promotions`.
- Added API regression coverage for import -> status -> suppress -> promote behavior.

### 2026-04-29 Records UI Polish

- Polished the Mission Control Records workspace with read-only operator tabs for All, Needs Skip Trace, Marketable, Suppressed, Promoted, and Incomplete.
- Expanded Records KPIs to include active/marketable inventory and no-phone counts alongside total, skip-trace, promoted, and open-task counts.
- Added record badges for record type, source, contactability, data quality, and promotion state while keeping write actions explicitly deferred until the Records command API lands.

### 2026-04-29 CRM Records Registry

- Added canonical CRM Records models and repository for `crm_records`, `crm_source_records`, `crm_record_source_memberships`, `crm_record_status_history`, and `crm_record_promotions`.
- Added Supabase migration `20260429180000_crm_records_registry.sql` with tenant-scoped tables, status/type checks, RLS policies, and record/source/promotion indexes.
- Wired Mission Control Records/dashboard read models to prefer canonical CRM records when present while preserving the existing lead-machine projection shell for scopes that have not imported canonical records yet.
- Added repository, migration, and Mission Control API regression tests for canonical Records registry behavior.

### 2026-04-29 CRM Branch Rebase

- Rebased `feature/ares-crm-control-plane-planning` onto current `origin/main` so CRM work includes the landed probate title-packet persistence commit `1bdd260`.

### 2026-04-25 CRM Records Read Model

- Started CRM buildout on `feature/ares-crm-control-plane-planning`.
- Added backend `/mission-control/records` read model derived from existing lead-machine leads, open tasks, and linked opportunities.
- Added dashboard record inventory stats so Mission Control can show record inventory before canonical CRM tables land.
- Added Mission Control frontend Records page, Records API client types/mapping, fixtures, and dashboard inventory cards.
- Verified: `uv run pytest tests/api/test_mission_control.py -q`, `npm --prefix apps/mission-control test -- --run src/lib/api.test.ts src/App.test.tsx src/pages/RecordsPage.test.tsx src/pages/DashboardPage.test.tsx`, `npm --prefix apps/mission-control run typecheck`, and `npm --prefix apps/mission-control run build`.

### 2026-04-25 CRM Control-Plane Planning

- Created and pushed planning branch `feature/ares-crm-control-plane-planning`.
- Researched current Go High Level docs for opportunities, pipelines, task reminders, multi-object tasks, contact detail, opportunity filtering, and forecasting.
- Researched DataSift/REISift docs for owner records, SiftMap, owner/property detail separation, statuses, phone status, and activity tracking.
- Captured YouTube resource metadata and chapters for both provided GoHighLevel tutorials; transcript download for the first video hit YouTube HTTP 429, so planning uses the official docs plus video chapters/descriptions.
- Added repo research note `docs/mission-control-wiki/raw/articles/2026-04-25-ghl-datasift-crm-research.md`.
- Added repo concept note `docs/mission-control-wiki/concepts/ares-crm-control-plane.md`.
- Added draft spec `docs/superpowers/specs/2026-04-25-ares-crm-control-plane-design.md`.
- Added roadmap `docs/superpowers/plans/2026-04-25-ares-crm-control-plane-roadmap.md`.
- Added vault notes under `30-Resources/Articles/2026-04-25 GoHighLevel DataSift CRM Research for Ares.md` and `wiki/Concepts/Ares CRM Control Plane.md`.
- Follow-up correction: Records must be a first-class Ares workspace and Supabase-backed canonical inventory layer. REISift uses Records for high-volume prospecting before SiftLine/lead boards; HighLevel custom objects show that non-contact business objects like properties should have first-class records, fields, relationships, workflows, dashboards, and imports. Ares opportunities should usually be promoted from records instead of every raw/source record becoming a pipeline card.

### 2026-04-25 Probate Title-Packet Supabase Wiring

- Created isolated worktree `/Users/solomartin/Projects/Ares/.worktrees/probate-intake-supabase-wiring` on `feature/probate-intake-supabase-wiring` from current `origin/main`.
- Rebuilt the stale probate intake branch as current-main code instead of merging the old branch directly.
- Added Supabase-backed title-packet persistence, import API, schema migration, package exports, and targeted tests for schema, repository, service, and Mission Control API behavior.
- Targeted verification passed: `pytest tests/api/test_mission_control_title_packet_import.py tests/api/test_mission_control_lead_machine.py tests/api/test_lead_machine.py tests/db/test_title_packets_schema.py tests/db/test_title_packets_repository.py tests/db/test_leads_repository.py tests/db/test_probate_leads_repository.py tests/db/test_tasks_supabase_adapter.py tests/services/test_title_packet_import_service.py tests/test_package_layout.py -q` (`35 passed, 1 warning`).

### 2026-04-25 Dashboard Theme Direction

- Generated and saved the approved polished ARES dashboard visual direction under `docs/design/ares-dashboard-theme-2026-04-25.md` and `docs/design/ares-dashboard-theme-2026-04-25.png`.
- Direction: real Mission Control dashboard first, dark obsidian/graphite UI, restrained ember accents, flame treatment around the `ARES` title, gothic-inspired display only for brand/title, and subtle pixel-grid tech overlays.

### 2026-04-25 Main Production Provider Wiring

- On `/Users/solomartin/Projects/Ares` `main`, production Ares now runs at `https://production-readiness-afternoon.vercel.app` with Supabase-backed runtime env and Trigger project `proj_puouljyhwiraonjkpiki`.
- Added provider-compatible runtime auth: protected routes still accept `Authorization: Bearer ...`, and provider callback URLs can use `runtime_api_key` query auth for providers that do not reliably preserve custom headers.
- Added raw Instantly provider payload support at `/lead-machine/webhooks/instantly?business_id=...&environment=...` while preserving the wrapped internal contract.
- Added form-encoded TextGrid webhook parsing for real status callbacks.
- Configured Instantly webhook `019dc29e-bd0f-7ceb-a8f6-1dd9af1a7645`; provider-side test returned success true / HTTP 200.
- Live TextGrid hosted smoke to operator phone `+13467725914` was received; signed form-encoded status callback smoke returned HTTP 200.
- Trigger prod env points at production Ares, worker version `20260425.6` deployed, and production `run_4` callback smoke reached completed status.
- Evidence files `docs/rollout-evidence/preview-2026-04-25.json` and `docs/rollout-evidence/production-2026-04-25.json` validate as ready; Cal.com, operator email smoke, and rollback bundle evidence are now captured.
- Cal.com webhook `3d941b34-6943-44ed-b9b0-8904ebab0978` was created through API v2 for booking created/rescheduled/cancelled, and synthetic production booking webhook returned HTTP 200.
- Resend live email smoke to `dejesusperales16@gmail.com` queued with provider id `4a9172b4-dd9d-403e-9b59-2cb2304cb7e1`.
- Supabase rollback bundle created at `/Users/solomartin/Projects/Ares-backups/2026-04-25-awmsrjeawcxndfnggoxw` with 50 REST-exported public tables, schema migrations, `manifest.json`, and `SHA256SUMS`; native `supabase db dump` was attempted after starting Colima but failed because the container could not resolve `db.awmsrjeawcxndfnggoxw.supabase.co`.
- Verification passed: `uv run pytest -q` (`583 passed, 6 warnings`), Mission Control vitest/typecheck/build, Trigger typecheck, `git diff --check`, `uv lock --check`, and no-live full-stack smoke.

### 2026-04-25 Production Readiness Execution

- Created isolated worktree `/Users/solomartin/Projects/Ares/.worktrees/production-readiness-afternoon` on `codex/production-readiness-afternoon` from `origin/test/production-readiness-handoff`.
- Fixed marketing lead confirmation email to use the shared Resend provider path, moved `httpx` into runtime dependencies for provider imports, added `app/index.py` as the Vercel FastAPI entrypoint, and added focused regressions.
- Added fail-closed hosted smoke assertions in `scripts/smoke_hermes_runtime_adapter.py`, rollout evidence skeleton/validator tooling, and stronger production promotion checks for completed preview/staging evidence identity.
- Linked preview Supabase project `awmsrjeawcxndfnggoxw`, passed the guarded preview dry-run, and applied migrations `202604200001`, `202604230001`, `202604230002`, `202604230003`, and `202604240001`.
- Fixed Supabase hosted runtime persistence regressions where generic synchronization tried to update/delete append-only `events` rows and projected `name` into `memberships_runtime`.
- Deployed Ares preview to Vercel as `dpl_HwBeYrGfehtsi5Mbsf9ieuPkCntw`, passed protected `vercel curl` checks for `/health`, missing runtime auth 401, authorized `/hermes/tools`, authorized `/mission-control/dashboard`, and `run_market_research` invoke/readback.
- Deployed Mission Control preview to Vercel as `dpl_FMuudqSDGp4Pz8p5XH9izfAm1hAj`; protected static checks confirmed the bundle points at the Ares preview runtime.
- Synced Trigger prod env vars with the Trigger management API and deployed worker version `20260425.3` to project `proj_puouljyhwiraonjkpiki`.
- Verified locally with `uv run pytest -q` (`580 passed, 5 warnings`), Trigger typecheck, Mission Control typecheck/tests/build, `vercel build --yes`, `uv lock --check`, and `git diff --check`.
- Rollout evidence now blocks only on provider webhook configuration, operator-owned phone/email, and guarded live provider smoke before production promotion.

### 2026-04-24 Provider Confirmation Email Readiness Fix

- Fixed `MarketingLeadService` confirmation email sending to use the service-level Resend provider path shared with Mission Control outbound email tests instead of the generic urllib request sender.
- Added focused regression coverage proving configured Resend confirmation email dispatch uses the provider sender, preserves provider message IDs, and still creates visible provider-failure manual-review tasks when Resend raises.
- Verified with `uv run pytest tests/api/test_marketing_leads.py tests/api/test_marketing_webhooks.py tests/api/test_marketing_runtime.py tests/api/test_marketing_sequence.py tests/domains/marketing/test_marketing_flow.py tests/services/test_booking_service.py tests/providers/test_resend.py tests/api/test_mission_control.py::test_provider_status_endpoint_reflects_configured_sms_and_email tests/api/test_mission_control.py::test_email_test_endpoint_returns_provider_acceptance -q` (`42 passed`) and `git diff --check`.
- Remaining caveat: the guarded live provider smoke from `docs/rollout-evidence/local-live-provider-smoke-2026-04-24.md` still needs rerun evidence against approved live recipients.

### 2026-04-24 Tax Overlay Adapter Slice

- Added `app/services/tax_overlay_service.py` with `TaxOverlayResult`, `TaxOverlayStatus`, `HarrisTaxStatementParser`, `TravisTaxSearchAdapter`/`Parser`, and `ActWebTaxDetailParser` for Dallas/Montgomery detail-page HTML.
- Added `tests/services/test_tax_overlay_service.py` covering Harris live-style statement layouts, delinquent/current status parsing, Travis quick-search payload/result parsing, official Travis table rows, and ACT Web detail parsing.
- Live smoke saved under `docs/rollout-evidence/tax-overlay-adapters-2026-04-24/`: Tangie acct `1091100001181` parsed owner `WILLIAMS TANGIE`, address `1407 GREEN TRAIL DR`, value `$214,867`, status `tax_overlay_verified_current`; McMahan acct `1172610010016` parsed owner `MCMAHAN PATRICK K & JANET`, address `5073 N NELSON AVE`, value `$320,544`, status `tax_overlay_verified_current`; Travis query `01150409100000` parsed account/owner/address/amount as a soft quick-search signal.
- Dallas/Montgomery ACT parser is fixture-ready, but live ACT hosts still need reachable samples before declaring live support.

### 2026-04-24 Tax Overlay Discovery

- Discovered official tax search/payment portals for all five Phase-1 counties; evidence saved under `docs/rollout-evidence/tax-overlay-discovery-2026-04-24/` and wiki page `docs/curative-title-wiki/Tax Overlay Adapter Matrix.md`.
- Harris: `https://www.hctax.net/Property/DelinquentTax`, direct JSON endpoint `/Property/Actions/DelAccountsList`, existing `hctax_client.py` path; parser hardening required.
- Tarrant: `https://www.tax.tarrantcountytx.gov/search`, official portal found but Cloudflare blocks current cloud/browser environment.
- Montgomery: `https://actweb.acttax.com/act_webdev/montgomery/index.jsp`, ACT Web JSP portal found; current environment timed out connecting.
- Dallas: `https://www.dallasact.com/act_webdev/dallas/index.jsp`, ACT Web JSP portal found; current environment timed out connecting.
- Travis: `https://tax-office.traviscountytx.gov/properties/taxes/account-search` / `https://travis.go2gov.net/cart/responsive/search.do`, working POST `/cart/responsive/quickSearch.do` with `criteria.heuristicSearch`.
- Ares tax overlay state policy: never set `tax_delinquent=true` from soft parser output; use explicit soft/unknown/blocked/verified states.

### 2026-04-24 HCAD Property Match Test

- Ran HCAD/property match test for the top contact-candidate packets using `/home/workspace/HCAD_Query/hcad.duckdb`; evidence saved under `docs/rollout-evidence/hcad-match-test-2026-04-24/`.
- Tangie Renee Williams (`543678`) matched high-confidence to HCAD acct `1091100001181`, owner `WILLIAMS TANGIE`, site `1407 GREEN TRAIL DR`, legal `LT 1181 BLK 24` / `FALLBROOK SEC 3`, market value `$245,311`.
- Janet Marie Mcmahan (`543652`) matched to HCAD acct `1172610010016`, owner `MCMAHAN PATRICK K and JANET`, site/mailing `5073 N NELSON AVE`, market value `$323,264`.
- Daniel R. Montoya (`525833-401`) remains ambiguous: HCAD has multiple Daniel Montoya candidates and one Larence/Lawrence Montoya respondent-name candidate, but no case-property tie until partition/property details are extracted.
- Live hctax checks on confirmed Tangie/McMahan accounts showed no delinquency signal, but the parser misread some owner/value fields; tax overlay should stay soft until parser hardening.

### 2026-04-24 Contact Candidate Packet Test

- Generated 12 contact-candidate packets from the enriched Harris probate keep-now set under `docs/rollout-evidence/contact-candidate-packets-2026-04-24/`.
- Added `docs/curative-title-wiki/Contact Candidate Packet Test.md` and linked it from the curative-title wiki hub and skiptrace workflow.
- Top packets: Tangie Renee Williams (`543678`, score 100), Daniel R. Montoya (`525833-401`, score 85), Janet Marie Mcmahan (`543652`, score 65).
- Paid skiptrace boundary: provider inputs should be normalized living candidate contacts with source lineage and explicit decedent exclusion, not raw probate rows.

### 2026-04-24 Curative Title Wiki Consolidation

- Added `docs/curative-title-wiki/index.md` as the single hub for curative-title process docs.
- Added linked wiki pages for operating model, browser-harness research workflow, county land-records playbook, evidence graph data model, skiptrace workflow, and Tangie Williams field test.
- Updated README, production-readiness handoff, and CONTEXT to point future sessions at the wiki hub.

### 2026-04-24 Tangie Williams Land-Records Recon Field Test

- Ran first browser-harness curative-title land-record recon field test on Harris probate case `543678` / Tangie Renee Williams.
- Harris real-property grantor search for `Williams Tangie` exposed a strong `FALLBROOK Sec 3 Lot 1181 Block 24` thread with 1999-2022 instruments and aliases `Tangie Williams`, `Tangie W McFadden`, and `Tangie Williams Brown`.
- The same search exposed a `PERKINS W; 4.673 acres; Abstract 621` Otis Williams estate thread with 2003 `AFFT` records likely useful for family/heir mapping.
- Free people-search checks against TruePeopleSearch, CyberBackgroundChecks, and Bing were blocked by Cloudflare/challenge in this browser environment; treat free skiptrace as an environment/access gate, not a data failure.
- Evidence saved under `docs/rollout-evidence/land-records-recon-2026-04-24/`.

### 2026-04-24 Curative Title Data Pipeline Doctrine

- Added `docs/curative-title-data-pipeline.md` to define the land-record-first curative-title workflow: deeds, affidavits, probate-related recordings, grantor/grantee chains, legal descriptions, and document details drive heir/descendant and partial-rights discovery.
- Documented browser harness / Hermes browser automation as a foundational workflow method for county land-record research; scripts should follow only after the browser workflow is proven and stable.
- Captured free-source skiptrace as a later reconnaissance layer using living candidate contacts from the evidence graph, not decedent-only rows.

### 2026-04-24 Probate Rollout Evidence

- Added Harris County probate rollout evidence under `docs/rollout-evidence/probate-smoke-2026-04-24/`: 202 raw last-week rows, 113 keep-now rows, and 12 priority heirship/title-friction detail enrichments.
- Case-detail enrichment uses the Harris Clerk `CourtCaseDetail.aspx?ID=...` AJAX detail path because the search-result list view does not expose executor/applicant/heir data.
- Ares memory-backed intake simulation accepted all 12 enriched priority cases, kept all 12, bridged all 12 into canonical leads, and scored them 59.0–75.0.
- Remaining backend gap: HCAD/property matching and tax delinquency overlay were not run; applicant/respondent/heir details currently persist in `raw_payload` instead of first-class probate fields.

### 2026-04-24 Production Readiness Handoff Branch

- Created `test/production-readiness-handoff` from `origin/main` commit `0c14769` as a test/handoff branch for the remaining live wiring gates.
- Added `docs/production-readiness-handoff.md` to define, in layman and operator terms, what remains before Ares is fully wired and production ready.
- Added `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md` with phased gates for preview Supabase, hosted Ares, Trigger.dev, Mission Control, provider webhooks, no-live smoke, guarded live provider smoke, production promotion, and evidence capture.
- Updated `CONTEXT.md`, `TODO.md`, and `README.md` to make the production-readiness handoff the active route for future sessions.

### 2026-04-24 Full-Stack Cohesion Phase 0/1 Kickoff

- Created clean worktree `/Users/solomartin/Projects/Ares-full-stack-cohesion` on `feature/ares-full-stack-cohesion-clean` from `origin/main`.
- Preserved the dirty Supabase persistence checkout at `/Users/solomartin/Projects/Ares` for later intentional reconciliation.
- Restored the remote docs branch handoff plans into the live tree: `2026-04-24-ares-full-stack-cohesion-mega-plan.md` and `2026-04-24-ares-supabase-wiring-from-memory.md`.
- Added the full-stack cohesion spec gate and local Hermes/Ares/Trigger/Supabase runbook.
- Cleaned `.env.example` into explicit runtime, Supabase, Trigger, provider, Mission Control, and model-provider sections.
- Set the local site-events default to memory-backed state so local health/smoke work does not require Supabase credentials.
- Added Vite dev proxy auth for Mission Control so local UI calls stay authenticated without exposing a public runtime key.
- Added Phase 1 config contract tests and static Trigger runtime API contract tests.

### 2026-04-24 Full-Stack Cohesion Phases 2 and 3

- Phase 2 hardened `SupabaseControlPlaneClient.transaction()` so core command-plane tables (`commands`, `approvals`, `runs`, `events`, `artifacts`) are persisted/deleted/restored with the same rollback safety as text runtime tables.
- Added FK-aware core restore ordering: commands before approvals/runs, parent runs before child replay runs, then events/artifacts; delete order remains child-first.
- Added regressions for core deletion flush, rollback after deletion/update failures, bigint string/int canonicalization, and parent-before-child run restore.
- Phase 3 added `docs/hermes-ares-runtime-adapter-contract.md`, `scripts/smoke_hermes_runtime_adapter.py`, and Hermes tool payload-stability coverage.
- Local adapter smoke succeeded against a short-lived Uvicorn server; the server was shut down afterward.

### 2026-04-24 Full-Stack Cohesion Phase 4

- Phase 4 standardized Trigger-to-Ares lifecycle callbacks through `reportRunLifecycle()` with snake_case request bodies and Ares-owned persistence.
- Lead-machine Trigger jobs now use required `runWithLifecycle()` wrapping when they are mapped to Ares runs; marketing sequence jobs use `runWithOptionalLifecycle()` because current lease-option non-booker scheduling is not yet backed by an Ares run.
- Removed the stale `create-manual-call-task` Trigger job ID and kept the planned `marketing-create-manual-call-task` job.
- Lease-option sequence child jobs no longer inherit parent `runId`/`commandId`/`idempotencyKey`, preventing delayed child jobs from mutating the parent run lifecycle.
- Manual-call and sequence child jobs now use per-lead queue keys based on business, environment, and lead.
- Artifact callbacks now persist `trigger_run_id` on the canonical run before appending artifact rows.
- QC approved Phase 4 after focused checks; broader gates passed with `uv run pytest -q`, Trigger typecheck, Mission Control tests/typecheck/build, and `git diff --check`.

### 2026-04-24 Full-Stack Cohesion Phase 5

- Phase 5 added `TEXTGRID_STATUS_CALLBACK_URL` and passes TextGrid status callback URLs through lead-intake, sequence, and booking outbound SMS paths.
- Marketing lead intake no longer silently drops provider/Trigger side-effect failures: it returns side-effect statuses and creates durable high-priority manual-review tasks with `visible_in_mission_control=true`.
- Outbound confirmation and sequence messages now persist provider message IDs when TextGrid/Resend responses expose `sid`, `message_sid`, `MessageSid`, or `id`.
- TextGrid status callbacks update durable message status by provider/external ID, record provider webhook receipts, mark them processed, and do not create false review tasks.
- Booking confirmation sends tolerate provider failures without blocking booking suppression/opportunity sync, and configured booking sends preserve successful partial provider IDs if a later channel fails.
- QC approved Phase 5 after the partial booking provider-ID blocker was fixed; broader gates passed with `uv run pytest -q`, Trigger typecheck, Mission Control tests/typecheck/build, and `git diff --check`.

### 2026-04-24 Full-Stack Cohesion Phase 6

- Phase 6 added the missing generic `POST /lead-machine/intake` seam without duplicating existing probate or marketing intake paths.
- The new `LeadIntakeService` writes existing canonical `LeadRecord` and `LeadEventRecord` records, returns `created` versus `deduped`, and keeps side-effect status fields explicit without sending live provider traffic.
- Intake replay safety uses source-namespaced external keys and deterministic `lead-intake:{business}:{environment}:{dedupe_key}` event idempotency keys.
- Unknown lead source values now fail closed instead of being silently coerced to `manual`, preserving canonical source truth and Supabase source constraints.
- Trigger now has separate `lead-intake` and `probate-intake` jobs so generic intake uses `/lead-machine/intake` while existing probate payloads keep `/lead-machine/probate/intake`.
- QC approved Phase 6 after fixing the probate Trigger path and unknown-source downgrade blockers; broader gates passed with `uv run pytest -q`, Trigger typecheck, Mission Control tests/typecheck/build, and `git diff --check`.

### 2026-04-24 Full-Stack Cohesion Phase 7

- Phase 7 added backend-owned `provider_failure_task_count` to the Mission Control dashboard response and frontend dashboard summary.
- Provider-failure task rows now preserve optional task metadata in the Mission Control API client and render distinctly in the Tasks page.
- Provider-failure dashboard/task read models are org-scoped through task details metadata so same business/environment tasks do not leak across actor orgs.
- QC approved Phase 7 after fixing the org-scoping blocker; broader gates passed with `uv run pytest -q`, Trigger typecheck, Mission Control tests/typecheck/build, and `git diff --check`.

### 2026-04-24 Full-Stack Cohesion Phase 8

- Added `RuntimeObservabilityService` as the shared nonfatal audit/usage seam for runtime command, approval, run, Trigger lifecycle, and replay paths.
- Command ingestion now appends `hermes_command_invoked` audit entries and `tool_call` usage records, including deduped command invocations scoped from the persisted command revision.
- Approval creation/approval and run creation now append runtime audit entries; run creation records `run` usage and approved-command runs route through `RunService` while preserving agent revision scope.
- Trigger lifecycle callbacks append operator-visible audit entries, and started callbacks count `host_dispatch` usage attempts with Trigger correlation metadata; no-dispatch approved runs fall back to command agent scope.
- Replay requests append actor-scoped audit while preserving existing safety: approval-required replays create approval records only and do not create child runs until approval resolution.
- Added command `agent_revision_id` persistence across memory, direct Supabase command adapters, hydrated Supabase transactions, and the additive `202604240001_command_agent_revision_scope.sql` migration.
- Verified with targeted audit/usage/replay/db regressions, `uv run pytest -q` (`542 passed, 5 warnings`), Trigger typecheck, Mission Control tests/typecheck/build, `git diff --check`, and fresh QC approval.

### 2026-04-24 Full-Stack Cohesion Phase 9

- Added deterministic in-process full-stack smoke coverage in `scripts/smoke_full_stack_cohesion.py` for `/health`, Hermes tool discovery/invocation, Trigger lifecycle callbacks, marketing lead intake, manual-call task intake, Cal.com booking webhook, TextGrid inbound webhook, Mission Control dashboard/runs, audit, usage, tasks, messages, and booking events.
- Added `scripts/smoke_provider_readiness.py` to validate TextGrid and Resend request shapes without sending; live smoke intent requires explicit provider env flags plus `--allow-live`.
- Added `docs/smoke-tests/full-stack-cohesion.md` documenting the no-live-sends local smoke flow.
- Hardened `reset_control_plane_store()` to clear dynamic marketing in-memory stores for contacts, conversations, messages, booking events, and sequence enrollments so repeated in-process smoke runs stay deterministic.
- The full-stack smoke forces memory-backed settings, clears live provider credentials in the service instances it uses, patches route-level marketing services only for the smoke duration, and blocks any attempted outbound provider request.
- QC initially found state accumulation, weak no-live guarding, and shallow Mission Control assertions; all were fixed before a fresh QC approval.
- Verified with `uv run pytest tests/smoke/test_full_stack_contract.py -q`, `uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends`, `uv run python scripts/smoke_provider_readiness.py`, `uv run pytest -q` (`545 passed, 5 warnings`), Trigger typecheck, Mission Control tests/typecheck/build, `git diff --check`, and fresh QC approval.

### 2026-04-24 Full-Stack Cohesion Phase 10

- Added `scripts/preview_rollout_readiness.py` as a guarded preview/staging readiness gate for linked Supabase target verification, required preview env, CLI availability, backend selection, and linked dry-run status.
- Added `tests/smoke/test_preview_rollout_readiness.py` covering unverified target blocking, expected project-ref requirement, backend env gating, dry-run requirement, and ready-after-dry-run behavior.
- Added `docs/preview-staging-rollout.md` with the preview rollout command sequence and no-live provider policy.
- The readiness gate refuses to run linked Supabase commands unless `--run-linked-dry-run` is present and `--expected-project-ref` matches `supabase/.temp/project-ref`.
- The readiness gate cannot report `ready`, `can_apply_preview_migrations`, or `can_run_preview_smoke` until the linked Supabase dry-run executes and passes.
- This checkout has no linked Supabase project ref; `supabase migration list --linked` and `supabase db push --dry-run --linked` fail safely with the missing-project-ref error, so no preview migrations, deploys, Trigger workers, or live provider sends were run.
- Verified with `uv run pytest tests/smoke/test_preview_rollout_readiness.py tests/smoke/test_full_stack_contract.py -q`, `uv run python scripts/preview_rollout_readiness.py` (`blocked`), `uv run pytest -q` (`550 passed, 5 warnings`), Mission Control tests/typecheck/build, Trigger typecheck, no-live full-stack smoke, `git diff --check`, and fresh QC approval.

### 2026-04-24 Full-Stack Cohesion Phase 11

- Added `scripts/production_promotion_readiness.py` as a read-only production promotion gate.
- Production promotion is blocked unless production is explicitly acknowledged, the linked Supabase project ref matches the expected production ref, the linked dry-run executes and passes, HEAD matches the staged commit, staging evidence JSON contains that same commit, a backup reference exists, required production env is present, and all runtime backends are `supabase`.
- Live provider smoke remains blocked unless `--allow-live-provider-smoke` and explicit SMS/email recipient flags are present.
- Added `tests/smoke/test_production_promotion_readiness.py` covering production acknowledgement, unverified target blocking, commit mismatch, dry-run requirement, valid ready path, live provider flags, evidence commit mismatch, and invalid evidence.
- Added `docs/production-promotion.md` documenting the promotion order, evidence contract, no-live default, and live-smoke opt-in contract.
- QC initially found that staging evidence was not bound to the staged commit and one test could call a real Supabase CLI; both were fixed before fresh QC approval.
- This checkout has no linked production Supabase project ref and no production env/evidence, so no production migrations, deploys, Trigger workers, or live provider sends were run.
- Verified with `uv run pytest tests/smoke/test_production_promotion_readiness.py tests/smoke/test_full_stack_contract.py -q`, `uv run python scripts/production_promotion_readiness.py ...` (`blocked`), `uv run pytest -q` (`558 passed, 5 warnings`), Mission Control tests/typecheck/build, Trigger typecheck, no-live full-stack smoke, `git diff --check`, and fresh QC approval.

### 2026-04-23 Origin Main Supabase Persistence Wiring

- Finished the remaining `origin/main` Supabase persistence cut on `fix/origin-main-supabase-persistence-wiring`.
- Added Supabase hydration/persistence coverage for the missing enterprise runtime collections (`organizations`, `memberships`, `catalog_entries`, `agent_installs`, `release_events`) and the Ares scope snapshots (`ares_plans_runtime`, `ares_execution_runs_runtime`, `ares_operator_runs_runtime`).
- Aligned task persistence with the live Supabase contract and fixed runtime backend rebinding so enterprise singleton services resolve against the active backend instead of stale import-time memory wiring.
- Hardened the Supabase transaction seam so failed flushes restore only rows touched by the failing request, tolerate PostgREST timestamp canonicalization / extra DB fields, and do not clobber newer same-row commits.
- Added regression coverage for enterprise runtime persistence, autonomy visibility hydration, task contract alignment, transaction-boundary rollback, flush-failure restore, and same-row concurrency protection.
- Verified with `uv run pytest tests/db/test_supabase_control_plane_client.py tests/db/test_supabase_persistence_wiring_schema.py tests/db/test_catalog_repository.py tests/db/test_organizations_repository.py tests/api/test_ares_plans.py tests/api/test_ares_runtime.py tests/api/test_mission_control.py tests/db/test_tasks_supabase_adapter.py tests/db/test_tasks_repository.py tests/db/test_marketing_repositories.py tests/api/test_organizations.py tests/api/test_memberships.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/api/test_release_management.py -q` (`86 passed`), `uv run pytest -q` (`496 passed, 5 warnings`), `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, and `supabase db reset --local` after `supabase start -x vector`.

### 2026-04-23 Governance Scope Truth Fix Follow-up

- Fixed the last merge warning in Mission Control settings/governance by keeping governance data org-scoped under secondary business/environment filters instead of half-filtering only `secretsHealth.revisions` while leaving org-wide aggregates, audit, and usage intact.
- Updated `apps/mission-control/src/App.tsx` so secondary filters no longer mutate governance read models, and updated `apps/mission-control/src/pages/SettingsPage.tsx` to state the contract explicitly: governance stays org-scoped while asset bindings honor the selected runtime filters.
- Added regressions in `apps/mission-control/src/App.test.tsx` and `apps/mission-control/src/pages/SettingsPage.test.tsx`.
- Verified with `npm --prefix apps/mission-control run test -- --run src/App.test.tsx src/pages/SettingsPage.test.tsx` (`24 passed`), `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `60 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, and `./.venv/bin/python -m pytest -q` (`471 passed, 5 warnings`).

### 2026-04-23 Release-Managed Agent Deactivation Follow-up

- Added a first-class release-management `deactivate` transition so active published revisions can be retired intentionally with an immutable release event instead of regressing the legacy archive path.
- Updated `app/db/release_management.py`, `app/services/release_management_service.py`, `app/api/release_management.py`, and `app/api/agents.py` so:
  - `POST /release-management/agents/{agent_id}/revisions/{revision_id}/deactivate` archives the active published revision, clears `active_revision_id`, appends a `deactivate` release event, and preserves lifecycle truth based on remaining non-archived revisions
  - legacy `/agents/{agent_id}/revisions/{revision_id}/archive` delegates active-revision retirement into that release-managed path while non-active archive behavior stays unchanged
- Updated release-event models/read models/UI types to allow `resulting_active_revision_id = null` for real retirement and kept Mission Control release copy truthful when the latest event retires an agent from active service.
- Added regressions in `tests/db/test_release_management_repository.py`, `tests/api/test_release_management.py`, `tests/api/test_agents.py`, and `apps/mission-control/src/pages/AgentDetailPage.test.tsx`.
- Verified with `npm --prefix apps/mission-control run test -- --run src/pages/AgentDetailPage.test.tsx src/lib/api.test.ts` (`11 passed`), `./.venv/bin/python -m pytest tests/db/test_release_management_repository.py tests/api/test_release_management.py tests/api/test_agents.py tests/api/test_mission_control.py tests/api/test_replays.py tests/services/test_mission_control_service.py -q` (`66 passed`), `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `59 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, and `./.venv/bin/python -m pytest -q` (`471 passed, 5 warnings`).

### 2026-04-23 Phase 7 QC Fix Follow-up

- Closed the two Phase 7 QC findings without widening scope:
  - `marketplace_publication_enabled` now derives live from config at read time instead of being persisted as stale point-in-time truth in catalog records
  - Mission Control catalog install copy now speaks in terms of selected target scope, and install success messaging explicitly reports when the install landed outside the current filtered view
- Updated `app/models/catalog.py`, `app/db/catalog.py`, and `app/services/catalog_service.py` so catalog responses keep visibility metadata truthful even if the marketplace-publication gate flips after the entry was created.
- Updated `apps/mission-control/src/App.tsx`, `apps/mission-control/src/pages/CatalogPage.tsx`, `apps/mission-control/src/components/AgentInstallWizard.tsx`, and related frontend tests so scope-switch/install messaging stays honest and same-scope installs still refresh the visible agents surface.
- Added/updated regressions in `tests/api/test_catalog.py`, `tests/db/test_catalog_repository.py`, `apps/mission-control/src/App.test.tsx`, and `apps/mission-control/src/pages/CatalogPage.test.tsx`.
- Verified with `npm --prefix apps/mission-control run test -- --run src/App.test.tsx src/pages/CatalogPage.test.tsx src/lib/api.test.ts` (`32 passed`), `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `59 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, `./.venv/bin/python -m pytest tests/api/test_catalog.py tests/db/test_catalog_repository.py tests/api/test_agent_installs.py tests/api/test_agents.py -q` (`24 passed`), and `./.venv/bin/python -m pytest -q` (`469 passed, 5 warnings`).

### 2026-04-23 Phase 7 Slice P7.3 Marketplace Readiness Flags

- Added a fail-closed marketplace publication gate in `app/core/config.py` + `app/services/agent_registry_service.py`: `marketplace_published` is now blocked by default unless `marketplace_publish_enabled` is explicitly turned on, so public launch cannot happen by accident.
- Extended catalog metadata in `app/models/catalog.py`, `app/db/catalog.py`, and `app/services/catalog_service.py` so catalog entries now expose source-agent visibility plus a derived `marketplace_publication_enabled` flag while remaining org-scoped internal catalog records.
- Updated Mission Control catalog mapping + UI (`apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/lib/fixtures.ts`, `apps/mission-control/src/pages/CatalogPage.tsx`) so operators can see listing visibility and whether public launch is still disabled without implying an actual marketplace rollout.
- Added focused regressions for the new gate + metadata in `tests/api/test_agents.py`, `tests/api/test_catalog.py`, `tests/api/test_agent_installs.py`, `tests/db/test_catalog_repository.py`, `apps/mission-control/src/lib/api.test.ts`, and `apps/mission-control/src/pages/CatalogPage.test.tsx`.
- Verified with `./.venv/bin/python -m pytest tests/api/test_catalog.py tests/api/test_agent_installs.py -q` (`6 passed`), `./.venv/bin/python -m pytest tests/api/test_agents.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/db/test_catalog_repository.py -q` (`23 passed`), `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `58 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, and `./.venv/bin/python -m pytest -q` (`468 passed, 5 warnings`).

### 2026-04-23 Phase 7 Slice P7.2 Catalog UI

- Added `apps/mission-control/src/pages/CatalogPage.tsx`, `apps/mission-control/src/components/AgentInstallWizard.tsx`, and `apps/mission-control/src/pages/CatalogPage.test.tsx` to expose the internal catalog as a bounded Mission Control surface on top of the already-landed `P7.1` backend APIs.
- Updated `apps/mission-control/src/App.tsx`, `apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/lib/fixtures.ts`, `apps/mission-control/src/App.test.tsx`, and `apps/mission-control/src/lib/api.test.ts` so the shell can fetch catalog entries, install a selected entry into the current runtime scope, and keep the UI truthful about org scope + fallback state.
- Closed the main truthfulness risks discovered during review:
  - fixture-backed catalog entries are visible for dogfood inspection but installs are disabled until `/catalog` is live again
  - catalog entries now carry `orgId`, are normalized to the selected org scope, and neutralize outside the internal org instead of leaking internal fixtures
  - install success/failure writes are dropped when the operator changes scope mid-request
- Added focused regressions covering catalog mapping/install behavior, fixture-backed install disabling, and org-scope neutralization in `apps/mission-control/src/App.test.tsx`, `apps/mission-control/src/lib/api.test.ts`, and `apps/mission-control/src/pages/CatalogPage.test.tsx`.
- Verified with `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `58 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, and `./.venv/bin/python -m pytest -q` (`465 passed, 5 warnings`).

### 2026-04-23 Phase 7 Slice P7.1 Catalog Domain (backend/domain)

- Added `app/models/catalog.py`, `app/models/agent_installs.py`, `app/db/catalog.py`, `app/db/agent_installs.py`, `app/services/catalog_service.py`, `app/services/agent_install_service.py`, `app/api/catalog.py`, and `app/api/agent_installs.py` for the first bounded internal catalog/install domain.
- Updated `app/db/client.py` and `app/main.py` so the in-memory control-plane store now tracks catalog entries + install lineage and the new routers are mounted behind the existing runtime API-key guard.
- Kept execution semantics stable by making installs reuse the existing agent-creation contract: catalog entries point at agent revisions with derived host/provider/skill/secret/release compatibility metadata, while installs create new agent/revision records plus a first-class install lineage record instead of adding a parallel runtime path.
- Added focused repository/API coverage in `tests/db/test_catalog_repository.py`, `tests/db/test_agent_install_repository.py`, `tests/api/test_catalog.py`, and `tests/api/test_agent_installs.py`.
- Verified with `./.venv/bin/python -m pytest tests/db/test_catalog_repository.py tests/db/test_agent_install_repository.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/api/test_agents.py -q` (`21 passed`) and `./.venv/bin/python -m pytest -q` (`460 passed, 5 warnings`).

### 2026-04-23 Phase 6 Completion Through P6.5 (QC-approved)

- Closed the remaining Phase 6 Mission Control slices on the active non-Supabase path:
  - `P6.3` added release/host visibility through `AgentReleasePanel`, `HostAdapterBadge`, and the agents-first shell wiring
  - `P6.4` added read-only governance surfaces for secrets health, audit, usage, and settings
  - `P6.5` added org-aware navigation/filtering with an `OrgSwitcher`, org-scoped API headers, secondary `business_id` / `environment` request scoping, and bounded fallback truth-gating
- Updated `app/services/organization_service.py` so the internal/default operator path can enumerate seeded orgs while non-internal actors remain self-scoped, preserving the non-Supabase tenancy seam.
- Updated the Mission Control frontend (`apps/mission-control/src/App.tsx`, `apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/pages/InboxPage.tsx`, and related tests/components) so:
  - scope switches neutralize prior-scope inbox/agent content while the next org/business/environment load is in flight
  - fallback data still respects secondary business/environment filters
  - org-only fixture fallback now fails neutral for dashboard/inbox/tasks/approvals/settings surfaces instead of relabeling internal fixture truth under another org
  - settings assets now re-fetch on scoped `business_id` / `environment` changes because the cache key matches the scoped request contract
- Expanded `tests/api/test_mission_control.py`, `tests/api/test_organizations.py`, `tests/services/test_mission_control_service.py`, `apps/mission-control/src/App.test.tsx`, `apps/mission-control/src/lib/api.test.ts`, `apps/mission-control/src/components/OrgSwitcher.test.tsx`, `apps/mission-control/src/components/MissionControlShell.test.tsx`, and `apps/mission-control/src/pages/InboxPage.test.tsx` with focused regressions for org-aware scope switching, neutral pending states, scoped fallback filtering, and settings asset re-scoping.
- Verified the final Phase 6 branch state with:
  - `npm --prefix apps/mission-control run test -- --run` (`19 files passed`, `52 tests passed`)
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run build`
  - `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest tests/api/test_mission_control.py tests/api/test_agents.py tests/api/test_release_management.py tests/api/test_organizations.py tests/services/test_mission_control_service.py -q` (`53 passed`)
  - `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest -q` (`458 passed, 5 warnings`)
- Fresh `gpt-5.4` XHIGH QC approved the current `P6.5` diff with no remaining blocker-level findings.

### 2026-04-23 Phase 6 Slice P6.2 Read-Only Agent Detail Workflow (QC-approved)

- Added the first bounded Mission Control agent-detail surface via `apps/mission-control/src/pages/AgentDetailPage.tsx`, wired from the agents-first workspace through `apps/mission-control/src/App.tsx` and `apps/mission-control/src/components/AgentRegistryTable.tsx`, while keeping the slice strictly read-only with no publish/rollback controls.
- Expanded the frontend Mission Control data seam in `apps/mission-control/src/lib/api.ts` plus fixtures/tests so the detail page can project revisions, release history, secrets health, recent audit, usage, and turns, and so partial auxiliary failures now mark degraded sections explicitly instead of silently pretending empty-state truth.
- Closed the remaining truthfulness blockers in the final pass:
  - the side context panel now uses the same loading/id-match truth gate as the main detail pane and no longer risks stale detail during agent switching
  - degraded root-detail fallback now preserves summary `slug`, `description`, `businessId`, `createdAt`, and `updatedAt`, while leaving lifecycle truth unavailable unless the summary actually provides it
  - shell-level `statusBadge` / `footerNote` now reconcile after agents-surface recovery instead of lagging behind stale fixture-fallback state
- Added focused regressions in `apps/mission-control/src/App.test.tsx` and `apps/mission-control/src/lib/api.test.ts` covering context-panel loading neutrality, degraded summary-truth preservation, lifecycle-truth non-fabrication, and shell/source reconciliation after agents recovery.
- Verified the closed slice with `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest tests/api/test_mission_control.py tests/api/test_agents.py tests/api/test_release_management.py -q`, and `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest -q` (`25 frontend tests passed`, `40 targeted backend tests passed`, `452 passed, 5 warnings` full backend suite).
- Fresh `gpt-5.4` XHIGH QC approved the current `P6.2` diff with no remaining blocker-level findings.

### 2026-04-22 Phase 6 Slice P6.1 Agents-First Mission Control Navigation

- Updated `apps/mission-control/src/App.tsx`, `apps/mission-control/src/components/MissionControlShell.tsx`, and `apps/mission-control/src/pages/AgentsPage.tsx` so lead-machine and marketing now default to agent-centered pages, the shell copy explicitly frames agents as the product unit, and approvals/runs sit beside dashboard/inbox as operator views around agents without introducing P6.2 detail pages or new control surfaces.
- Added bounded UI-only glue for agent/operator-view cards plus approvals navigation, keeping the no-Supabase path intact and preserving the existing fixture/live read-model wiring.
- Expanded `apps/mission-control/src/App.test.tsx`, `apps/mission-control/src/components/MissionControlShell.test.tsx`, and `apps/mission-control/src/pages/AgentsPage.test.tsx` with failing-first coverage for the agents-first IA, adjacent operator-view summaries, and approvals visibility.
- Verified with `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run typecheck`, and `npm --prefix apps/mission-control run build`.

### 2026-04-22 Phase 5 Slice P5.3 Replay Lineage Blocker Repair

- Added `app/services/replay_lineage_service.py` and refactored replay lineage derivation there so both immediate replays and later-approved replay approvals reuse the same actor/revision/release-context logic while keeping replay/source revision ids pinned to the historical parent run.
- Updated `app/services/replay_service.py` to create replay-owned command records with fresh idempotency keys before dispatch or approval creation, eliminating reuse of the original command identity and preserving the original command's `run_id`.
- Updated `app/services/approval_service.py` and `app/services/run_lifecycle_service.py` so replay approvals persist lineage metadata inside the existing approval payload snapshot, approved replay children are created with `parent_run_id`/`replay_reason`, and child-only `replay_lineage_bound` events are appended at approval time without duplicating the parent replay-request event.
- Expanded `tests/api/test_replays.py` and `tests/api/test_approvals.py` with failing-first regressions proving replay no longer overwrites the original command/run binding and approval-required replay later creates a distinct child run with preserved replay lineage bound on approval.
- Verified with `./.venv/bin/python -m pytest tests/api/test_replays.py tests/api/test_approvals.py -q` (`9 passed`; failing-first repro was `2 failed, 7 passed`).

### 2026-04-22 Phase 5 Slice P5.3 Replay Lineage Upgrade

- Updated `app/models/runs.py`, `app/services/replay_service.py`, `app/services/run_lifecycle_service.py`, and `app/api/replays.py` so replay responses now carry runtime-owned lineage models with triggering actor metadata plus separate source/replay revision context.
- Reused the bounded release-management domain instead of adding new persistence: replay lineage derives source release context from the latest immutable release event affecting the parent revision at the parent run timestamp, and derives replay release context from the latest immutable agent release event at replay time.
- Replaced direct parent-run event mutation in replay handling with append-only runtime events written through `run_lifecycle_service`, emitting `replay_requested` on the parent run and `replay_lineage_bound` on the child run when a replay is dispatched.
- Expanded `tests/api/test_replays.py` with failing-first assertions for triggering actor capture, release-channel/event lineage, and preserving original-vs-current release context after clone-based rollback while keeping child dispatch pinned to the original revision id.
- Verified with `./.venv/bin/python -m pytest tests/api/test_replays.py -q` (`6 passed`; failing-first repro was `2 failed, 4 passed`).

### 2026-04-22 Phase 5 Slice P5.2 Release Management Domain

- Added `app/models/release_management.py`, `app/db/release_management.py`, `app/services/release_management_service.py`, and `app/api/release_management.py` to introduce a bounded release-management surface with immutable `publish`/`rollback` event records plus dedicated org-scoped list/publish/rollback routes.
- Extended `app/db/client.py` and `app/main.py` additively so the in-memory control-plane store now tracks release events per agent and the new router is mounted behind the existing runtime API-key guard.
- Repaired the rollout blockers by making rollback clone the requested historical revision into a fresh published revision instead of reactivating a deprecated row in place, keeping the rollback target recorded on the event while old revision ids remain stable for replay/session pinning.
- Routed legacy `/agents/{agent_id}/revisions/{revision_id}/publish` through the release-management service so publish history is no longer bypassable, and made legacy active-archive fail closed until a matching release-event transition exists.
- Expanded `tests/db/test_release_management_repository.py`, `tests/api/test_release_management.py`, `tests/api/test_agents.py`, and `tests/api/test_replays.py` with failing-first coverage for clone-based rollback semantics, legacy publish event emission, fail-closed active archive, and replay staying pinned to the original revision id across supersede + rollback transitions.
- Verified with `./.venv/bin/python -m pytest tests/db/test_release_management_repository.py tests/api/test_release_management.py tests/api/test_agents.py tests/api/test_replays.py -q` (`24 passed`; failing-first repro was `5 failed, 19 passed`).

### 2026-04-22 Phase 5 Slice P5.1 Revision Lifecycle + Release Channel Metadata

- Updated `app/models/agents.py` so revision state now supports `draft`, `candidate`, `published`, `deprecated`, and `archived`, while keeping rollback/rolled_back semantics intentionally deferred to a later release-event slice.
- Updated `app/db/agents.py` so new revisions persist a `release_channel`, draft revisions can move into `candidate`, publishing a newer revision deprecates the previously active published revision instead of auto-archiving it, deprecated revisions fail closed on republish, archive/clone now recompute lifecycle status from the remaining non-archived revisions, and clone preserves the source release channel.
- Updated `app/services/agent_registry_service.py` to pass through `release_channel`, expose an internal candidate-promotion service seam, and prefer the latest non-archived revision when deriving revision state for read models.
- Expanded `tests/api/test_agents.py` with failing-first coverage for default/custom `release_channel` round-tripping and the richer publish transition where superseded revisions become `deprecated` and cannot be republished.
- Expanded `tests/db/test_agents_repository.py` with failing-first coverage for draft→candidate promotion, deprecated republish rejection, and the lifecycle fallback to `deprecated` when the latest published revision is archived but an older deprecated revision remains.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_agents_repository.py tests/api/test_agents.py -q` (`17 passed`; failing-first repro was `5 failed, 12 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_agents.py -q` (`14 passed`)

### 2026-04-22 Phase 4 Slice P4.5 Mission Control Governance Surface

- Added `MissionControlGovernanceResponse` plus active-revision secrets-health summaries in `app/models/mission_control.py`, keeping the slice read-only and focused on approvals, secrets health, audit, and usage.
- Updated `app/services/mission_control_service.py` with `get_governance()` and an internal secrets-health projection that derives org-scoped status directly from active revision metadata, secret bindings, and stored secrets instead of calling secret read paths that append `secret_accessed` audit events.
- Updated `app/api/mission_control.py` to expose `GET /mission-control/settings/governance` as the single org-scoped governance bundle endpoint.
- Expanded `tests/api/test_mission_control.py` with failing-first coverage proving the new endpoint scopes approvals/audit/usage to the caller org, ignores draft-only secret declarations, and does not introduce governance-read `secret_accessed` audit noise.
- Updated the native Mission Control shell (`apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/App.tsx`, `apps/mission-control/src/pages/SettingsPage.tsx`, `apps/mission-control/src/lib/fixtures.ts`, `apps/mission-control/src/App.test.tsx`) so Settings now reads and renders the governance snapshot with a thin read-only surface while preserving existing asset status.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_mission_control.py -q` (`19 passed`; failing-first repro was `1 failed, 18 deselected` for the new governance test)
  - `npm --prefix apps/mission-control run test -- --run src/App.test.tsx` (`4 passed`)
  - `npm --prefix apps/mission-control run typecheck` (`passed`)

### 2026-04-22 Phase 4 Slice P4.3 Audit Trust, Ordering, and Scrubbing

- Updated `app/api/audit.py` so raw `/audit` now uses trusted actor context on both write and read paths: POST derives `org_id`, `actor_id`, and `actor_type` from actor headers/default context and fails with `422` on conflicting body values, while GET defaults to the caller org and rejects mismatched `org_id` queries with `422`.
- Updated `app/services/audit_service.py` to centralize actor-scoped org resolution, populate server-side default actor metadata when append callers omit it, scrub sensitive audit metadata before persistence/response, and keep read-path scrubbing in place for defense in depth.
- Updated `app/models/audit.py` and `app/db/audit.py` so audit records now own a persisted monotonic `updated_at` field, backfill legacy hydrated rows to `created_at` when the field is absent, and sort newest-first by `(created_at, updated_at)` so equal-timestamp append order survives generic text-table persistence/hydration.
- Expanded `tests/db/test_audit_repository.py` with a failing-first regression that round-trips identical-timestamp audit payloads through persisted `updated_at` ordering and proves the latest append still wins after hydration.
- Expanded `tests/api/test_audit.py` with failing-first coverage for trusted actor/org derivation, org-scoped audit reads, append/read metadata redaction, and `422` rejection for conflicting `org_id`/`actor_id`/`actor_type` body values.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_audit_repository.py tests/api/test_audit.py -q` (`7 passed`; failing-first repro was `1 failed, 6 passed`)

### 2026-04-22 Phase 4 Slice P4.2 Secret Binding Integrity + Read Audit

- Updated `app/db/secrets.py` so `bind_secret()` now fails closed unless the target secret exists, the target agent revision exists, the revision's owning agent belongs to the same org as the secret, and the requested `binding_name` is declared in `revision.compatibility_metadata["requires_secrets"]`; existing `(revision_id, binding_name)` dedupe/rebind behavior remains intact.
- Updated `app/services/secrets_service.py` to keep returning `SecretSummaryRecord` public read models, validate revision existence before listing revision bindings, and emit `secret_accessed` audit events through the existing `audit_service.append_event()` seam for secret-list and revision-binding read paths without logging plaintext values.
- Updated `app/api/secrets.py` to map secret endpoint validation errors consistently: not-found failures return `404`, while fail-closed declared-ref validation returns `422`.
- Expanded `tests/db/test_secrets_repository.py` with failing-first coverage for missing revision, foreign-org revision, undeclared binding-name rejection, and preserved dedupe/rebind behavior.
- Expanded `tests/api/test_secrets.py` with failing-first coverage for redacted public responses, secret read-path audit emission, missing/undeclared/foreign binding rejection, and missing revision validation on `/secrets/revisions/{revision_id}`.
- Updated the affected Mission Control secret-surface regression in `tests/api/test_mission_control.py` so published test agents explicitly declare the secret refs they bind.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_secrets_repository.py tests/api/test_secrets.py -q` (`7 passed`; failing-first repro was `6 failed, 1 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_mission_control.py -q -k secret_audit_and_usage_endpoints_scope_to_actor_org` (`1 passed, 17 deselected`)

### 2026-04-22 Phase 4 Slice P4.1d RBAC Runtime Duplicate-Role Source Collapse

- Updated `app/db/rbac.py` so `resolve_tool_mode()` no longer emits one source per assigned role row for canonical-ish legacy duplicates; it now groups assigned role grants by logical canonical name before source emission.
- Kept the collapse bounded to canonical-ish names only: duplicate grants for the same logical canonical role are conservatively combined with the existing mode ordering, while unknown noncanonical legacy roles still retain per-row behavior and safe ordering.
- Emitted a stable canonical runtime source label like `role:org_admin` for grouped canonical-ish duplicates so effective-permission traces no longer leak raw legacy names such as `role: Org_Admin `.
- Added a failing-first regression in `tests/db/test_rbac_repository.py` that seeds two semantically duplicate legacy `org_admin` rows, assigns both, grants conflicting modes, and proves effective resolution returns one conservatively combined logical source.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py -q` (`6 passed` after fix; failing-first repro was `1 failed, 5 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py tests/api/test_rbac.py -q` (`10 passed`)

### 2026-04-22 Phase 4 Slice P4.1c RBAC Canonical-Ish Legacy Duplicate Collapse

- Updated `app/db/rbac.py` so canonical-name lookup now scans all semantically matching stored rows before trusting `role_keys`, deterministically chooses the oldest `(created_at, id)` survivor, and repairs the canonical key to that survivor.
- Added read-path presentation/collapse helpers so `list_roles()` returns at most one logical role per canonical normalized name while still leaving unknown legacy role names untouched; canonical-ish survivors are presented as canonical names like `org_admin` even if the stored row is `" Org_Admin "`.
- Kept strict canonical validation for new input and the existing lazy canonicalization-on-touch behavior in `create_role()`, so a canonical create now updates the deterministic survivor instead of whichever duplicate `role_keys` happened to reference.
- Expanded `tests/db/test_rbac_repository.py` with a failing-first regression that seeds two semantically duplicate legacy rows directly into the store, including a stale canonical key pointing at the newer duplicate, and proves lookup/list/create collapse them to one logical `org_admin` role.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py -q` (`5 passed` after fix; failing-first repro was `1 failed, 4 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py tests/api/test_rbac.py -q` (`9 passed`)

### 2026-04-22 Phase 4 Slice P4.1b RBAC Legacy Role Backward-Compat Hardening

- Added `normalize_stored_org_role_name()` in `app/models/rbac.py` so stored/read-path normalization trims and lowercases without strict enum rejection, while `normalize_org_role_name()` still enforces canonical-only validation for new requested role names.
- Updated `org_role_sort_key()` to order canonical names first but fall back safely for unknown legacy stored names instead of raising during role listing, assignment listing, or effective-permission resolution.
- Updated `app/db/rbac.py` to scan existing stored roles by loose normalized name when canonical lookup misses, repair the canonical role-key index on match, and lazily canonicalize a matched legacy role name when `create_role()` touches it so canonical input dedupes instead of creating a semantic duplicate.
- Added focused regression coverage in `tests/db/test_rbac_repository.py` proving legacy unknown stored names no longer crash read/effective paths and canonical input dedupes against legacy canonical-ish stored names like `" Org_Admin "`.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py -q` (`5 passed` after fix; failing-first repro was `2 failed, 3 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py tests/api/test_rbac.py -q` (`9 passed`)

### 2026-04-22 Phase 3 Slice P3.5 Hermes Tool Skill-Surface Gating

- Updated `app/services/hermes_tools_service.py` so `list_tools(agent_revision_id=...)` resolves the revision's bound skills, intersects their `required_tools` with `POLICY_BY_COMMAND`, and only narrows the exposed Hermes command surface when that intersection is non-empty.
- Kept backward compatibility open by falling back to the full Hermes command surface when a revision has no skills or its resolved skills only declare empty/non-command `required_tools` such as legacy metadata like `lookup_title`.
- Added invoke-time gating in `HermesToolsService.invoke_tool()` so command-backed tools outside the resolved skill surface raise `ToolPermissionError` and therefore stay API-level `403`s without replacing existing permission/RBAC/capability checks for still-visible tools.
- Added focused API regressions in `tests/api/test_hermes_tools.py` covering surface intersection, non-command fallback, and out-of-surface invocation rejection.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py -q` (`12 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_permissions.py tests/api/test_rbac.py tests/services/test_hermes_tools_service.py -q` (`19 passed`)

### 2026-04-22 Phase 3 Slice P3.4c Agent-Backed Replay Dispatch Continuity

- Added `HostAdapterDispatchesRepository.get_by_run_id()` so replay resolution can reuse the existing in-memory/hydrated host-adapter dispatch seam to recover the parent run's `agent_revision_id` without adding new persistence wiring.
- Updated `app/services/replay_service.py` so safe-autonomous replays derive `agent_revision_id` from the parent run's adapter dispatch, create child runs through `run_service.create_run(..., agent_revision_id=...)`, and only append replay events after successful child-run or approval creation to avoid partial replay state on failure.
- Updated `app/api/replays.py` to translate replay-time dispatchability failures into clean `422` responses instead of surfacing a `500`.
- Added API regression coverage in `tests/api/test_replays.py` proving agent-backed replays create a second adapter dispatch correlated to the child run id, non-agent replay behavior stays intact, and archived revisions fail cleanly without bogus child runs or dispatches.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_replays.py -q` (`4 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_replays.py tests/api/test_hermes_tools.py tests/api/test_commands.py -q` (`19 passed`)

### 2026-04-22 Phase 3 Slice P3.4b Agent-Backed Command Idempotency Restore

- Added `CommandsRepository.get_by_idempotency_key()` for both in-memory and existing Supabase-backed command lookups without changing persistence ownership or schema wiring.
- Updated `CommandService.create_command()` so agent-backed safe-autonomous retries short-circuit to the original persisted command/run before dispatchability validation, while brand-new invalid/draft/archived/disabled requests still fail closed before any queue records are created.
- Added QC regression coverage in `tests/api/test_hermes_tools.py` and `tests/api/test_commands.py` proving archived-revision retries with the same idempotency key return the original deduped command/run and do not create a second adapter dispatch.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_commands.py tests/services/test_agent_execution_service.py tests/services/test_hermes_tools_service.py -q` (`23 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_commands_repository.py tests/db/test_control_plane_supabase_adapters.py -q` (`8 passed`)

### 2026-04-22 Phase 3 Slice P3.4a Hermes Tool Agent-Dispatch Runtime Path

- Extended `app/models/commands.py`, `app/services/hermes_tools_service.py`, `app/services/command_service.py`, and `app/services/run_service.py` so Hermes tool invocations now carry optional `agent_revision_id` into the safe-autonomous runtime path.
- Safe-autonomous agent-backed execution now pre-validates dispatchability through `agent_execution_service` before command/run persistence, rejecting missing, draft, archived, and disabled-adapter revisions without leaving queued command/run leftovers; non-agent safe-autonomous behavior and approval-required behavior remain unchanged.
- `agent_execution_service` still dispatches published revisions through the host-adapter seam, keeps `run.id` as the adapter correlation/external reference, and now treats disabled adapters as non-dispatchable instead of returning a queued-looking no-op.
- Added focused API/service coverage in `tests/api/test_hermes_tools.py`, `tests/api/test_commands.py`, and `tests/services/test_agent_execution_service.py` for the fail-closed QC repros while preserving the existing happy-path adapter dispatch and non-agent no-dispatch behavior.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_commands.py tests/services/test_agent_execution_service.py -q` (`18 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_commands.py tests/services/test_agent_execution_service.py tests/api/test_agents.py -q` (`31 passed`)

### 2026-04-22 Phase 3 Slice P3.3 Host-Adapter Contract Hardening

- Hardened `app/models/host_adapters.py`, `app/host_adapters/base.py`, `app/host_adapters/registry.py`, `app/host_adapters/trigger_dev.py`, `app/host_adapters/codex.py`, and `app/host_adapters/anthropic.py` so the adapter seam now explicitly models dispatch, status correlation, artifact reporting, cancellation, and disabled behavior.
- Added adapter read-model metadata for later runtime/UI work, including `display_name`, `adapter_details_label`, `capabilities`, and `disabled_reason`, while keeping Trigger-specific information framed as adapter details rather than product identity.
- Kept Codex and Anthropic registered but disabled, unified their disabled/no-op behavior through the shared base contract, and added duplicate-kind protection in the host registry.
- Expanded focused coverage in `tests/host_adapters/test_host_registry.py`, `tests/host_adapters/test_trigger_dev_adapter.py`, and `tests/host_adapters/test_disabled_host_adapters.py` for adapter descriptions, correlation records, artifact reporting, cancellation handling, and disabled-adapter contract behavior.
- Verified with:
  - `./.venv/bin/python -m pytest tests/host_adapters/test_host_registry.py tests/host_adapters/test_trigger_dev_adapter.py tests/host_adapters/test_disabled_host_adapters.py -q` (`8 passed`)
  - `./.venv/bin/python -m pytest -q` (`392 passed`)

### 2026-04-22 Phase 3 Slice P3.2 Skill Registry Contract Hardening

- Hardened `app/models/skills.py`, `app/db/skills.py`, `app/services/skill_registry_service.py`, and `app/api/skills.py` so skills now carry explicit `permission_requirements` alongside normalized `name`, `description`, `required_tools`, and input/output contract metadata.
- Added defensive-copy behavior in the skills repository so nested contract metadata and tool/permission lists cannot be mutated through returned records.
- Kept agent revisions bound to `skill_ids` only and tightened missing-skill error reporting to return a clean deduplicated `Unknown skill ids: ...` failure.
- Added focused repository/API coverage in `tests/db/test_skills_repository.py` and `tests/api/test_skills.py`, then verified `tests/api/test_agents.py` still passes for skill-id binding behavior.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_skills_repository.py tests/api/test_skills.py -q` (`6 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_agents.py -q` (`13 passed`)
  - `./.venv/bin/python -m pytest -q` (`388 passed`)

### 2026-04-22 Phase 2 Lane C Org Directory Tenant Isolation

- Hardened `app/api/organizations.py`, `app/api/memberships.py`, `app/services/organization_service.py`, and `app/services/access_service.py` so org directory reads/writes now resolve against the header-derived actor org instead of global memory state.
- `GET /organizations` now only returns the caller's org record, foreign org detail reads return `404`, and mismatched org writes fail with `422`.
- `GET /memberships` now scopes to the caller org by default, rejects cross-org `org_id` query overrides with `422`, and blocks cross-org membership detail/write access cleanly.
- Added focused API coverage in `tests/api/test_organizations.py` and `tests/api/test_memberships.py`, including `X-Ares-Org-Id` actor-header regressions for the QC repros.
- Verified with targeted coverage only: `uv run pytest tests/api/test_organizations.py tests/api/test_memberships.py -q` (`5 passed`).

### 2026-04-22 Phase 2 Lane B Org-Scoped API Hardening

- Hardened `app/api/permissions.py`, `app/api/rbac.py`, `app/services/permission_service.py`, and `app/services/rbac_service.py` so the existing header-based actor org now gates permission/RBAC reads and writes.
- Tightened cross-org failure behavior for permission/RBAC paths and `POST /sessions` without touching Supabase wiring, migrations, or Mission Control surfaces.
- Added tenant-isolation API coverage for agents, sessions, permissions, and RBAC proving the same `business_id` / `environment` can exist in multiple orgs without leakage.
- Verified the lane with targeted pytest coverage only: `tests/api/test_permissions.py tests/api/test_rbac.py tests/api/test_agents.py tests/api/test_sessions.py`.

### 2026-04-22 In-Memory Org Directory Slice

- Added first-class in-memory `organizations` and `memberships` models, repositories, and services without touching Supabase wiring.
- Seeded the default internal org plus an internal runtime membership inside the in-memory control-plane store so existing `org_internal` defaults resolve cleanly.
- Mounted authenticated `organizations` and `memberships` API routes and added focused repository/API coverage for the new slice.

### 2026-04-21 Mission Control + Enterprise Backlog Branch Reset

- Created `feature/mission-control-enterprise-backlog` from current `main` as the new combined-scope branch for Mission Control orchestration + enterprise platform backlog work.
- Added `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md` as the canonical execution plan for that branch.
- Corrected the mistaken deprecation on `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`; it is now a live source plan again.
- Repointed `TODO.md`, `CONTEXT.md`, and `memory.md` for the combined branch so the older loose-ends handoff no longer drives current scope there.

### 2026-04-20 Shared Control-Plane Runtime Supabase Pass

- Added `supabase/migrations/202604200001_shared_control_plane_runtime.sql` for the remaining text-id control-plane runtime entities:
  - agents / revisions
  - sessions / memory summaries
  - turns / turn events
  - permissions / RBAC / secrets
  - audit / usage / outcomes
  - agent assets / Mission Control threads / skills / host adapter dispatches
- Added `app/db/control_plane_store_supabase.py` and upgraded `SupabaseControlPlaneClient.transaction()` to hydrate and flush the remaining control-plane store sections through Supabase instead of raising `NotImplementedError`
- This preserves the existing repository/service contracts for the managed-agent and Mission Control surfaces while making `control_plane_backend=supabase` actually usable across the broader runtime
- Added focused persistence coverage in `tests/db/test_supabase_control_plane_client.py`
- Verified repo state after the pass with:
  - `244 passed` backend tests via `./.venv/bin/python -m pytest -q`
  - local Supabase `db reset --local` passing on April 20, 2026

### 2026-04-20 Control-Plane Supabase Wiring Pass

- Added a shared `app/db/control_plane_supabase.py` adapter layer for the core control-plane tables already present in `202604130001_hermes_control_plane_core.sql`
- Wired explicit Supabase-backed repository paths for:
  - `commands`
  - `approvals`
  - `runs`
  - `events`
  - `artifacts`
- Fixed the persistence bug where memory-mode object mutation masked missing writes in Supabase mode:
  - command ingestion now persists approval/run status transitions explicitly
  - run lifecycle callbacks now persist run status updates before recording events
  - run creation now records the initial `run_created` event through the repository seam instead of only mutating the in-memory object
- Added focused adapter coverage in `tests/db/test_control_plane_supabase_adapters.py`
- Verified repo state after the pass with:
  - `242 passed` backend tests via `./.venv/bin/python -m pytest -q`
  - Mission Control frontend `vitest` passing locally

### 2026-04-20 Loose-Ends QC Blocker Fixes

- Fixed inbound SMS stop/pause mutation scoping:
  - `InboundSmsService` now passes the resolved lead identity into sequence mutation calls
  - `_SequenceReplyAdapter` now resolves active enrollments with scoped `business_id + environment + contact_id` when available instead of relying on global phone lookup
  - ambiguous/unresolved replies still create manual-review tasks and receipts, but do not mutate sequence state
- Fixed provider-thread resolution safety:
  - `_resolve_inbound_lead()` now uses provider-thread matching only when tenant metadata is present
  - unscoped provider-thread fallback is skipped, so duplicate thread IDs without tenant metadata fall through to manual review / phone resolution only
  - in-memory `ConversationsRepository` no longer keys rows by `provider_thread_id`, so duplicate external thread IDs can coexist across tenants
- Added regression coverage for:
  - shared-phone stop replies only stopping the resolved tenant's sequence
  - duplicate provider-thread IDs resolving correctly with tenant metadata
  - unscoped provider-thread metadata skipping the global thread matcher
- Verified with `uv run pytest tests/services/test_inbound_sms_service.py tests/api/test_marketing_webhooks.py -q` (`16 passed`)

### 2026-04-20 Ralph Story-06 Verification

- Completed branch-level rollout gates for the loose-ends MVP in memory mode:
  - backend: `uv run pytest -q` (`257 passed`)
  - Mission Control: `typecheck`, `vitest --run` (`14 passed`), `build`
  - Trigger: `npm --prefix trigger run typecheck`
- Executed fixture-backed smoke flows:
  - lease-option submit -> booking webhook -> sequence guard (`booked` -> `stopped`)
  - probate intake -> outbound enqueue -> Instantly webhook ingest
- Verified runtime startup/health with Supabase env vars unset and all backends forced to memory (`MEMORY_STARTUP=PASS`).

### 2026-04-20 Ralph Story-05 Verification

- Added RED/GREEN coverage for thin opportunity seam progression:
  - direct opportunity forward-stage transition (`qualified_opportunity -> offer_path_selected`)
  - Mission Control operator task completion path that advances lease-option opportunities when follow-up outcome marks the contact ready
- Added Mission Control service opportunity sync from thread context for lease-option contacts:
  - uses booking status and follow-up outcome to decide whether to open/advance opportunity
  - resolves marketing contact from thread context `lead_id` (contact id) or phone fallback
  - advances to `offer_path_selected` when operator marks outcome ready
- Verified story-05 gates with:
  - `uv run pytest -q` (`257 passed`)
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run test -- --run` (`14 passed`)
  - `npm --prefix apps/mission-control run build`

### 2026-04-20 Ralph Story-04 Verification

- Added explicit lane-separated Mission Control dashboard read models:
  - `outbound_probate_summary`
  - `inbound_lease_option_summary`
  - `opportunity_pipeline_summary` (lane+stage summaries)
- Kept additive compatibility by retaining existing dashboard totals while exposing lane-specific aggregates for Mission Control workspace badges/context.
- Updated Mission Control frontend mapping and fixtures so opportunity stages preserve `source_lane` instead of flattening by stage.
- Updated Pipeline board rendering so stage cards remain lane-labeled and do not collapse probate vs lease-option rows.
- Verified story-04 gates with:
  - `uv run pytest -q` (`255 passed`)
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run test -- --run` (`14 passed`)
  - `npm --prefix apps/mission-control run build`

### 2026-04-20 Ralph Story-03 Verification

- Hardened the lease-option inbound lane in memory mode with:
  - sequence guard state derived from latest enrollment status (active/paused/completed/stopped) for pending leads
  - booking-confirmation timeline logging into `messages` for SMS and email channels when configured
  - inbound SMS resolution order: provider thread metadata first, then tenant-scoped phone matching
  - explicit manual-review task creation when inbound SMS lead resolution is ambiguous or unmatched
- Added focused regression coverage for:
  - paused sequence guard behavior
  - booking confirmation message timeline writes
  - thread-first inbound SMS resolution
  - ambiguity task creation for duplicate phone matches
- Verified lease-option and full backend gates with:
  - `uv run pytest tests/services/test_booking_service.py tests/api/test_marketing_webhooks.py -q` (`14 passed`)
  - `uv run pytest tests/api/test_marketing_leads.py tests/api/test_marketing_webhooks.py tests/api/test_marketing_runtime.py tests/api/test_marketing_sequence.py tests/domains/marketing/test_marketing_flow.py tests/services/test_booking_service.py -q` (`33 passed`)
  - `uv run pytest -q` (`255 passed`)

### 2026-04-20 Ralph Story-02 Verification

- Verified the probate outbound write path acceptance gate in memory-backed mode for:
  - `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
- Confirmed replay-safe webhook handling and receipt-first processing remain covered by existing API/service tests
- Verified branch health with `uv run pytest -q` (`251 passed`) and `npm --prefix trigger run typecheck`
- Updated Ralph board state so `story-02-build-probate-outbound-write-path` is marked `done` / `passes: true`

### 2026-04-20 Loose-Ends Scope Repoint

- Repointed the loose-ends branch back to the probate outbound + lease-option inbound MVP implementation plan
- Kept the 2026-04-15 enterprise-agent-platform plan in the repo but marked it deprecated
- Restored `TODO.md`, `CONTEXT.md`, and `memory.md` to the lead-machine / two-lane MVP scope

### 2026-04-21 Phase5 Guarded Autonomous Operator Wiring

- Added `app/services/ares_autonomous_operator_service.py` to wire the guarded operator loop across:
  - versioned Ares agent registry initialization (`ares_guarded_operator` revision `v1`)
  - playbook execution for approved objectives
  - deterministic high-risk policy gates (outreach/contract/spending/market-expansion require approval)
  - durable memory journaling and evaluation-loop metric recording
- Added `POST /ares/operator/run` in `app/api/ares.py` to execute approved objective runs and persist latest operator snapshot per `(business_id, environment)` in control-plane scope state.
- Extended Mission Control autonomy visibility contracts and service wiring to surface `autonomous_operator` summary with decisions, exceptions, policy checks, audit log, adaptation summary, and escalation state.
- Updated `app/main.py` startup wiring to initialize the guarded autonomous operator surface on app creation.
- Extended tests:
  - `tests/api/test_mission_control_phase3.py` with guarded operator visibility coverage
  - `tests/test_package_layout.py` with `/ares/operator/run` route registration coverage
- Verified with `uv run pytest tests/api/test_mission_control_phase3.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase4 Execution + Mission Control Workflow Integration

- Updated `POST /ares/execution/run` in `app/api/ares.py` to integrate the workflow playbook runner on each bounded execution run.
- Added explicit high-risk policy checks for send/contract/disposition actions on each run, with hard-approval-required outcomes surfaced in runtime output and execution snapshots.
- Added per-scope drift detection against the previous execution snapshot and persisted drift status/reason into execution review data.
- Added workflow evaluation output (`workflow_id`, exception count, surfaced exceptions, suggested next action) into execution review snapshots.
- Extended Mission Control execution review contracts in `app/models/mission_control.py` to include:
  - high-risk policy checks
  - workflow eval summary
  - drift detection summary
  - major decisions and major failures
- Extended `tests/api/test_mission_control_phase3.py` to cover:
  - hard-approval-required high-risk checks in autonomy visibility
  - workflow eval + major decision/failure surfacing
  - drift detection visibility across consecutive execution runs in the same scope
- Verified with `uv run pytest tests/api/test_mission_control_phase3.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase4 Playbook, State, and Eval Services

- Added `app/services/ares_playbook_service.py` as a deterministic workflow runner that can:
  - choose county/market slice
  - pull probate/tax signals via county adapters
  - enrich and score leads through existing matching logic
  - generate outreach drafts and follow-up approval tasks
  - monitor response events and set next-best-action
- Added `app/services/ares_state_service.py` for workflow state memory with per-step status/history plus retry and fallback handling.
- Added `app/services/ares_eval_service.py` to capture and surface workflow exceptions in explicit eval reports (no silent drops).
- Added service coverage:
  - `tests/services/test_ares_playbook_service.py`
  - `tests/services/test_ares_state_service.py`
  - `tests/services/test_ares_eval_service.py`
- Verified with `uv run pytest tests/services/test_ares_playbook_service.py tests/services/test_ares_state_service.py tests/services/test_ares_eval_service.py -q`.

### 2026-04-21 Phase4 Workflow Models and Contracts

- Added `app/domains/ares_workflows/models.py` with workflow contract models for:
  - county or market workflow scope (`AresWorkflowScope`)
  - per-step workflow state (`AresWorkflowStepState` + `AresWorkflowStepStatus`)
  - next-best-action and append-only workflow history (`AresWorkflowState` + `record_history`)
- Added workflow domain exports in `app/domains/ares_workflows/__init__.py`.
- Added workflow model contract tests in `tests/domains/ares_workflows/test_workflow_models.py`.
- Extended package export checks in `tests/test_package_layout.py` for `app.domains.ares_workflows`.
- Verified with `uv run pytest tests/domains/ares_workflows/test_workflow_models.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase3 Execution API + Mission Control Wiring

- Added `POST /ares/execution/run` in `app/api/ares.py` to launch bounded execution runs through `AresExecutionService` with explicit run scope (`market`, up to two counties, budget/retry/allowlist) and deterministic county payload adapters.
- Persisted the latest bounded execution snapshot per `(business_id, environment)` in the in-memory store as `ares_execution_runs_by_scope`.
- Extended Mission Control autonomy visibility to surface `execution_review` with bounded run state (`completed|completed_with_failures|interrupted`) plus execution result summary (lead/failure counts and ranked lead tier output).
- Updated phase-3 API tests in:
  - `tests/api/test_ares_runtime.py`
  - `tests/api/test_mission_control_phase3.py`
  - `tests/test_package_layout.py` (route registration for `/ares/execution/run`)
- Verified with `uv run pytest tests/api/test_ares_runtime.py tests/api/test_mission_control_phase3.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase3 Bounded Execution Service

- Expanded `app/services/ares_execution_service.py` from guardrails-only authorization into a bounded execution pipeline that:
  - fetches county probate/tax payloads via deterministic county fetch adapters
  - normalizes record fields and dedupes overlap records per county/lane/address
  - enriches probate records from matching tax records when data is available
  - runs overlay matching with ranked lead outputs
  - generates lead briefs, outreach drafts, task suggestions, and follow-up work queue items
  - surfaces county fetch failures as explicit recoverable run output failures and supports run interruption via kill-switch
- Reworked `tests/services/test_ares_execution_service.py` to validate the bounded pipeline behavior plus existing execution guardrail enforcement.
- Verified with `uv run pytest tests/services/test_ares_execution_service.py -q`.

### 2026-04-21 Phase3 Execution Contracts and Guardrails

- Added bounded execution contract models in `app/domains/ares/models.py`:
  - `AresExecutionRunSpec` (narrow county-scoped run, action budget, retry limit, approved tool allowlist)
  - `AresExecutionActionSpec` (typed action authorization request contract)
  - `AresExecutionDecision` and `AresExecutionGuardrailResult` (deterministic guardrail decisions)
- Added `app/services/ares_execution_service.py` with guardrail enforcement for:
  - tool allowlist
  - retry-limit checks
  - run-level action budget exhaustion checks
  - policy-service delegated risky-call approvals
  - audit trail and kill-switch deny behavior
- Added `tests/services/test_ares_execution_service.py` for bounded-run model and guardrail contract coverage.
- Verified phase-3 guardrails with:
  - `uv run pytest tests/services/test_ares_policy_service.py tests/services/test_ares_execution_service.py -q`

### 2026-04-21 Phase2 Planner API + Mission Control Review Surface

- Added `POST /ares/plans` in `app/api/ares.py` to expose deterministic planner output and explanation for operator review.
- Persisted latest planner snapshot per `(business_id, environment)` in the in-memory control-plane store (`ares_plans_by_scope`).
- Extended Mission Control autonomy visibility with `planner_review` so the latest planner goal/explanation/plan is visible in one response.
- Added `tests/api/test_ares_plans.py` for planner request/response contract and Mission Control planner surfacing.
- Updated package-layout route assertions for `/ares/plans` and verified with:
  - `uv run pytest tests/api/test_ares_plans.py tests/test_package_layout.py -q`

### 2026-04-21 Phase2 Planner Service Logic

- Added `app/services/ares_planner_service.py` with deterministic planning logic to:
  - parse goal text into county slices and source lanes
  - choose planner checks for county scope, overlay match quality, and approval gate enforcement
  - generate concrete sequential planner steps with explicit side-effecting action approval requirements
  - produce operator-facing plan explanation text (`explain_plan`)
- Extended `AresPlannerPlan` in `app/domains/ares/models.py` with optional `counties` to capture county-slice planning scope
- Added `tests/services/test_ares_planner_service.py` covering:
  - probate+tax county-slice goal acceptance
  - lane/check selection
  - concrete steps plus side-effecting approval gate
  - operator explanation output
- Verified with `uv run pytest tests/services/test_ares_planner_service.py -q`

### 2026-04-21 Phase2 Planner Models and Contracts

- Added planner-domain contract models in `app/domains/ares/models.py`:
  - `AresPlannerCheck` for explicit checks
  - `AresPlannerStep` for step-by-step plans scoped to a source lane
  - `AresPlannerPlan` for goal, source lanes, checks, steps, and rationale
  - `AresPlannerActionType` with `read_only` and `side_effecting`
- Enforced side-effect approval in model validation: side-effecting steps must set `requires_approval=True`
- Exported planner models through `app/domains/ares/__init__.py` and package layout assertions
- Added planner model coverage in `tests/domains/ares_planning/test_planner_models.py`
- Verified with `uv run pytest tests/domains/ares_planning/test_planner_models.py tests/test_package_layout.py -q`

### 2026-04-21 Shared Mission Control Autonomy Visibility

- Added operator-facing autonomy visibility read model:
  - `GET /mission-control/autonomy-visibility`
  - `MissionControlAutonomyVisibilityResponse` with `current_phase`, `active_run`, pending approvals, failed steps, lead quality, confidence, and next action
- Added Mission Control phase-3 API coverage in `tests/api/test_mission_control_phase3.py` for the new autonomy visibility surface
- Verified with `uv run pytest tests/api/test_mission_control_phase3.py -q`

### 2026-04-21 Shared Evaluation Loop Foundation

- Added `app/services/ares_eval_loop_service.py` with durable JSON-backed evaluation-loop state and inspectable run entries
- Added typed evaluation primitives:
  - `AresEvalSample` for lead/response/conversion counts plus false positives, duplicate work, and operator corrections
  - `AresEvalMetrics` for lead quality, response quality, conversion quality, false-positive rate, duplicate-work rate, and operator-correction rate
  - `AresEvalResult` and `AresEvalLoopState` for stable persisted evaluation records
- Added `tests/services/test_ares_eval_loop_service.py` covering required metrics calculation, durable save/reload behavior, and stable metrics contract keys/zero-denominator behavior
- Verified with `uv run pytest tests/services/test_ares_eval_loop_service.py -q`

### 2026-04-21 Ares Shared Agent Registry Foundation

- Added versioned Ares agent registry primitives:
  - `app/domains/ares/agent_registry.py` with `AresAgentRevisionSpec` and `AresVersionedAgentRecord`
  - fields lock `name`, `purpose`, `revisions`, `allowed_tools`, `risk_policy`, `output_contract`, and `active_revision`
- Added `app/services/ares_agent_registry_service.py` to register revisions, track active revision, and export/import model snapshots
- Added round-trip coverage:
  - `tests/domains/ares/test_agent_registry_models.py`
  - `tests/services/test_ares_agent_registry_service.py`

### 2026-04-21 Ares Master Scope Docs + Memory Handoff

- Updated repo-facing handoff docs to point at the merged phased implementation plan as the execution source of truth:
  - `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md`
- Kept the master-scope PRD as the overnight loop handoff artifact:
  - `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-prd.json`
- Restated Phase 1 hard guardrails in docs/memory surfaces:
  - counties remain Harris, Tarrant, Montgomery, Dallas, Travis
  - probate is primary and tax delinquency is overlay
  - outreach drafts remain pending human approval before send

### 2026-04-21 Ares Phase1 API Route

- Added `app/api/ares.py` with `POST /ares/run` to execute the phase-1 Ares runtime path:
  - county-filtered probate/tax intake
  - probate-first ranking with tax overlay via `AresMatchingService`
  - optional lead briefs and outreach drafts via `AresCopyService`
- Wired the new route in `app/main.py` so it is mounted in the protected FastAPI app
- Added `tests/api/test_ares_runtime.py` and updated package-layout coverage for route registration
- Verified with `uv run pytest tests/api/test_ares_runtime.py tests/test_package_layout.py -q`

### 2026-04-21 Ares Phase1 Matching Overlay Tiering

- Added `app/services/ares_service.py` with `AresMatchingService` and deterministic tiering:
  - probate lane is primary
  - verified tax delinquency is applied as an overlay on probate records by county + normalized property address
  - probate+verified-tax overlaps rank highest over probate-only
  - tax-only output is allowed only for estate-of records and only when no probate records are present
- Added `tests/services/test_ares_service.py` covering probate-first behavior, overlay matching, highest-rank overlap, county-aware matching, and estate-only tax-only constraints
- Verified with `uv run pytest tests/services/test_ares_service.py -q`

### 2026-04-16 Live Supabase Smoke + Adapter Hardening

- Repaired remote Supabase migration history on project `awmsrjeawcxndfnggoxw` and applied:
  - `202604160001_lead_machine_runtime.sql`
  - `202604160002_runtime_opportunities.sql`
- Corrected the live lease-option booking schema to allow `booked` events and verified the lane against remote Supabase:
  - `POST /marketing/leads` -> `201`
  - `POST /marketing/internal/non-booker-check` -> `200`
  - `POST /marketing/webhooks/calcom` -> `200`
  - remote evidence in `contacts`, `booking_events`, `sequence_enrollments`, and `provider_webhooks`
- Verified the probate outbound lane against remote Supabase with a stubbed Instantly transport:
  - `POST /lead-machine/probate/intake` -> `201`
  - `POST /lead-machine/outbound/enqueue` -> `200`
  - `POST /lead-machine/webhooks/instantly` -> `200`
  - remote evidence in `probate_leads`, `leads`, `automation_runs`, `campaign_memberships`, `provider_webhooks`, `lead_events`, `suppressions`, and `opportunities`
- Fixed several Supabase adapter seams uncovered by the live smoke pass:
  - lead-machine migration composite-tenant uniqueness ordering
  - lease-option booking event constraint mismatch (`booked` vs `created`)
  - Supabase rehydration for `probate_leads`, `leads`, `campaign_memberships`, `provider_webhooks`, `lead_events`, and `suppressions`
  - `automation_runs` Supabase insert excluding runtime-only `deduped`
  - campaign active-tenant guard accepting slug requests for numeric Supabase-backed campaigns
  - webhook lead resolution preferring direct email matches so replies attach to the routed probate lead
- Verified repo state after the fixes with `177 passed` backend tests via `./.venv/bin/python -m pytest -q`

### 2026-04-16 MVP Runtime Execution Pass

- Finished the probate outbound write path with:
  - typed `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
- Added `ProbateLeadsRepository` plus canonical `probate_leads` persistence in the intake flow
- Extended probate records to preserve `tax_delinquent`, `estate_of`, and `pain_stack`
- Tightened lead-machine API validation so malformed intake rows and malformed webhook payloads fail with `422` instead of leaking through as `500` / false-positive `200`
- Added the thin opportunity seam in live runtime paths:
  - probate positive reply / interested events create or update probate opportunities
  - first-time booked lease-option contacts create or update lease-option opportunities
- Fixed opportunity identity so records dedupe by `source_lane + identity`, preventing probate and lease-option rows from collapsing together
- Added additive Mission Control surfaces:
  - backend `GET /mission-control/lead-machine`
  - frontend workspaces for `Lead Machine`, `Marketing`, and `Pipeline`
- Verified the repo state with:
  - `168 passed` backend tests via `./.venv/bin/python -m pytest -q`
  - Mission Control `typecheck`, `vitest --run`, and `vite build`
  - Trigger `typecheck`

### 2026-04-16 Mission Control Lane Separation Backend Acceptance

- Added backend Mission Control coverage proving the operator dashboard keeps lease-option marketing counts, additive probate lead-machine counts, and persisted opportunity pipeline summaries separate
- Added an additive `lead_machine_summary` dashboard read model for probate outbound counts without changing the existing marketing inbox/tasks surfaces
- Tightened opportunity stage summaries so they are grouped by both `source_lane` and `stage`, preventing probate and lease-option pipeline rows from collapsing together

### 2026-04-16 Opportunity Creation Wiring Pass

- Wired `OpportunityService` into the live probate webhook path so positive reply and interested events create or update a probate opportunity record
- Wired `OpportunityService` into the live lease-option booking path so first-time booked contacts create or update a lease-option inbound opportunity record
- Added focused service tests covering the probate opportunity trigger and the lease-option booked-contact opportunity trigger

### 2026-04-16 Combined MVP Implementation Plan

- Added `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
- Locked tonight's MVP as a two-lane cut:
  - probate outbound via Instantly cold email
  - lease-option inbound via the existing marketing flow
- Decided to reuse the existing lease-option marketing slice in this branch and bring the newer probate / lead-machine slice forward from `origin/main`
- Decided to wire Supabase as the canonical backend for both live MVP lanes instead of deferring live persistence again
- Chose a shared-runtime split:
  - lease-option keeps its existing marketing objects
  - probate gets lane-specific lead-machine tables
  - both lanes share provider webhook receipts, tasks, Mission Control, and a thin `opportunities` seam

### 2026-04-16 Real Estate Runtime Thesis

- Added `docs/superpowers/specs/2026-04-16-ares-real-estate-runtime-thesis-design.md`
- Locked the product direction: Ares is the reusable runtime, not the main agent
- Chose the long-term domain map: data gathering, prospecting, acquisitions, transaction coordination, title, and dispo
- Chose the architecture split:
  - source lanes describe where an opportunity came from
  - strategy lanes describe how the opportunity may be solved or monetized
  - operational stages describe where the record is in the business process
- Locked the current MVP shape:
  - source lane = probate
  - outbound method = cold email
  - downstream skeleton = thin contract-to-close placeholders for title, TC, and dispo
- Confirmed that tax distress and estate signals should become composite pain-stack inputs, especially `estate_of + tax_delinquent`

### 2026-04-14 Lease-Option Marketing Wiring Pass

- Replaced the landing-page `n8n` handoff with Hermes lead-ingress payloads while keeping the old `n8n` helper type-compatible for legacy tests
- Wired `MarketingLeadService` to configured `TextGrid`, `Resend`, `Cal.com` booking URLs, and Trigger HTTP scheduling instead of the earlier no-op defaults
- Wired booking confirmations, manual-call task persistence, and sequence-step outbound dispatch onto the current in-memory marketing repositories
- Added exact-config support for local env names already present on Martin's machine, including `Cal_API_key` and Trigger settings
- Added webhook-signature enforcement seams for `Cal.com` and `TextGrid` using request details from the FastAPI routes
- Verified current repo state with `95` backend tests passing, Mission Control tests/build passing, Trigger typecheck passing, and landing-page tests/build passing
- Added a marketing-only Supabase adapter layer and verified a live smoke insert into remote `public.contacts` for `limitless/dev`
- Applied the core and lease-option marketing migrations to Supabase project `awmsrjeawcxndfnggoxw` and seeded `public.businesses` with `limitless/dev`
- Kept the repo honest about the remaining MVP risks: inbound SMS matching is still phone-only and sequence guard state is still derived too simplistically for a multi-tenant or more advanced sequence rollout

### 2026-04-14 Lease-Option Marketing MVP Design

- Added `docs/superpowers/specs/2026-04-14-lease-option-marketing-mvp-design.md` as the live marketing MVP design
- Locked the first live scope to lease-option sellers with `45+ DOM` messaging
- Chose `Cal.com` for booking, `TextGrid` for SMS, and `Resend` for transactional email
- Chose the lead-state rule: submit creates `pending`, booking flips to `booked`, and only non-bookers after 5 minutes enter the 10-day intensive
- Chose Hermes to replace the current landing-page `n8n` handoff so booking state, sequence state, inbound replies, and manual-call tasks live in one control plane

### 2026-04-13 Mission Control Finish Plan

- Added `docs/superpowers/plans/2026-04-13-mission-control-finish-plan.md` to separate safe branch completion from later Supabase persistence work
- Captured the recommended rollout order: finish backend/frontend Mission Control contract first, then do additive Supabase migrations in a separate gated pass
- Noted that the branch can be finished without immediate schema changes because the current blocking work is contract alignment, not persistence

### 2026-04-13 Mission Control Docs Sync

- Updated README, CONTEXT, memory, and Mission Control planning/spec docs to reflect the phase-6 landed read models and native shell
- Corrected stale repo-root references in the orchestration plan
- Kept the current phase focus on docs/release-gate cleanup while Supabase persistence remains deferred

### 2026-04-13 Mission Control Frontend Shell

- Added `apps/mission-control/` as a minimal React/TypeScript Mission Control app scaffold with a dense native shell, dashboard, inbox, approvals, runs, agents, and settings/assets surfaces
- Added a typed Mission Control API client, tiny query cache helper, and local fixtures so the UI remains buildable and testable without live Supabase or live backend coupling
- Added Vite/Vitest/TypeScript setup plus targeted UI tests covering shell navigation/search rendering and dashboard count rendering from fixture data

### 2026-04-12 Repo Bootstrap

- Created the clean `Hermes Central Command` repo path
- Confirmed a fresh Supabase project is reachable
- Confirmed migration dry-run access works against the new project
- Ported WAT and memory/context operating conventions into the new repo
- Added Trigger.dev bootstrap files and verified `trigger:dev` reaches a ready local worker
- Added `CODEX.md` with subagent orchestration and cleanup rules

### 2026-04-13 Managed-Agent Scaffold Phase 5

- Added in-memory managed-agent scaffolding for versioned agents, revisions, sessions, tool permissions, outcomes, and connect-later operational assets
- Added FastAPI routes for agents, sessions, permissions, outcomes, and agent assets
- Updated Hermes tools to respect explicit `always_allow`, `always_ask`, and `forbidden` permission policies without adding live Supabase wiring
- Added a scaffold-only Supabase migration placeholder for the deferred managed-agent schema seam
- Added targeted API and package-layout tests covering the new phase-5 surface

### 2026-04-13 Mission Control Read Models

- Added scaffold-first Mission Control read models for dashboard, inbox, and run lineage backed only by the in-memory control-plane store
- Added protected FastAPI routes for `/mission-control/dashboard`, `/mission-control/inbox`, and `/mission-control/runs`
- Added targeted API and package-layout tests covering dashboard counts, seeded inbox threads, and replay lineage with `parent_run_id`

### 2026-04-13 Control Plane Foundation

- Added typed command, approval, run, replay, and site-event runtime models
- Added FastAPI routes for commands, approvals, runs, replays, Hermes tools, and site events
- Added in-memory services to support idempotent command ingestion and replay safety
- Added Trigger.dev marketing worker chain scaffold in `trigger/`
- Added landing-page site-event forwarding plus runtime ingestion tests

### 2026-04-13 Mission Control Plan Rewrite

- Rewrote the Mission Control orchestration plan under `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- Made Hermes portability explicit: platform-agnostic core, installable anywhere the runtime stack can run
- Added feature-fit, anti-lock-in, and anti-duplication language so borrowed cloud-computer patterns stay adapter-friendly and Trigger.dev remains the durable execution backbone

### 2026-04-19 Ares North Star

- Framed Ares in repo-facing docs as the self-hosted operating system for distressed real-estate lead management; the operator UI is a visibility layer, not the core product.

### 2026-04-21 Ares Phase1 Models Contracts

- Added a new `app.domains.ares` domain module with explicit exports for `AresCounty`, `AresSourceLane`, `AresRunRequest`, and `AresLeadRecord`
- Locked county enum ordering to Harris, Tarrant, Montgomery, Dallas, Travis
- Locked run-request defaults with `include_briefs=True` and `include_drafts=True`, and county-string coercion into `AresCounty`
- Added explicit `estate_of` inference that marks records when owner names contain `estate of` or when the source lane is tax delinquency
- Added domain tests and package layout coverage for the new Ares domain module and verified the story command passes

### 2026-04-21 Ares Phase1 Briefs Drafts

- Added `app/services/ares_copy_service.py` with deterministic generation for operator-facing lead briefs and outreach drafts from ranked Ares opportunities
- Locked draft gating in code with `approval_status=\"pending_human_approval\"` and `auto_send=False` so drafts stay human-review-only
- Preserved rationale, county, source lane, and rank in both brief and draft outputs
- Added `tests/services/test_ares_copy_service.py` covering concise brief generation and pending-approval draft generation paths

### 2026-04-21 Shared Durable Memory Foundation

- Added `app/services/ares_memory_service.py` with JSON-backed durable memory state for market preferences, county defaults, lead history, outreach history, operator decisions, outcomes, and exceptions
- Added `tests/services/test_ares_memory_service.py` covering empty-load defaults and save/reload persistence across service instances
- Verified `uv run pytest tests/services/test_ares_memory_service.py -q` passes

### 2026-04-21 Shared Deterministic Tool Policy Foundation

- Added `app/services/ares_policy_service.py` with explicit tool allowlists, typed input/output contract validation, magical side-effect blocking, risky-call hard approval gating, audit entries, and kill-switch enforcement
- Added `tests/services/test_ares_policy_service.py` covering allowlist denial, typed contracts, magical side-effect blocking, hard-approval requirements, and audit/kill-switch behavior
- Verified `uv run pytest tests/services/test_ares_policy_service.py -q` passes
