$ git diff --stat
 .env.example |  6 ++++++
 CONTEXT.md   | 25 +++++++++++--------------
 README.md    |  6 +++++-
 TODO.md      | 12 +++++++-----
 memory.md    | 33 ++++++++++++++++++++-------------
 5 files changed, 49 insertions(+), 33 deletions(-)

$ git diff -- .env.example scripts/activation_readiness.py tests/scripts/test_activation_readiness.py docs/activation-readiness-handoff.md README.md TODO.md CONTEXT.md memory.md docs/qc/2026-05-10/activation-readiness-handoff/REPORT.md
diff --git a/.env.example b/.env.example
index 07cf964..e5c0bd1 100644
--- a/.env.example
+++ b/.env.example
@@ -28,6 +28,8 @@ TRIGGER_PROJECT_REF=
 TRIGGER_SECRET_KEY=
 TRIGGER_API_URL=https://api.trigger.dev
 TRIGGER_NON_BOOKER_CHECK_TASK_ID=marketing-check-submitted-lead-booking
+TRIGGER_APPOINTMENT_REMINDER_TASK_ID=marketing-send-appointment-reminder
+MARKETING_APPOINTMENT_REMINDERS_ENABLED=true

 # Marketing providers
 CAL_API_KEY=
@@ -43,6 +45,10 @@ RESEND_API_KEY=
 RESEND_EMAIL_URL=https://api.resend.com/emails
 RESEND_FROM_EMAIL=
 RESEND_REPLY_TO_EMAIL=
+SLACK_BOT_TOKEN=
+SLACK_CHANNEL_INTAKE=
+SLACK_CHANNEL_LEADS=
+SLACK_CHANNEL_ERRORS=
 INSTANTLY_API_KEY=
 INSTANTLY_WEBHOOK_SECRET=
 INSTANTLY_BASE_URL=https://api.instantly.ai
diff --git a/CONTEXT.md b/CONTEXT.md
index c5c0f48..5aa3472 100644
--- a/CONTEXT.md
+++ b/CONTEXT.md
@@ -3,34 +3,31 @@
 ## Stable Facts
 - Repo: `martinp09/Ares`
 - Current working checkout: `/root/Ares-inspect`
-- Active branch after ship: `feat/landing-ares-intake-sms-agent`
+- Active branch: `chore/activation-readiness-handoff-2026-05-09`
+- Latest merged main: PR #7 at `cda9c828` (`feat: expand landing intake contract`)
 - Runtime production URL: `https://production-readiness-afternoon.vercel.app`
 - Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
 - Supabase project ref: `awmsrjeawcxndfnggoxw`
 - Trigger project: `proj_puouljyhwiraonjkpiki`

 ## Current Scope
-- Landing-page -> Ares intake/SMS bridge is the active PR #7 branch `feat/landing-ares-intake-sms-agent`: Ares now accepts full seller-form context through `POST /marketing/leads`, preserves consent/UTM metadata, returns side-effect status, sends booking-link confirmation SMS/email when live-gated providers are configured, scaffolds Slack intake alerts behind the same live-send gate, and schedules Trigger-backed 24h/1h appointment reminders from Cal.com `starts_at` on booked/rescheduled events.
-- Approved local route smoke to Martin's phone/email reached Ares provider routes with `PROVIDER_LIVE_SENDS_ENABLED=true`; TextGrid returned `Balance is below 0` before SMS delivery and Resend was blocked by invalid `RESEND_FROM_EMAIL`, so provider funding/sender env remains the live-send gate.
-- Landing page branch `feat/landing-ares-intake-sms-agent` now routes `POST /api/contact` directly to Ares server-side; Supabase+n8n is no longer the active submit path.
-- Security-audit hardening is complete and ready to operate from `main` after the merge of `hardening/ares-security-audit-patches-2026-05-09`.
-- QC evidence: `docs/qc/2026-05-09/ares-security-audit-patches/`.
-- Patched: secret/build-context hygiene, runtime auth fail-closed behavior, docs/auth/security headers, server-derived provider webhook trust, Cal/TextGrid/Instantly signature enforcement, global provider live-send gate, Mission Control no-browser-token behavior, Node/Python advisory cleanup, and Bandit static-scan cleanup.
-- Verification passed: `git diff --check`, py compile, `uv run pytest -q` (`633 passed`), Trigger typecheck, Mission Control typecheck/build/full tests (`72 passed`), root/Trigger/Mission Control npm audits, pip-audit, and Bandit.
-- Harris daily lead-machine foundation remains merged to `main` via PR #5; Slack and production promotion are still separate follow-ups.
-- Production wiring is live and must remain untouched unless explicitly requested.
+- Lease-options landing -> Ares intake/SMS/email/Slack/reminder backend is merged to `main`; current branch adds activation readiness tooling/docs only.
+- `scripts/activation_readiness.py` reports Ares/landing live-launch gates without printing raw secrets; handoff is `docs/activation-readiness-handoff.md` and QC is `docs/qc/2026-05-10/activation-readiness-handoff/`.
+- Local readiness verdict is blocked by expected env/provider gates: live sends disabled, TextGrid/Resend/Slack/Cal/Trigger provider env missing in this checkout, and landing runtime env not present in this shell.
+- Approved prior route smoke reached Ares provider routes; TextGrid returned `Balance is below 0`, and Resend was blocked by invalid `RESEND_FROM_EMAIL`.
+- Security-audit hardening and Harris daily lead-machine foundation are merged to `main`; production wiring is live and must remain untouched unless explicitly requested.

 ## Current TODO
-1. Fix live provider env gates before claiming delivery: add TextGrid funds/valid sender account state, set verified `RESEND_FROM_EMAIL`, add `SLACK_BOT_TOKEN` plus `SLACK_CHANNEL_INTAKE`, and set `CAL_BOOKING_URL`/Cal webhook env.
-2. Deploy/update landing envs only after setting `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, and `BUSINESS_RUNTIME_ENVIRONMENT`; keep production promotion env-preserving.
+1. Set/fix provider envs/accounts, then rerun `python scripts/activation_readiness.py --json` before any live smoke.
+2. Set landing deployment envs: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
 3. Update provider callback configurations externally if any deployed provider still references old query-string runtime-key callback URLs.
 4. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

 ## Recent Change
-- 2026-05-09: Added live-gated intake provider bundle on the Ares branch: TextGrid booking-link SMS, Resend confirmation email, Slack intake scaffold, Cal.com `starts_at`, and Trigger-backed 24h/1h appointment reminders. Merge-readiness audit then tightened Slack behind the global live-send gate and made rescheduled Cal.com events refresh reminder scheduling without duplicate confirmations. Local approved route smoke hit TextGrid/Resend but delivery is blocked by TextGrid balance and invalid `RESEND_FROM_EMAIL`.
+- 2026-05-10: Added non-secret activation readiness tooling/handoff docs after PR #7 merge.
+- 2026-05-09: PR #7 merged landing -> Ares intake provider bundle: TextGrid booking-link SMS, Resend confirmation email, Slack intake scaffold behind live-send gate, Cal.com `starts_at`, and Trigger-backed 24h/1h reminders with reschedule refresh.
 - 2026-05-09: Completed security-audit hardening patch set and QC at `docs/qc/2026-05-09/ares-security-audit-patches/`.
 - 2026-05-09: Merged Harris daily probate + HCAD `Estate Of` import foundation to `main` via PR #5; Vercel preview smoke passed and Slack remains intentionally last.
-- 2026-04-30: Added Harris probate campaign launch backend slice and QC at `docs/qc/2026-04-30/harris-probate-campaign-launch/`.

 ## Read These Sections In `memory.md`
 1. `## Current Direction`
diff --git a/README.md b/README.md
index d84f24e..a8a7d0c 100644
--- a/README.md
+++ b/README.md
@@ -75,7 +75,8 @@ Current implementation notes:
 - Mission Control UI now follows the approved dark industrial terminal / pixel CRT style system
 - site-event ingestion is append-only and non-blocking at the API layer
 - Production wiring is live for Supabase-backed runtime state, Trigger callbacks, Instantly reply webhooks, TextGrid SMS/status callbacks, Cal.com booking callbacks, and Resend email smoke. Evidence is in `docs/rollout-evidence/production-2026-04-25.json`.
-- Lease-options landing-page contact intake is owned by Ares through `POST /marketing/leads`; the endpoint preserves seller-fit fields, consent metadata, and attribution from the public form, returns booking/side-effect status, and keeps seller-facing SMS/email plus Trigger reminder side effects gated by `PROVIDER_LIVE_SENDS_ENABLED`. Slack intake alerts are server-side and safely skipped until `SLACK_BOT_TOKEN` plus an intake/lead channel are configured.
+- Lease-options landing-page contact intake is owned by Ares through `POST /marketing/leads`; the endpoint preserves seller-fit fields, consent metadata, and attribution from the public form, returns booking/side-effect status, and keeps seller-facing SMS/email plus Trigger reminder side effects gated by `PROVIDER_LIVE_SENDS_ENABLED`. Slack intake alerts are server-side and safely skipped until `PROVIDER_LIVE_SENDS_ENABLED=true` plus `SLACK_BOT_TOKEN` and an intake/lead channel are configured.
+- Activation readiness handoff: `docs/activation-readiness-handoff.md`; non-secret gate report: `python scripts/activation_readiness.py --json`.

 ## Landing Page Intake Contract

@@ -174,6 +175,8 @@ curl -sS -H 'Authorization: Bearer dev-runtime-key' http://127.0.0.1:8000/hermes

 ## Verification

+- Activation gates: `python scripts/activation_readiness.py --json`
+- Provider request shape: `python scripts/smoke_provider_readiness.py`
 - Python: `uv run pytest -q`
 - Lead machine smoke: `uv run python scripts/smoke/lead_machine_smoke.py`
 - Trigger.dev: `npm --prefix trigger run typecheck`
@@ -194,6 +197,7 @@ curl -sS -H 'Authorization: Bearer dev-runtime-key' http://127.0.0.1:8000/hermes
 - `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-prd.json` as the overnight loop handoff artifact
 - future runtime database for canonical business state
 - curative-title workflow wiki: `docs/curative-title-wiki/index.md`
+- activation-readiness handoff: `docs/activation-readiness-handoff.md`
 - production-readiness handoff for live wiring gates: `docs/production-readiness-handoff.md`
 - production-readiness execution plan: `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`

diff --git a/TODO.md b/TODO.md
index 46124b5..94e77c7 100644
--- a/TODO.md
+++ b/TODO.md
@@ -1,18 +1,19 @@
 ---
 title: "Ares TODO / Handoff"
 status: active
-updated_at: "2026-05-09T22:25:23Z"
+updated_at: "2026-05-10T02:00:00Z"
 repo: "martinp09/Ares"
 local_checkout: "/root/Ares-inspect"
-current_branch: "feat/landing-ares-intake-sms-agent"
+current_branch: "chore/activation-readiness-handoff-2026-05-09"
 production_wiring_commit: "47be904"
+latest_main_commit: "cda9c828de40f9738bf936b185685ff47e5aac26"
 ---

 # Ares TODO / Handoff

 ## Current status

-Ares production wiring remains live for the controlled operator rollout. The Harris daily probate + HCAD `Estate Of` lead-machine foundation is merged to `main`; hosted preview smoke passed without Slack or provider sends. Security-audit hardening is merged to `main` with QC evidence at `docs/qc/2026-05-09/ares-security-audit-patches/`. The lease-options landing-page contact form is being moved onto Ares as the canonical intake backend through `feat/landing-ares-intake-sms-agent`; the backend now includes production-ready SMS/email confirmation, Slack intake scaffold, and appointment reminder plumbing, with credentialed live sends still gated by provider/env readiness.
+Ares production wiring remains live for the controlled operator rollout. The Harris daily probate + HCAD `Estate Of` lead-machine foundation is merged to `main`; hosted preview smoke passed without Slack or provider sends. Security-audit hardening is merged to `main` with QC evidence at `docs/qc/2026-05-09/ares-security-audit-patches/`. The lease-options landing-page -> Ares intake/provider/reminder backend is merged to `main` via PR #7 at `cda9c828`; live sends are still gated by provider/env readiness. Current branch `chore/activation-readiness-handoff-2026-05-09` adds non-secret activation readiness tooling and handoff docs.

 Live production evidence:

@@ -27,10 +28,10 @@ Known caveats:

 - Native `pg_dump` backup is not captured because the Supabase CLI container could not resolve the Supabase DB host from Colima. A REST table-export rollback bundle exists instead.
 - Slack digest delivery for the Harris daily import is intentionally last and blocked until `SLACK_BOT_TOKEN` plus target channels are available.
-- Slack intake notification delivery for lease-option leads is scaffolded but blocked until `SLACK_BOT_TOKEN` plus `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` are available.
+- Slack intake notification delivery for lease-option leads is scaffolded but blocked until `SLACK_BOT_TOKEN` plus `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` are available and `PROVIDER_LIVE_SENDS_ENABLED=true`.
 - Local approved live smoke to Martin's phone/email reached Ares routes; TextGrid returned `Balance is below 0` before SMS delivery and Resend was blocked by invalid `RESEND_FROM_EMAIL` format, so provider funding/sender env must be fixed before claiming live delivery.
 - Production promotion for the Harris daily import should be a dedicated handoff that preserves the production runtime/provider env contract; preview smoke passed at `https://production-readiness-afternoon-9adxg1gvb.vercel.app`.
-- Deployed provider callback configurations should be checked/updated externally after this security branch lands if any still use old `runtime_api_key` query-string URLs; runtime auth is now bearer-only plus provider signatures.
+- Deployed provider callback configurations should be checked/updated externally if any still use old `runtime_api_key` query-string URLs; runtime auth is now bearer-only plus provider signatures.

 ## Current product slice

@@ -45,6 +46,7 @@ Known caveats:
 - [done] Add Cal.com `starts_at` preservation plus Trigger-backed 24h/1h appointment reminder scheduling and `/marketing/internal/appointment-reminder` dispatch, including reschedule reminder refresh.
 - [done] Gate confirmation SMS/email, Slack intake alerts, appointment reminders, and non-booker Trigger scheduling behind `PROVIDER_LIVE_SENDS_ENABLED`; first deploy remains no-live-send by default.
 - [done] Replace the landing page active submit path with a server-side Ares bearer-auth handoff and remove Supabase+n8n active code.
+- [done] Add `scripts/activation_readiness.py` plus `docs/activation-readiness-handoff.md` for non-secret launch gate checks and smoke sequencing; QC evidence at `docs/qc/2026-05-10/activation-readiness-handoff/`.
 - [blocked] Approved local route smoke to Martin `+1***5914` / email reached Ares; TextGrid needs account funds and Resend needs valid `RESEND_FROM_EMAIL` before delivery succeeds.
 - [ ] Set landing runtime envs in the deployment target: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
 - [ ] Set Ares runtime envs for live launch: valid `CAL_BOOKING_URL`, `CAL_WEBHOOK_SECRET`, TextGrid callback secret/url, verified `RESEND_FROM_EMAIL`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_INTAKE`, and Trigger reminder task env.
diff --git a/memory.md b/memory.md
index e3d4cdf..e231793 100644
--- a/memory.md
+++ b/memory.md
@@ -27,7 +27,7 @@

 ## Current Direction

-- `/root/Ares-inspect` has active branch `feat/landing-ares-intake-sms-agent`; it now owns lease-option intake confirmation SMS/email, Slack intake scaffold, and appointment reminders. Harris daily lead-machine foundation and security-audit hardening are merged to `main`, and production wiring remains untouched.
+- `/root/Ares-inspect` has active branch `chore/activation-readiness-handoff-2026-05-09`; PR #7 is merged to `main` at `cda9c828` and lease-option intake confirmation SMS/email, Slack intake scaffold, and appointment reminders are code-ready behind live-send gates. Current activation docs/tooling: `docs/activation-readiness-handoff.md` and `scripts/activation_readiness.py`.
 - `POST /lead-machine/harris/daily-import` is implemented for Harris daily probate + HCAD `Estate Of` imports; it defaults to dry-run, records QC warnings, and never sends providers/Slack.
 - CRM control-plane work has been merged to `origin/main`.
 - CRM control-plane draft spec: `docs/superpowers/specs/2026-04-25-ares-crm-control-plane-design.md`.
@@ -186,18 +186,19 @@

 ## Open Work

-1. handle production/provider callback env updates in a dedicated handoff if any deployed callback still uses old query-string runtime-key URLs
-2. wire real Slack daily digest delivery only after Slack bot token and target channel config are available
-3. run a dedicated production promotion only when intentionally preserving/updating production runtime/provider env wiring
-4. add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract
-5. enrich Harris probate campaign exports with email/phone before any Instantly/TextGrid enrollment; current source artifact is direct-mail-ready only
-6. consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary; current Records bulk UI fans out through real single-record command callbacks
-7. defer owner/property graph, research cockpit, and map UI until Records and stage model are stable
-8. add explicit canonical source-lane metadata for CRM records before broadening promote routing beyond probate/lease-option lanes
-9. preserve production evidence files as the handoff source of truth
-10. optionally replace the REST rollback bundle with native pg_dump once Supabase CLI container DNS is fixed
-11. add production monitoring/alerts for provider callback failures
-12. keep browser acquisition and ambiguous research in Hermes or other driver agents, not inside Ares
+1. set/fix provider envs/accounts, then rerun `python scripts/activation_readiness.py --json` before any live smoke; current expected blockers are TextGrid funds/config, valid Resend sender, Slack token/channel, Cal URL/secret, Trigger secret, and landing runtime envs
+2. handle production/provider callback env updates in a dedicated handoff if any deployed callback still uses old query-string runtime-key URLs
+3. wire real Slack daily digest delivery only after Slack bot token and target channel config are available
+4. run a dedicated production promotion only when intentionally preserving/updating production runtime/provider env wiring
+5. add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract
+6. enrich Harris probate campaign exports with email/phone before any Instantly/TextGrid enrollment; current source artifact is direct-mail-ready only
+7. consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary; current Records bulk UI fans out through real single-record command callbacks
+8. defer owner/property graph, research cockpit, and map UI until Records and stage model are stable
+9. add explicit canonical source-lane metadata for CRM records before broadening promote routing beyond probate/lease-option lanes
+10. preserve production evidence files as the handoff source of truth
+11. optionally replace the REST rollback bundle with native pg_dump once Supabase CLI container DNS is fixed
+12. add production monitoring/alerts for provider callback failures
+13. keep browser acquisition and ambiguous research in Hermes or other driver agents, not inside Ares

 ## Completed Branch Work

@@ -208,6 +209,12 @@

 ## Change Log

+### 2026-05-10 Activation Readiness Handoff
+
+- Added `scripts/activation_readiness.py` to report runtime/provider/landing launch gates without printing raw secrets; it fingerprints secret presence and redacts sensitive URL queries.
+- Added `docs/activation-readiness-handoff.md` plus QC under `docs/qc/2026-05-10/activation-readiness-handoff/`.
+- Updated `.env.example`, README, TODO, and CONTEXT so PR #7 is treated as merged and the remaining work is provider/env activation plus external callback cleanup.
+
 ### 2026-05-09 Live SMS/Resend/Slack Reminder Finish

 - Extended `feat/landing-ares-intake-sms-agent` so Ares lead intake sends live-gated TextGrid confirmation SMS with booking link/STOP copy, Resend confirmation email, and server-side Slack intake alerts when configured and `PROVIDER_LIVE_SENDS_ENABLED=true`.
