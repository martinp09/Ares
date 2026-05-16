 CONTEXT.md                                                    |  5 +++--
 TODO.md                                                       | 11 ++++++-----
 memory.md                                                     | 11 +++++++++--
 .../20260516131500_probate_source_identity_dedupe.sql         |  5 ++---
 tests/db/test_probate_source_identity_schema.py               |  2 ++
 5 files changed, 22 insertions(+), 12 deletions(-)
diff --git a/CONTEXT.md b/CONTEXT.md
index a1e3808..6194151 100644
--- a/CONTEXT.md
+++ b/CONTEXT.md
@@ -14,20 +14,21 @@
 - The deal spine remains no-send: deal promotion rejects `no_send=false`, `provider_sends_enabled=false` by default, fire-list provider gate items are operator-review only, and the UI adds no send/enroll/provider action buttons.
 - Origin-main hardening cleanup landed on GitHub `main`: `709f714` hardens runtime gates/CI and `be11aaa` tracks Docker deployment files; VPS edge/container hardening landed and deployed from `32a3f57`.
 - Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf`; handoff docs landed at `9f30d2f`; env preflight landed at `a859fd2`; case-detail enrichment finishes the final high-value probate PRD gap.
-- Probate autopilot dedupe/manual-isolation hardening is active in the local main worktree: hashed source identities (`county_case_sha256_v1`), same-scope prior-run dedupe, same-packet duplicate exclusion, Trigger `source_run_scope=autonomous`, isolated Hermes manual-run state/environment, and Supabase durable identity migration `20260516131500_probate_source_identity_dedupe.sql`. QC: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`.
+- Probate autopilot dedupe/manual-isolation hardening is active: hashed source identities (`county_case_sha256_v1`), same-scope prior-run dedupe, same-packet duplicate exclusion, Trigger `source_run_scope=autonomous`, isolated Hermes manual-run state/environment, and remote Supabase durable identity migration `20260516131500_probate_source_identity_dedupe.sql` applied on 2026-05-16. QC: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/` and `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`.
 - Trigger schedules default to live public probate source acquisition, public case-detail page enrichment, and public CAD/tax/land-record enrichment; backend live source/case-detail/CAD/tax/land flags also default on.
 - Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and remains source of truth for eligibility, suppression, verification, approval, deal state, and mirror/send state; legacy `/crm/hubspot/*` live writes now also require `operator_approval=true`.
 - Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot batch mirror writes, Slack/provider sends, and deploys remain separate approval gates; GitHub Actions CI now runs backend, Mission Control, Trigger, Docker image, and whitespace gates.
 - VPS `100.74.177.6` live Ares is deployed from `32a3f57`: `/opt/ares/Ares` is detached at `origin/main`, `ares-api` and `ares-ui` were rebuilt/recreated with non-root users and loopback-only Docker ports, Caddy binds only to `100.74.177.6:80` and loads the runtime bearer from root-only `/etc/caddy/ares-runtime.env`, `ares-edge-firewall.service` drops public `eth0` access to Caddy/Supabase dev ports, and Supabase migration `20260516011000_deal_spine_runtime` is applied. Post-deploy smoke: direct API `/deals` without auth `401`; tailnet `/health` 200, `/deal-desk` 200, `/deals` 200 in 327ms, `/deals/fire-list` 200 in 73ms, `/mission-control/probate-autopilot/health` 200; QC `docs/qc/2026-05-16/vps-edge-container-hardening/`.

 ## Current TODO
-1. Monitor the next non-empty no-send probate scheduler run after dedupe/isolation hardening; current local autonomous ledger comparison has 2026-05-15 Harris `39` / Montgomery `8` identities and 2026-05-16 `0` / `0`, so no today-vs-yesterday duplicate identities are present yet.
+1. Monitor the next non-empty no-send probate scheduler run after dedupe/isolation hardening; the durable identity ledger is now applied in remote Supabase, while current local autonomous ledger comparison has 2026-05-15 Harris `39` / Montgomery `8` identities and 2026-05-16 `0` / `0`, so no today-vs-yesterday duplicate identities are present yet.
 2. Wire `public.probate_source_identities` into the production Supabase source-run persistence adapter when the probate lane moves from file-backed source-run state to Supabase-backed state.
 3. Before any production no-send deployment, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.
 4. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
 5. Monitor VPS edge/firewall health after the `32a3f57` tailnet-only deployment; deal endpoints now use targeted Supabase reads and smoke at `/deals` 327ms / `/deals/fire-list` 73ms with no data.

 ## Recent Change
+- 2026-05-16: Applied remote Supabase migration `20260516131500_probate_source_identity_dedupe.sql` after Martin approved live migration push. First apply attempt safely failed before migration history because `business_id` was `text`; patched it to match live `public.businesses.business_id bigint`, removed the invalid lower-case check, reran focused contracts (`36 passed`), applied successfully, and verified remote migration history/schema/RLS/policies/indexes. QC: `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`.
 - 2026-05-16: Hardened Harris+Montgomery probate source dedupe/manual isolation. Nightly source-pull now computes stable hashed probate source identities, compares new rows against prior completed same-scope source runs, excludes prior/same-packet duplicates from new counts/enrichment, reports duplicate counts in `source_quality`, and preserves duplicate artifacts. Trigger schedules emit `source_run_scope=autonomous`; forced/manual Hermes runner state is isolated under `/opt/ares/lead-data/probate_autopilot/manual_runs` with `<environment>-manual`; Supabase migration `20260516131500_probate_source_identity_dedupe.sql` defines durable unique `(business_id, environment, source_run_scope, county, source_identity_key)`. QC: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`; verification db+services `466 passed`, Trigger typecheck passed.
 - 2026-05-16: Fixed Harris+Montgomery probate scheduler runtime error from the Saturday 07:10 CT run. Root cause: the background runner and Trigger schedule were using a current-day-only source window for morning catchup; current-day empty/unstable county pages caused adapter errors. Fix: 07:10 now pulls previous-day→current-day, 02:20 pulls 7 days, Sunday 03:15 pulls 30 days, and zero-row Harris/Montgomery result pages are valid non-errors. QC: `docs/qc/2026-05-16/probate-autopilot-scheduler-runtime-error/`; verification full backend `948 passed`, Trigger typecheck passed, temp-state 07:10 replay healthy with no provider side effects.
 - 2026-05-16: VPS edge/container hardening deployed from `32a3f57`: Caddy now binds only to tailnet `100.74.177.6:80`, runtime bearer moved to root-only systemd env file, `ares-edge-firewall.service` drops public Caddy/Supabase-dev ports on `eth0`, Docker API/UI ports are loopback-only, containers run non-root with `no-new-privileges`/dropped caps, and targeted deal Supabase reads cut no-data `/deals` smoke from ~12s to 327ms and `/deals/fire-list` to 73ms. QC: `docs/qc/2026-05-16/vps-edge-container-hardening/`.
diff --git a/TODO.md b/TODO.md
index 092f87f..99d9acc 100644
--- a/TODO.md
+++ b/TODO.md
@@ -1,7 +1,7 @@
 ---
 title: "Ares TODO / Handoff"
 status: active
-updated_at: "2026-05-16T13:10:45Z"
+updated_at: "2026-05-16T13:45:00Z"
 repo: "martinp09/Ares"
 local_checkout: "/opt/ares/worktrees/ares-main"
 target_branch: "main"
@@ -16,7 +16,7 @@ implementation_commit: "9c256bf"

 Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. This slice turns qualified leads into canonical deal records with lane-aware task/document/risk templates, stage transition blockers, fire-list read models, Supabase runtime persistence, and a read-only Mission Control Deal Desk page.

-The Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf` as an operational no-send system; handoff docs landed at `9f30d2f`, env preflight landed at `a859fd2`, and case-detail enrichment finished the last high-value probate enrichment gap. Trigger schedules default to live public probate source acquisition, live public case-detail page enrichment, and live public CAD/tax/land-record enrichment. Backend defaults those live intelligence lanes on, but Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and keeps every outbound path blocked. Dedupe/manual-isolation hardening now adds hashed probate source identities, same-scope prior-run dedupe, same-packet duplicate exclusion, `source_run_scope=autonomous` scheduled payloads, isolated manual Hermes runner state, and Supabase durable identity schema `20260516131500_probate_source_identity_dedupe.sql`; QC `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`.
+The Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf` as an operational no-send system; handoff docs landed at `9f30d2f`, env preflight landed at `a859fd2`, and case-detail enrichment finished the last high-value probate enrichment gap. Trigger schedules default to live public probate source acquisition, live public case-detail page enrichment, and live public CAD/tax/land-record enrichment. Backend defaults those live intelligence lanes on, but Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and keeps every outbound path blocked. Dedupe/manual-isolation hardening adds hashed probate source identities, same-scope prior-run dedupe, same-packet duplicate exclusion, `source_run_scope=autonomous` scheduled payloads, isolated manual Hermes runner state, and remote Supabase durable identity schema `20260516131500_probate_source_identity_dedupe.sql` applied on 2026-05-16; QC `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/` and `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`.

 Origin-main hardening cleanup landed on GitHub `main`: `709f714` adds the dynamic Montgomery PublicSearch land-record end date, live no-send smoke case-detail assertion, legacy `/crm/hubspot/*` `operator_approval=true` live-write gate, and CI; `be11aaa` tracks Docker deployment files and Docker CI.

@@ -30,7 +30,7 @@ Back Office Spine v0 verification passed pre-merge and post-merge: focused backe

 Cleanup verification on the `be76288` baseline passed: focused backend => `44 passed`; full backend => `945 passed`; Mission Control tests => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` and smoke/script py-compile => passed. GitHub Actions CI passed on `709f714` and `be11aaa`.

-No HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, live smoke, or Vercel deploys were executed by this cleanup. The only live mutations after approval were the VPS Docker/Caddy rebuild and the existing Supabase deal-spine migration.
+- No HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, live smoke, or Vercel deploys were executed by this cleanup. The only live mutations after approval were the VPS Docker/Caddy rebuild, the existing Supabase deal-spine migration, and the approved Supabase probate source identity migration.

 ## Primary handoff artifacts

@@ -42,13 +42,14 @@ No HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptr
 - Live operational PRD execution QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`
 - Live no-send smoke command: `uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day YYYY-MM-DD`
 - Probate dedupe/isolation QC: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`
-- Supabase probate source identity migration: `supabase/migrations/20260516131500_probate_source_identity_dedupe.sql`
+- Supabase probate source identity migration: `supabase/migrations/20260516131500_probate_source_identity_dedupe.sql` (applied remotely 2026-05-16)
+- Remote Supabase probate source identity migration QC: `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`
 - Probate no-send activation runbook: `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
 - HubSpot operating-spine QC index: `docs/qc/2026-05-14/README.md`

 ## Immediate next actions

-1. Monitor the next non-empty no-send probate scheduler run after the 2026-05-16 dedupe/isolation hardening. Current local autonomous ledger comparison has 2026-05-15 Harris `39` / Montgomery `8` source identities and 2026-05-16 `0` / `0`, so there are no today-vs-yesterday duplicate scraped identities yet; future non-empty runs should show `duplicate_prior_run_count` when overlap exists.
+1. Monitor the next non-empty no-send probate scheduler run after the 2026-05-16 dedupe/isolation hardening. The durable source identity table is now applied in remote Supabase, while current local autonomous ledger comparison has 2026-05-15 Harris `39` / Montgomery `8` source identities and 2026-05-16 `0` / `0`, so there are no today-vs-yesterday duplicate scraped identities yet; future non-empty runs should show `duplicate_prior_run_count` when overlap exists.
 2. Wire `public.probate_source_identities` into the production Supabase source-run persistence adapter when this lane moves from file-backed source-run state to Supabase-backed state.
 3. Before production no-send deployment, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.
 4. Keep Instantly enrollment/send, SMS/Vapi dispatch, paid skiptrace, and HubSpot batch mirror writes gated until separately approved.
diff --git a/memory.md b/memory.md
index 13a7da9..3c7a464 100644
--- a/memory.md
+++ b/memory.md
@@ -15,7 +15,7 @@

 - `/opt/ares/worktrees/ares-main` main handoff for Harris+Montgomery probate autopilot operational no-send implementation is `9c256bf` plus handoff docs at `9f30d2f`; the finished `fix/probate-autopilot-enrichment-wiring` branch was deleted.
 - Back Office Spine v0 landed on `main` at `e898ee0` and the local feature branch was deleted: canonical deal records, lead-to-deal promotion, lane-template tasks/docs/risks, stage blockers, fire-list, Supabase runtime persistence, and a read-only Mission Control Deal Desk. QC `docs/qc/2026-05-16/back-office-spine-v0/`; post-merge verification passed full backend `942`, Mission Control `82`, Mission Control typecheck/build, Trigger typecheck, and diff check. Follow-on hardening landed on GitHub `main` at `709f714`, Docker deployment tracking at `be11aaa`, and VPS edge/container hardening at `32a3f57`; VPS `100.74.177.6` is now tailnet-only via Caddy, API/UI Docker ports are loopback-only, containers run non-root, and deal read-model smoke improved from ~12s to `/deals` 327ms / `/deals/fire-list` 73ms with no data.
-- Probate autopilot is a live no-send intelligence/enrichment system: Trigger schedules and backend defaults run Harris+Montgomery public probate source adapters, public case-detail party/event/document/contact-candidate enrichment, and public CAD/tax/land-record enrichment, while Ares still requires explicit no-send approvals and blocks Instantly/SMS/Vapi/paid skiptrace/HubSpot batch writes until separately approved. Dedupe/isolation hardening: source rows use `county_case_sha256_v1` hashed identities, prior-run comparisons are scoped by `business_id + environment + source_run_scope`, scheduled payloads are `autonomous`, manual Hermes forced runs use isolated manual state/environment, and Supabase migration `20260516131500_probate_source_identity_dedupe.sql` defines the durable identity ledger. QC `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`. 2026-05-16 scheduler fix: 07:10 CT now pulls previous-day→current-day, 02:20 pulls 7 days, Sunday 03:15 pulls 30 days, and zero-row county result pages are valid non-errors; temp replay parsed Harris `40` + Montgomery `8`, SLA healthy. QC `docs/qc/2026-05-16/probate-autopilot-scheduler-runtime-error/`.
+- Probate autopilot is a live no-send intelligence/enrichment system: Trigger schedules and backend defaults run Harris+Montgomery public probate source adapters, public case-detail party/event/document/contact-candidate enrichment, and public CAD/tax/land-record enrichment, while Ares still requires explicit no-send approvals and blocks Instantly/SMS/Vapi/paid skiptrace/HubSpot batch writes until separately approved. Dedupe/isolation hardening: source rows use `county_case_sha256_v1` hashed identities, prior-run comparisons are scoped by `business_id + environment + source_run_scope`, scheduled payloads are `autonomous`, manual Hermes forced runs use isolated manual state/environment, and remote Supabase migration `20260516131500_probate_source_identity_dedupe.sql` is applied for the durable identity ledger. QC `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/` and `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`. 2026-05-16 scheduler fix: 07:10 CT now pulls previous-day→current-day, 02:20 pulls 7 days, Sunday 03:15 pulls 30 days, and zero-row county result pages are valid non-errors; temp replay parsed Harris `40` + Montgomery `8`, SLA healthy. QC `docs/qc/2026-05-16/probate-autopilot-scheduler-runtime-error/`.
 - Ares remains source of truth; HubSpot is a mirror/operator surface; Instantly/Vapi/SMS/paid skiptrace remain separate explicit approval gates.
 - HubSpot operating spine / agentic company Phases 1-9 are complete with final QC index/readiness artifacts and runbooks under `docs/qc/2026-05-14/` and `docs/runbooks/`.
 - HubSpot portal customization was live-applied after operator instruction; HubSpot has Ares property groups/properties and all 12 Ares stages in the existing single `Sales Pipeline` (`docs/qc/2026-05-14/hubspot-live-buildout/`).
@@ -246,12 +246,19 @@

 ## Change Log

+### 2026-05-16 Probate Source Identity Supabase Migration
+
+- Applied remote Supabase migration `20260516131500_probate_source_identity_dedupe.sql` after Martin approved live migration push.
+- Initial live apply attempt failed before migration history because `probate_source_identities.business_id` was `text` while live `public.businesses.business_id` is `bigint`; patched the migration to `business_id bigint not null` and removed the invalid `business_id = lower(business_id)` check.
+- Successful verification: focused contracts `36 passed`, remote migration list shows `20260516131500` present locally/remotely, async schema check confirmed `business_id_type=bigint`, 21 columns, FK/unique/check constraints, RLS, tenant policies, and indexes. QC: `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`.
+- No Instantly enrollment/send, SMS/Vapi, paid skiptrace, HubSpot write, Slack/provider send, county mutation, Vercel deploy, or raw probate-row QC artifact.
+
 ### 2026-05-16 Probate Autopilot Dedupe And Manual Isolation

 - Hardened source-run dedupe so probate rows receive a stable `county_case_sha256_v1` hashed `source_identity_key` and nightly source-pull compares new source rows against prior completed same-scope source runs before computing `record_count`, `keep_now_count`, and enrichment inputs.
 - Prior same-scope duplicates are preserved in `duplicate_prior_run_rows`; same-packet repeats are preserved in `duplicate_current_run_rows`; morning brief `source_quality` reports prior/current duplicate counts and `deduped_existing_record_count`.
 - Trigger.dev scheduled payloads now emit `source_run_scope=autonomous`; forced/manual Hermes runner executions use `source_run_scope=manual`, isolated manual state/artifact/lock paths under `/opt/ares/lead-data/probate_autopilot/manual_runs`, and `<environment>-manual`.
-- Added Supabase durable contract migration `20260516131500_probate_source_identity_dedupe.sql` with unique `(business_id, environment, source_run_scope, county, source_identity_key)` and RLS.
+- Added and applied Supabase durable contract migration `20260516131500_probate_source_identity_dedupe.sql` with unique `(business_id, environment, source_run_scope, county, source_identity_key)` and RLS.
 - Local autonomous ledger comparison printed aggregate/hash-derived counts only: 2026-05-15 Harris `39` / Montgomery `8` identities; 2026-05-16 Harris `0` / Montgomery `0`; overlap `0` for both counties. QC evidence: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`; focused contracts `36 passed`; db+services `466 passed`; Trigger typecheck passed. No provider sends, Instantly enrollment, SMS/Vapi, paid skiptrace, HubSpot writes, Slack/provider sends, or deploy.

 ### 2026-05-16 Probate Autopilot Scheduler Runtime Error Fix
diff --git a/supabase/migrations/20260516131500_probate_source_identity_dedupe.sql b/supabase/migrations/20260516131500_probate_source_identity_dedupe.sql
index 78090a9..6bb7ba6 100644
--- a/supabase/migrations/20260516131500_probate_source_identity_dedupe.sql
+++ b/supabase/migrations/20260516131500_probate_source_identity_dedupe.sql
@@ -5,7 +5,7 @@

 create table if not exists public.probate_source_identities (
     id uuid primary key default gen_random_uuid(),
-    business_id text not null,
+    business_id bigint not null,
     environment text not null,
     source_run_scope text not null default 'autonomous',
     county text not null,
@@ -33,8 +33,7 @@ create table if not exists public.probate_source_identities (
     constraint probate_source_identities_version_check check (source_identity_version = 'county_case_sha256_v1'),
     constraint probate_source_identities_counts_check check (seen_count >= 1 and latest_record_count >= 0),
     constraint probate_source_identities_lower_check check (
-        business_id = lower(business_id)
-        and environment = lower(environment)
+        environment = lower(environment)
         and source_run_scope = lower(source_run_scope)
         and county = lower(county)
         and source_identity_key = lower(source_identity_key)
diff --git a/tests/db/test_probate_source_identity_schema.py b/tests/db/test_probate_source_identity_schema.py
index f262809..2851454 100644
--- a/tests/db/test_probate_source_identity_schema.py
+++ b/tests/db/test_probate_source_identity_schema.py
@@ -17,6 +17,7 @@ def test_probate_source_identity_migration_adds_durable_dedupe_table() -> None:
     sql = _sql()

     assert "create table if not exists public.probate_source_identities" in sql
+    assert "business_id bigint not null" in sql
     assert "references public.businesses (business_id, environment)" in sql
     assert "alter table public.probate_source_identities enable row level security" in sql
     assert "public.current_tenant_business_id()" in sql
@@ -40,4 +41,5 @@ def test_probate_source_identity_migration_enforces_stable_hashed_case_identity(
     assert "check (source_identity_version = 'county_case_sha256_v1')" in sql
     assert "county in ('harris', 'montgomery')" in sql
     assert "source_identity_key = lower(source_identity_key)" in sql
+    assert "business_id = lower(business_id)" not in sql
     assert "seen_count >= 1 and latest_record_count >= 0" in sql
