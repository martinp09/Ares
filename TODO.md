---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-24T00:00:00-05:00"
repo: "martinp09/Ares"
local_checkout: "/Users/solomartin/Projects/Ares-full-stack-cohesion"
current_branch: "feature/ares-full-stack-cohesion-clean"
---

# Ares TODO / Handoff

## Live pointer

The current implementation blueprint is:

- `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`

Supporting source map:

- `docs/superpowers/plans/2026-04-24-ares-supabase-wiring-from-memory.md`

## Completed slices

Phase 0 + Phase 1:

- full-stack cohesion spec
- clean `.env.example`
- Hermes/Ares/Trigger/Supabase runbook
- config contract tests
- Trigger runtime API static contract test
- Vite dev proxy for authenticated Mission Control API calls without exposing a public runtime key
- no Supabase migrations
- no live SMS/email sends

Phase 2:

- Supabase control-plane transaction now snapshots, flushes, deletes, and restores core `commands`, `approvals`, `runs`, `events`, and `artifacts`.
- Rollback restore is FK-safe for command/run/event/artifact tables, including parent-before-child replay runs.
- Regression coverage covers core deletions, update rollback, bigint canonicalization, and failed flush restore.

Phase 3:

- Added `docs/hermes-ares-runtime-adapter-contract.md`.
- Added `scripts/smoke_hermes_runtime_adapter.py`.
- Added Hermes tool payload-stability coverage.

Phase 4:

- Standardized Trigger lifecycle callback payloads to Ares snake_case callback models.
- Added required lifecycle reporting for run-mapped lead-machine jobs.
- Kept scheduled marketing sequence jobs lifecycle-optional so existing non-run Trigger scheduling still works.
- Removed stale `create-manual-call-task` Trigger job ID and kept the planned `marketing-create-manual-call-task` ID.
- Enforced per-lead queue keys for lease-option sequence and manual-call child jobs.
- Persisted `trigger_run_id` from artifact callbacks.

Phase 5:

- Added `TEXTGRID_STATUS_CALLBACK_URL` config and passed it through outbound SMS requests.
- Provider side-effect failures during lead intake now create durable manual-review tasks visible in Mission Control.
- Lead-intake and sequence dispatch outbound messages now persist provider message IDs when available.
- TextGrid status callbacks update durable message status and record processed provider webhook receipts.
- Booking confirmation sends preserve successful provider message IDs even if a later channel fails, while booking suppression/opportunity sync still proceeds.

Phase 6:

- Added canonical `POST /lead-machine/intake` backed by existing `LeadRecord` and `LeadEventRecord` repositories.
- Generic lead intake is replay-safe through source-namespaced identity keys and deterministic intake event idempotency keys.
- Unknown lead source values fail closed instead of silently becoming `manual`.
- Trigger `lead-intake` now targets `/lead-machine/intake`; probate payloads keep a separate `probate-intake` job pointed at `/lead-machine/probate/intake`.

Phase 7:

- Mission Control dashboard now exposes backend-owned `provider_failure_task_count`.
- Provider-failure task counts and task rows are org-scoped through task details metadata, preventing cross-org leakage for same business/environment.
- Mission Control tasks UI distinguishes provider-failure reviews while preserving normal manual-call rendering.

Phase 8:

- Runtime command ingestion appends `hermes_command_invoked` audit events and `tool_call` usage records.
- Approval creation/approval and run creation now append durable audit events; run creation records `run` usage.
- Trigger lifecycle callbacks append `trigger_run_started`/`trigger_run_completed`/`trigger_run_failed` audit events, and started callbacks count `host_dispatch` usage attempts.
- Replay requests append audit with actor context and preserve existing side-effect safety: approval-required commands create no child run until the replay approval is approved.
- Observability is nonfatal after primary state changes, so audit/usage failures do not strand commands, approvals, runs, Trigger callbacks, or replays.
- Agent-backed audit/usage scope is preserved through command persistence, approval paths, Trigger lifecycle fallback, replay approvals, deduped retries, and direct/hydrated Supabase command storage.

Phase 9:

- Added deterministic in-process full-stack smoke coverage in `scripts/smoke_full_stack_cohesion.py`.
- The full-stack smoke exercises `/health`, Hermes tool discovery/invocation, Trigger lifecycle callbacks, lead intake, manual-call task intake, Cal.com booking webhook, TextGrid inbound webhook, Mission Control dashboard/runs, audit, usage, and repository-backed messages/tasks/bookings.
- Full-stack smoke forces memory-backed settings, clears live provider credentials, patches route-level marketing services during the run, and blocks any attempted live provider request.
- `reset_control_plane_store()` now clears dynamic marketing in-memory stores so repeated in-process smoke runs do not accumulate contacts, conversations, messages, bookings, or sequence enrollments.
- Added `scripts/smoke_provider_readiness.py` for TextGrid/Resend request-shape validation without sending; live flags require explicit `--allow-live`.
- Added `docs/smoke-tests/full-stack-cohesion.md` with the local smoke commands and no-live-sends contract.

## Hard rules

- Do not install Ares into Hermes.
- Do not make Hermes, Trigger.dev, providers, or Mission Control the source of truth.
- Do not let Mission Control frontend call Supabase directly.
- Do not rewrite already-applied baseline migrations in place.
- Do not remove `business_id + environment` while adding `org_id`.
- Do not run live provider sends without explicit opt-in recipient flags.
- Preserve the existing dirty Supabase persistence work in `/Users/solomartin/Projects/Ares` until it is intentionally reconciled.

## Latest verification

```bash
git diff --check
uv run pytest tests/smoke/test_health.py tests/api/test_runtime_config_contract.py tests/api/test_trigger_contract_files.py -q
uv run pytest tests/db/test_supabase_control_plane_client.py tests/db/test_control_plane_supabase_adapters.py -q
uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py tests/api/test_trigger_callbacks.py tests/api/test_hermes_tools.py tests/api/test_lead_machine_trigger_contract.py tests/api/test_marketing_sequence.py tests/api/test_marketing_leads.py -q
uv run pytest tests/providers/test_textgrid.py tests/providers/test_resend.py tests/providers/test_calcom.py tests/services/test_inbound_sms_service.py tests/services/test_booking_service.py tests/api/test_marketing_runtime.py tests/api/test_marketing_webhooks.py tests/api/test_marketing_leads.py tests/api/test_mission_control.py tests/api/test_mission_control_marketing.py -q
uv run pytest tests/api/test_lead_machine.py tests/services/test_lead_intake_service.py tests/api/test_lead_machine_trigger_contract.py -q
uv run pytest tests/api/test_mission_control.py::test_provider_failure_tasks_are_org_scoped_in_dashboard_and_tasks tests/api/test_marketing_leads.py -q
uv run pytest tests/api/test_audit.py tests/api/test_usage.py tests/api/test_replays.py -q
uv run pytest tests/smoke/test_full_stack_contract.py -q
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
uv run python scripts/smoke_provider_readiness.py
uv run pytest -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

## Next gate

Commit Phase 9, then start Phase 10 preview/staging rollout readiness next. Keep live Supabase migrations, provider sends, Trigger deploys, and production deploys gated on an explicitly verified safe target.
