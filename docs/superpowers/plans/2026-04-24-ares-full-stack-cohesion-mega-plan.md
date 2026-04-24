# Ares Full-Stack Cohesion Mega Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for implementation or `superpowers:executing-plans` for inline execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Ares into one cohesive app where Hermes, Ares, Trigger.dev, Supabase, Mission Control, TextGrid SMS, Resend email, Cal.com booking, and the lead-machine workflows all talk through explicit contracts instead of vibes and cursed glue.

**Architecture:** Hermes remains the operator shell. Ares is the deterministic runtime/API/policy/state layer. Supabase is canonical persistence. Trigger.dev runs durable async jobs and schedules. Providers transport side effects only: TextGrid for SMS, Resend for transactional/opt-in email, Cal.com for booking, and later Instantly/Smartlead for cold outbound. Mission Control reads Ares backend-owned read models; it never talks directly to Supabase.

**Tech Stack:** FastAPI, Pydantic, Supabase/Postgres/RLS, Trigger.dev v4, TypeScript, React/Vite/Vitest, TextGrid Twilio-compatible SMS API, Resend API, Cal.com webhooks, Hermes Agent HTTP runtime adapter.

---

## Source Inputs

This mega plan expands and supersedes the narrower Supabase-only map:

- `docs/superpowers/plans/2026-04-24-ares-supabase-wiring-from-memory.md`
- `CONTEXT.md`
- `memory.md`
- `TODO.md`
- `app/core/config.py`
- `app/main.py`
- `app/api/marketing.py`
- `app/api/trigger_callbacks.py`
- `app/api/mission_control.py`
- `app/db/client.py`
- `app/db/marketing_supabase.py`
- `app/domains/site_events/service.py`
- `app/services/marketing_lead_service.py`
- `app/services/inbound_sms_service.py`
- `app/services/booking_service.py`
- `app/providers/textgrid.py`
- `app/providers/resend.py`
- `trigger/src/shared/runtimeApi.ts`
- `trigger/src/runtime/reportRunLifecycle.ts`
- `trigger/src/marketing/*.ts`
- `supabase/migrations/*.sql`

## Current Reality

### Already exists

- Ares FastAPI runtime with protected routes behind `Authorization: Bearer <runtime_api_key>`.
- Hermes-facing tool surface:
  - `GET /hermes/tools`
  - `POST /hermes/tools/{tool_name}/invoke`
- Runtime command/approval/run APIs:
  - `POST /commands`
  - `POST /approvals/{approval_id}/approve`
  - `GET /runs/{run_id}`
  - `POST /replays/{run_id}`
- Trigger callback APIs:
  - `POST /trigger/callbacks/runs/{run_id}/started`
  - `POST /trigger/callbacks/runs/{run_id}/completed`
  - `POST /trigger/callbacks/runs/{run_id}/failed`
  - `POST /trigger/callbacks/runs/{run_id}/artifacts`
- Marketing APIs:
  - `POST /marketing/leads`
  - `POST /marketing/webhooks/calcom`
  - `POST /marketing/webhooks/textgrid`
  - `POST /marketing/internal/non-booker-check`
  - `POST /marketing/internal/lease-option-sequence/guard`
  - `POST /marketing/internal/lease-option-sequence/step`
  - `POST /marketing/internal/manual-call-task`
- Trigger.dev jobs currently present:
  - `marketing-check-submitted-lead-booking`
  - `marketing-run-lease-option-sequence-step`
  - `marketing-create-manual-call-task`
  - `createCampaignBrief`
  - `draftCampaignAssets`
  - `assembleLaunchProposal`
  - `runMarketResearch`
- Partial marketing Supabase adapter for contacts/conversations/messages/bookings/tasks/sequences.
- Direct site-events Supabase REST writer.
- TextGrid outbound SMS builder and inbound webhook normalization.
- Resend outbound email builder.
- Cal.com webhook handling seam.

### Still broken / incomplete

- `SupabaseControlPlaneClient.transaction()` still raises `NotImplementedError`.
- `control_plane_backend=supabase` is not safe yet.
- Marketing service swallows provider and Trigger scheduling exceptions; this hides failed side effects.
- Inbound SMS matching is phone-only and not tenant-safe enough.
- Sequence guard state is too simplistic for multi-tenant / advanced sequence rollout.
- Trigger jobs do not yet have full durable workflow observability in Supabase.
- Hermes does not yet have a first-class runtime adapter command pack that lets Telegram/operator actions call Ares cleanly.
- Mission Control still has fixture/in-memory surfaces and no full live end-to-end proof.
- Provider delivery status callbacks are not fully wired into durable message/event state.
- There is no one canonical end-to-end smoke proving: Hermes command -> Ares state -> Trigger job -> SMS/email/booking side effect -> provider webhook -> Ares state -> Mission Control read.

## Non-Goals

- Do not install Ares into Hermes.
- Do not make Hermes the database or business runtime.
- Do not let Mission Control frontend call Supabase directly.
- Do not make Trigger.dev the source of truth.
- Do not mirror Trigger internal logs into Supabase; store business-visible workflow state.
- Do not make TextGrid/Resend/Cal.com/Instantly the product model.
- Do not rewrite already-applied baseline migrations in place.
- Do not remove `business_id + environment` while adding org tenancy.
- Do not push production Supabase migrations from the wrong environment.

## Target Topology

```text
Telegram / CLI / Operator
  -> Hermes Agent
  -> Hermes Ares Runtime Adapter
  -> Ares FastAPI runtime
  -> Supabase canonical state + audit
  -> Trigger.dev async jobs / schedules
  -> Ares internal runtime endpoints
  -> Provider adapters: TextGrid, Resend, Cal.com, Instantly/Smartlead later
  -> Provider webhooks back into Ares
  -> Supabase events/messages/tasks/runs
  -> Mission Control backend read models
  -> Mission Control UI / Hermes status replies
```

## Ownership Map

### Hermes owns

- Telegram/CLI/operator shell.
- Human approvals and confirmations.
- Operator coordination and summaries.
- Hermes-native skills and local workflows.
- Calling Ares through explicit HTTP adapter/env config.

### Ares owns

- Runtime API.
- Business policy.
- Typed commands.
- Durable state integration.
- Provider adapter invocation.
- Trigger callback ingestion.
- Mission Control backend read models.
- Audit, usage, replay, release and operator-visible state.

### Supabase owns

- Canonical business records.
- Runtime events and audit.
- Workflow run records.
- Lead/contact/conversation/message/task/sequence state.
- Durable agent/session/permission/outcome/asset records.

### Trigger.dev owns

- Async jobs.
- Delays and schedules.
- Retries.
- Background workflow execution.

### Providers own

- TextGrid: SMS transport and SMS callbacks.
- Resend: email transport.
- Cal.com: booking events.
- Instantly/Smartlead later: cold outbound transport and campaign delivery callbacks.

---

# Phase 0 — Spec Gate And Branch Safety

## Goal

Create a single source of truth before implementation starts. This avoids mixing Supabase cutover, Hermes adapter work, Trigger jobs, provider webhooks, and Mission Control UI changes into one radioactive PR.

## Files

- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Modify: `TODO.md`
- Create: `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md`
- Keep: `docs/superpowers/plans/2026-04-24-ares-supabase-wiring-from-memory.md`
- Create/Use: `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`

## Tasks

- [ ] Create a dedicated implementation branch.

```bash
git switch -c feature/ares-full-stack-cohesion
```

Expected: branch created from the current known-good Ares branch after reviewing existing dirty docs.

- [ ] Write the spec gate.

The spec must define:

- Hermes/Ares boundary.
- Ares/Supabase persistence ownership.
- Ares/Trigger async boundary.
- Ares/provider adapter boundary.
- Mission Control read-model boundary.
- Lead-machine happy path.
- Non-goals.
- Required smoke tests.

- [ ] Update `CONTEXT.md` to point to this mega plan as the live integration scope.

- [ ] Update `memory.md` with only durable architecture facts after the spec is accepted.

## Verification

```bash
git diff --check
```

Expected: no whitespace errors. No runtime code changes yet.

## Exit Gate

A future worker can answer “who owns what?” without asking chat to reinterpret the architecture.

---

# Phase 1 — Environment And Contract Preflight

## Goal

Prove every system has explicit configuration and every crossing has a named contract before touching persistence.

## Files

- Modify: `.env.example`
- Modify: `README.md`
- Create: `docs/hermes-ares-trigger-supabase-runbook.md`
- Modify: `app/core/config.py`
- Modify: `trigger/src/shared/runtimeApi.ts`
- Test: `tests/smoke/test_health.py`
- Test: `tests/api/test_runtime_config_contract.py`
- Test: `trigger/src/shared/runtimeApi.test.ts` if Trigger test harness is present; otherwise add static contract test under `tests/api/test_trigger_contract_files.py`.

## Required env vars

### Hermes connector

```bash
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
HERMES_RUNTIME_API_KEY=dev-runtime-key
```

### Ares runtime

```bash
RUNTIME_API_KEY=dev-runtime-key
CONTROL_PLANE_BACKEND=memory
MARKETING_BACKEND=memory
SITE_EVENTS_BACKEND=memory
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DIRECT_CONNECTION_STRING=
TRIGGER_SECRET_KEY=
TRIGGER_API_URL=https://api.trigger.dev
TRIGGER_NON_BOOKER_CHECK_TASK_ID=marketing-check-submitted-lead-booking
CAL_API_KEY=
CAL_BOOKING_URL=
CAL_WEBHOOK_SECRET=
TEXTGRID_ACCOUNT_SID=
TEXTGRID_AUTH_TOKEN=
TEXTGRID_FROM_NUMBER=
TEXTGRID_SMS_URL=https://api.textgrid.com
TEXTGRID_WEBHOOK_SECRET=
RESEND_API_KEY=
RESEND_FROM_EMAIL=
RESEND_REPLY_TO_EMAIL=
```

### Trigger.dev runtime

```bash
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
HERMES_RUNTIME_API_KEY=dev-runtime-key
TRIGGER_SECRET_KEY=
```

### Mission Control UI

```bash
VITE_RUNTIME_API_BASE_URL=
RUNTIME_API_BASE_URL=http://127.0.0.1:8000
RUNTIME_API_KEY=dev-runtime-key
```

Local Vite dev uses a server-side proxy that injects `Authorization` from `RUNTIME_API_KEY` or `HERMES_RUNTIME_API_KEY`. Do not expose runtime auth with `VITE_RUNTIME_API_KEY`.

## Tasks

- [ ] Make `.env.example` readable and complete.

Current `.env.example` is credential-shaped sludge. Split it into sections:

- Hermes/Ares runtime.
- Supabase.
- Trigger.dev.
- Marketing providers.
- Mission Control UI.
- Optional model providers.

- [ ] Add config contract tests.

Test expected defaults:

- `control_plane_backend == "memory"`
- `marketing_backend == "memory"`
- `runtime_api_key` resolves.
- `site_events_backend` local default decision is explicit. If local dev lacks Supabase, set docs to use `SITE_EVENTS_BACKEND=memory`.

- [ ] Document local startup commands.

```bash
uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000
RUNTIME_API_BASE_URL=http://127.0.0.1:8000 RUNTIME_API_KEY=dev-runtime-key npm --prefix apps/mission-control run dev -- --host 127.0.0.1 --port 5173
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000 HERMES_RUNTIME_API_KEY=dev-runtime-key npm --prefix trigger run dev
```

- [ ] Document first smoke.

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS -H 'Authorization: Bearer dev-runtime-key' http://127.0.0.1:8000/hermes/tools
```

## Verification

```bash
uv run pytest tests/smoke/test_health.py tests/api/test_runtime_config_contract.py -q
npx tsc -p trigger/tsconfig.json --noEmit
npm --prefix apps/mission-control run typecheck
```

## Exit Gate

All env names and startup commands are explicit. No worker has to guess which variable points where.

---

# Phase 2 — Supabase Canonical Persistence Foundation

## Goal

Move from process-local runtime state to durable Supabase-backed repositories without changing public API behavior.

## Files

- Create: `supabase/migrations/202604240001_runtime_core_compatibility.sql`
- Create: `supabase/migrations/202604240002_managed_agent_persistence.sql`
- Modify: `app/db/client.py`
- Modify: `app/db/commands.py`
- Modify: `app/db/approvals.py`
- Modify: `app/db/runs.py`
- Modify: `app/db/events.py`
- Modify: `app/db/artifacts.py`
- Modify: `app/services/command_service.py`
- Modify: `app/services/approval_service.py`
- Modify: `app/services/run_service.py`
- Modify: `app/services/replay_service.py`
- Modify: `app/services/run_lifecycle_service.py`
- Test: `tests/db/test_commands_repository.py`
- Test: `tests/db/test_approvals_repository.py`
- Test: `tests/db/test_runs_repository.py`
- Test: `tests/api/test_commands.py`
- Test: `tests/api/test_approvals.py`
- Test: `tests/api/test_runs.py`
- Test: `tests/api/test_replays.py`
- Test: `tests/api/test_trigger_callbacks.py`

## Tasks

- [ ] Decide and document ID strategy.

Use this preferred shape unless rejected during implementation:

- Keep SQL bigint IDs internal.
- Add public runtime ID columns:
  - `runtime_command_id text unique`
  - `runtime_approval_id text unique`
  - `runtime_run_id text unique`
  - `runtime_artifact_id text unique`
- API continues exposing `cmd_*`, `apr_*`, `run_*` IDs.

- [ ] Add additive runtime compatibility migration.

Migration must preserve:

- command idempotency uniqueness.
- append-only events.
- replay lineage.
- Trigger run correlation.
- tenant scope.

- [ ] Implement command adapter.

Preserve:

- create command returns 201.
- duplicate idempotency returns 200 and `deduped=true`.
- policy/status mapping remains API-compatible.

- [ ] Implement approval adapter.

Preserve:

- approval-required commands create approval, not run.
- approval decision creates exactly one run.
- re-approval is idempotent.

- [ ] Implement runs/events/artifacts adapter.

Preserve:

- run detail response shape.
- normalized durable events/artifacts under the hood.
- replay lineage.
- Trigger callback transitions.

- [ ] Replace `SupabaseControlPlaneClient.transaction()` dead end.

Do not leave `control_plane_backend=supabase` booting into `NotImplementedError`.

## Verification

```bash
supabase db reset --local
CONTROL_PLANE_BACKEND=memory uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py tests/api/test_trigger_callbacks.py -q
CONTROL_PLANE_BACKEND=supabase uv run pytest tests/db/test_commands_repository.py tests/db/test_approvals_repository.py tests/db/test_runs_repository.py -q
CONTROL_PLANE_BACKEND=supabase uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py tests/api/test_trigger_callbacks.py -q
```

## Exit Gate

`control_plane_backend=supabase` changes storage only, not API behavior.

---

# Phase 3 — Hermes ↔ Ares Runtime Adapter

## Goal

Make Hermes able to use Ares as the runtime from Telegram/CLI without embedding Ares business logic inside Hermes prompts.

## Files

Ares repo:

- Create: `docs/hermes-ares-runtime-adapter-contract.md`
- Modify: `README.md`
- Test: `tests/api/test_hermes_tools.py`

Hermes repo, if implementation crosses into Hermes later:

- Create: `skills/software-development/ares-runtime-operator/` or equivalent Hermes-native skill.
- Create/modify a Hermes tool adapter only if the Hermes runtime supports external HTTP tools for this slice.

## Contract

Hermes calls Ares through:

```bash
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
HERMES_RUNTIME_API_KEY=dev-runtime-key
```

Required calls:

- discover tools: `GET /hermes/tools`
- invoke tool: `POST /hermes/tools/{tool_name}/invoke`
- approve: `POST /approvals/{approval_id}/approve`
- check run: `GET /runs/{run_id}`
- Mission Control dashboard: `GET /mission-control/dashboard`
- Mission Control approvals: `GET /mission-control/approvals`
- Mission Control runs: `GET /mission-control/runs`

## Tasks

- [ ] Write the runtime adapter contract doc.

Include:

- request headers.
- error behavior.
- example command invoke.
- approval flow.
- run polling.
- Mission Control readback.

- [ ] Add a Hermes operator smoke script if it belongs in Ares docs.

Create: `scripts/smoke_hermes_runtime_adapter.py`

Script behavior:

1. Reads `HERMES_RUNTIME_API_BASE_URL` and `HERMES_RUNTIME_API_KEY`.
2. Calls `/health`.
3. Calls `/hermes/tools`.
4. Invokes `run_market_research` with an idempotency key.
5. Prints command id and run id.

- [ ] Add tests around `/hermes/tools` payload stability.

Test:

- tools list includes known command types.
- approval modes match policy.
- invoke returns current API shape.

## Verification

```bash
uv run pytest tests/api/test_hermes_tools.py -q
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000 HERMES_RUNTIME_API_KEY=dev-runtime-key uv run python scripts/smoke_hermes_runtime_adapter.py
```

## Exit Gate

From Hermes/Telegram, an operator can create a typed Ares run, approve a gated command, and retrieve run state without direct database/provider access.

---

# Phase 4 — Ares ↔ Trigger.dev Runtime Contract

## Goal

Make Trigger.dev and Ares communicate through stable runtime endpoints, with durable lifecycle records and no hidden background magic.

## Files

- Modify: `trigger/src/shared/runtimeApi.ts`
- Modify: `trigger/src/runtime/reportRunLifecycle.ts`
- Modify: `trigger/src/runtime/queueKeys.ts`
- Modify: `trigger/src/marketing/checkSubmittedLeadBooking.ts`
- Modify: `trigger/src/marketing/runLeaseOptionSequenceStep.ts`
- Modify: `trigger/src/marketing/createManualCallTask.ts`
- Create: `trigger/src/lead-machine/leadIntake.ts`
- Create: `trigger/src/lead-machine/instantlyEnqueueLead.ts`
- Create: `trigger/src/lead-machine/instantlyWebhookIngest.ts`
- Create: `trigger/src/lead-machine/followupStepRunner.ts`
- Create: `trigger/src/lead-machine/suppressionSync.ts`
- Create: `trigger/src/lead-machine/taskReminderOrOverdue.ts`
- Modify: `trigger/bootstrap.ts`
- Modify: `app/api/trigger_callbacks.py`
- Modify: `app/services/run_lifecycle_service.py`
- Test: `tests/api/test_trigger_callbacks.py`
- Test: `tests/api/test_lead_machine_trigger_contract.py`

## Tasks

- [ ] Create a Trigger job contract test.

Expected IDs:

- `marketing-check-submitted-lead-booking`
- `marketing-run-lease-option-sequence-step`
- `marketing-create-manual-call-task`
- `lead-intake`
- `instantly-enqueue-lead`
- `instantly-webhook-ingest`
- `followup-step-runner`
- `suppression-sync`
- `task-reminder-or-overdue`

- [ ] Standardize runtime API endpoint names in Trigger.

All Trigger jobs must call Ares using `invokeRuntimeApi()` and the env vars:

- `HERMES_RUNTIME_API_BASE_URL` or `RUNTIME_API_BASE_URL`
- `HERMES_RUNTIME_API_KEY` or `RUNTIME_API_KEY`

- [ ] Add lifecycle reporting to every durable workflow job.

Each job that maps to an Ares run must call:

- started callback.
- completed callback.
- failed callback.
- artifacts callback when it produces operator-visible output.

- [ ] Add durable workflow run state in Supabase through Ares, not direct Trigger DB writes.

Trigger passes IDs and payloads back to Ares. Ares persists canonical state.

- [ ] Add queue key discipline.

Lease-option/non-booker sequence jobs must keep queue key by:

```text
business_id + environment + lead_id
```

## Verification

```bash
npx tsc -p trigger/tsconfig.json --noEmit
uv run pytest tests/api/test_trigger_callbacks.py tests/api/test_lead_machine_trigger_contract.py -q
```

## Exit Gate

Trigger.dev can run jobs, call Ares, report lifecycle, and schedule follow-up work without becoming the source of truth.

---

# Phase 5 — Provider Adapter Cohesion: TextGrid, Resend, Cal.com

## Goal

Make SMS, email, and booking providers reliable, observable, and durable inside the Ares runtime.

## Files

- Modify: `app/providers/textgrid.py`
- Modify: `app/providers/resend.py`
- Modify: `app/providers/calcom.py`
- Modify: `app/services/marketing_lead_service.py`
- Modify: `app/services/inbound_sms_service.py`
- Modify: `app/services/booking_service.py`
- Modify: `app/api/marketing.py`
- Modify: `app/api/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Test: `tests/services/test_textgrid_provider.py`
- Test: `tests/services/test_resend_provider.py`
- Test: `tests/services/test_booking_service.py`
- Test: `tests/services/test_inbound_sms_service.py`
- Test: `tests/api/test_marketing_runtime.py`
- Test: `tests/api/test_mission_control.py`

## Tasks

- [ ] Stop silently swallowing provider failures in operator-visible paths.

Current `MarketingLeadService.intake_lead()` catches and ignores SMS, email, and Trigger scheduling exceptions. Replace silent swallowing with durable side-effect status records:

- confirmation SMS queued/sent/failed.
- confirmation email queued/sent/failed/skipped.
- Trigger non-booker check scheduled/failed/skipped.

API can still return success for lead intake, but Mission Control must see side-effect failures.

- [ ] Fix Resend payload shape if needed.

`app/providers/resend.py` currently emits `to: [to_email]`. Existing Mailers AWF provider lesson says Resend recipient should often be a string in workflow JSON. Decide by live API/test contract and make it consistent across helpers.

- [ ] Add TextGrid status callback support.

Use `build_outbound_sms_request(..., status_callback_url=...)` and wire callbacks to:

- `POST /marketing/webhooks/textgrid`
- durable `messages` status updates.
- provider event records.

- [ ] Harden TextGrid inbound webhook matching.

Current matching uses `contacts.find_by_phone(phone=event.from_number)`. Add tenant-safe matching:

- match by provider `To` number to business/environment/org.
- match by `From` phone within that tenant.
- if multiple matches, create review task instead of picking one.
- if no match, create unlinked inbound message/review event instead of dropping it.

- [ ] Harden sequence reply action handling.

Replies should:

- `STOP` / `UNSUBSCRIBE` / `OPT OUT` => stop sequence and mark suppression.
- `call me` / `agent` => pause sequence and create operator task.
- other inbound reply => mark qualified/review-needed and pause automation unless policy says otherwise.

- [ ] Harden Cal.com booking webhooks.

Ensure booking created/rescheduled/cancelled updates:

- lead booking status.
- booking event table.
- sequence enrollment guard state.
- Mission Control timeline.

## Verification

```bash
uv run pytest tests/services/test_textgrid_provider.py tests/services/test_resend_provider.py tests/services/test_booking_service.py tests/services/test_inbound_sms_service.py -q
uv run pytest tests/api/test_marketing_runtime.py tests/api/test_mission_control.py -q
```

Optional live smoke, only with explicit permission and safe numbers/emails:

```bash
node /home/workspace/Mailers\ AWF/tools/test_textgrid_sms.mjs <to-number> "Ares TextGrid smoke"
node /home/workspace/Mailers\ AWF/tools/test_resend_email.mjs <to-email> "Ares Resend smoke" "Ares email smoke"
```

## Exit Gate

Lead intake, SMS, email, booking, provider callbacks, sequence pause/stop, and operator task creation are all visible in durable Ares state.

---

# Phase 6 — Lead-Machine End-To-End Workflows

## Goal

Make the real-estate lead machine cohesive: lead sources enter Ares, get persisted, go through Trigger workflows, use provider adapters, and show in Mission Control.

## Files

- Modify: `TODO.md`
- Create: `app/models/leads.py`
- Create: `app/models/lead_events.py`
- Create: `app/models/campaign_memberships.py`
- Create: `app/db/leads.py`
- Create: `app/db/lead_events.py`
- Create: `app/db/campaign_memberships.py`
- Create: `app/services/lead_intake_service.py`
- Create: `app/services/suppression_service.py`
- Create: `app/api/lead_machine.py`
- Modify: `app/main.py`
- Create: `tests/api/test_lead_machine.py`
- Create: `tests/services/test_lead_intake_service.py`
- Create: `tests/services/test_suppression_service.py`
- Modify/Create: `trigger/src/lead-machine/*.ts`

## Workflows

### Lease-option inbound lead

```text
Landing page / Hermes / API
  -> POST /marketing/leads or /lead-machine/intake
  -> Ares persists lead/contact/conversation/event
  -> Ares sends confirmation SMS/email through providers
  -> Ares schedules non-booker check in Trigger.dev
  -> Trigger waits 5m
  -> Trigger calls /marketing/internal/non-booker-check
  -> if still pending, Trigger runs sequence steps
  -> Ares dispatches SMS/email
  -> TextGrid/Cal.com webhooks update Ares
  -> Mission Control shows status/tasks/replies
```

### Probate keep-now lead

```text
Probate puller / fixture source
  -> Ares lead intake
  -> deterministic keep-now filter
  -> HCAD match/scoring
  -> Supabase lead + lead_event
  -> Mission Control lead queue
  -> approval-gated outreach bundle
```

### Curative-title cold email

```text
Lead queue
  -> suppression / consent / cold-provider policy
  -> Instantly or Smartlead enqueue job
  -> provider webhook ingest
  -> durable campaign membership + lead events
  -> manual task only after email.sent
  -> Mission Control reply/suppression state
```

## Tasks

- [ ] Create canonical lead and lead_event model.

Required fields:

- `id`
- `business_id`
- `environment`
- `org_id` when available
- `source`
- `source_record_id`
- `campaign_key`
- `first_name`
- `last_name`
- `phone`
- `email`
- `property_address`
- `county`
- `status`
- `pipeline_stage`
- `priority`
- `dedupe_key`
- `metadata`

- [ ] Add durable lead intake API.

Route:

```text
POST /lead-machine/intake
```

Response distinguishes:

- `created`
- `deduped`
- `queued`
- `skipped`
- `failed_side_effects`

- [ ] Add Trigger lead-machine jobs.

Jobs from `TODO.md`:

- `lead-intake`
- `instantly-enqueue-lead`
- `instantly-webhook-ingest`
- `create-manual-call-task`
- `followup-step-runner`
- `suppression-sync`
- `task-reminder-or-overdue`

- [ ] Enforce manual-call task rule.

Only `email.sent` creates a manual call task for the cold-email flow.

- [ ] Make suppression durable.

Suppression reasons:

- replied.
- unsubscribed.
- hard_bounce.
- invalid_mailbox.
- duplicate_active_sequence.
- manual_pause.
- manual_stop.

## Verification

```bash
uv run pytest tests/api/test_lead_machine.py tests/services/test_lead_intake_service.py tests/services/test_suppression_service.py -q
npx tsc -p trigger/tsconfig.json --noEmit
```

## Exit Gate

The lead machine has one canonical intake/event model that all sources and providers can use.

---

# Phase 7 — Mission Control Cohesion

## Goal

Make Mission Control show the whole app, not just isolated runtime widgets.

## Files

- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `apps/mission-control/src/lib/api.ts`
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/components/MissionControlShell.tsx`
- Create: `apps/mission-control/src/pages/LeadMachinePage.tsx`
- Create: `apps/mission-control/src/pages/ProvidersPage.tsx`
- Create: `apps/mission-control/src/pages/WorkflowRunsPage.tsx`
- Create: `apps/mission-control/src/components/ProviderHealthPanel.tsx`
- Create: `apps/mission-control/src/components/LeadTimeline.tsx`
- Create: `apps/mission-control/src/components/WorkflowRunTimeline.tsx`
- Test: `tests/api/test_mission_control.py`
- Test: `apps/mission-control/src/pages/LeadMachinePage.test.tsx`
- Test: `apps/mission-control/src/pages/ProvidersPage.test.tsx`

## Tasks

- [ ] Add cohesive dashboard sections.

Dashboard should show:

- active Ares runs.
- pending approvals.
- Trigger job health.
- provider health:
  - TextGrid.
  - Resend.
  - Cal.com.
  - Supabase.
- lead-machine queue counts.
- replies needing review.
- failed side effects.

- [ ] Add lead timeline.

Timeline includes:

- intake.
- confirmation SMS/email.
- booking event.
- sequence enrollment.
- outbound sequence steps.
- inbound SMS replies.
- manual tasks.
- cold-email provider events.

- [ ] Add provider health page.

Show config/readiness without leaking secrets:

- TextGrid configured / not configured.
- Resend configured / not configured.
- Cal.com webhook secret configured / not configured.
- Trigger runtime reachable / not checked / failed.
- Supabase backend selected / memory fallback.

- [ ] Add workflow runs page.

Show:

- Ares run id.
- Trigger run id.
- status.
- started/completed/failed.
- artifacts.
- linked lead/campaign/task.

## Verification

```bash
uv run pytest tests/api/test_mission_control.py -q
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

## Exit Gate

An operator can see a lead, its automation state, provider side effects, Trigger job state, and required human actions from Mission Control.

---

# Phase 8 — Runtime Observability, Audit, Usage, Replay

## Goal

Make the app debuggable and replay-safe. No more “it queued somewhere maybe.” Fantastic way to die, operationally.

## Files

- Create/Modify: `app/models/audit.py`
- Create/Modify: `app/db/audit.py`
- Create/Modify: `app/services/audit_service.py`
- Create/Modify: `app/api/audit.py`
- Create/Modify: `app/models/usage.py`
- Create/Modify: `app/db/usage.py`
- Create/Modify: `app/services/usage_service.py`
- Create/Modify: `app/api/usage.py`
- Modify: `app/services/replay_service.py`
- Modify: `app/services/run_lifecycle_service.py`
- Modify: `app/services/mission_control_service.py`
- Test: `tests/api/test_audit.py`
- Test: `tests/api/test_usage.py`
- Test: `tests/api/test_replays.py`

## Tasks

- [ ] Add append-only audit for every meaningful action.

Events:

- Hermes command invoked.
- Approval created/approved/rejected.
- Trigger job scheduled/started/completed/failed.
- SMS/email attempted/sent/failed.
- Provider webhook received.
- Booking created/rescheduled/cancelled.
- Sequence paused/stopped/completed.
- Manual task created/completed.
- Lead suppressed/unsuppressed.

- [ ] Add usage accounting.

Track:

- runs.
- sessions.
- tool calls.
- provider sends.
- Trigger workflow attempts.
- model provider calls later.

- [ ] Add replay rules.

Replay should:

- create a new run or workflow attempt.
- preserve original lineage.
- never re-send SMS/email unless explicitly allowed.
- require approval for side-effectful replay.

## Verification

```bash
uv run pytest tests/api/test_audit.py tests/api/test_usage.py tests/api/test_replays.py -q
```

## Exit Gate

A failed workflow can be inspected, understood, and safely replayed without guessing or duplicate sends.

---

# Phase 9 — End-To-End Smoke Harness

## Goal

Prove the whole app works as one system.

## Files

- Create: `scripts/smoke_full_stack_cohesion.py`
- Create: `scripts/smoke_provider_readiness.py`
- Create: `docs/smoke-tests/full-stack-cohesion.md`
- Test: `tests/smoke/test_full_stack_contract.py`

## Smoke: no live sends

Default smoke must not send real SMS/email.

Flow:

1. Start Ares with memory or local Supabase.
2. Discover Hermes tools.
3. Invoke safe Ares command.
4. Create test lead.
5. Schedule fake/non-live Trigger path or assert task payload shape.
6. Simulate Cal.com webhook.
7. Simulate TextGrid inbound webhook.
8. Verify Mission Control dashboard/read models.
9. Verify audit/events/tasks/messages.

## Smoke: live provider opt-in

Only with explicit operator flags:

```bash
ARES_SMOKE_SEND_SMS=1
ARES_SMOKE_TO_PHONE=+1...
ARES_SMOKE_SEND_EMAIL=1
ARES_SMOKE_TO_EMAIL=...
```

Live smoke validates:

- TextGrid request shape.
- Resend request shape.
- provider response stored in Ares.

## Verification

```bash
uv run pytest tests/smoke/test_full_stack_contract.py -q
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

## Exit Gate

One command proves Hermes/Ares/Trigger/Supabase/provider/Mission Control cohesion in a deterministic way.

---

# Phase 10 — Preview/Staging Rollout

## Goal

Move from local proof to hosted proof without production chaos.

## Tasks

- [ ] Verify Supabase target.

```bash
supabase migration list --linked
supabase db push --dry-run --linked
```

- [ ] Apply migrations to preview/staging.

- [ ] Configure preview/staging env vars.

- [ ] Deploy/run Ares runtime.

- [ ] Run Trigger.dev dev/preview worker.

- [ ] Run Mission Control against preview runtime.

- [ ] Run no-live-send smoke.

- [ ] Run live provider smoke only after explicit approval.

## Verification

```bash
uv run pytest -q
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
npx tsc -p trigger/tsconfig.json --noEmit
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

## Exit Gate

Preview/staging proves the app can run cohesively before any production cutover.

---

# Phase 11 — Production Promotion

## Goal

Promote the exact tested migration chain and app build. No surprise rewrites. No “quick tweak before deploy” demon possession.

## Tasks

- [ ] Create backup/rollback point.
- [ ] Apply same migration chain proven in staging.
- [ ] Deploy Ares runtime with `CONTROL_PLANE_BACKEND=supabase` only after staging green.
- [ ] Deploy Trigger.dev jobs.
- [ ] Deploy Mission Control UI pointed at production Ares runtime.
- [ ] Run no-live-send smoke against production-safe fixtures.
- [ ] Run controlled live SMS/email smoke with explicit recipient approval.
- [ ] Monitor:
  - command ingestion.
  - approvals.
  - Trigger callbacks.
  - TextGrid status callbacks.
  - Cal.com callbacks.
  - Mission Control dashboard.
  - audit/usage events.

## Exit Gate

Production Ares is cohesive: Hermes can command it, Trigger can execute it, Supabase persists it, providers report back to it, and Mission Control can explain what happened.

---

# Minimum Test Gates For The Mega Plan

```bash
supabase db reset --local
uv run pytest tests/db/test_commands_repository.py tests/db/test_approvals_repository.py tests/db/test_runs_repository.py -q
uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py tests/api/test_trigger_callbacks.py -q
uv run pytest tests/api/test_hermes_tools.py tests/api/test_marketing_runtime.py tests/api/test_mission_control.py -q
uv run pytest tests/services/test_textgrid_provider.py tests/services/test_resend_provider.py tests/services/test_booking_service.py tests/services/test_inbound_sms_service.py -q
uv run pytest tests/api/test_lead_machine.py tests/services/test_lead_intake_service.py tests/services/test_suppression_service.py -q
uv run pytest tests/api/test_audit.py tests/api/test_usage.py -q
uv run pytest tests/smoke/test_full_stack_contract.py -q
uv run pytest -q
npx tsc -p trigger/tsconfig.json --noEmit
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
git diff --check
```

# Recommended Execution Strategy

Use separate subagents per phase, with QC between phases:

1. **Architecture/spec gate agent** — locks boundaries and docs.
2. **Supabase runtime core agent** — commands/approvals/runs/events/artifacts.
3. **Hermes adapter agent** — Hermes runtime adapter docs/smoke/tool contract.
4. **Trigger.dev agent** — job IDs, runtime API, lifecycle callbacks.
5. **Provider agent** — TextGrid/Resend/Cal.com side effects and webhooks.
6. **Lead-machine agent** — canonical leads, suppression, probate/cold-email flows.
7. **Mission Control agent** — dashboard/timeline/provider/workflow visibility.
8. **Observability agent** — audit/usage/replay/smoke harness.
9. **QC/devil agent** — checks no boundary was blurred and no source-of-truth duplication happened.

# First Slice To Execute

Start with **Phase 0 + Phase 1 only**.

Reason: if the boundary/env/runbook contracts are wrong, every later phase turns into archaeology with keyboards. We are not doing that again.

First concrete implementation PR should contain:

- full-stack cohesion spec.
- clean env contract.
- runbook.
- config contract tests.
- Trigger runtime API contract test.
- no live Supabase migrations.
- no live SMS sends.

# One-Line Truth

Supabase wiring is the database backbone, but the actual product only becomes real when Hermes can command Ares, Trigger can execute Ares work, TextGrid/Resend/Cal.com can report side effects back into Ares, and Mission Control can show the entire chain without lying.
