# HubSpot Operating Spine + Agentic Company Plan

> **Status update (2026-05-14):** Phases 1-9 are complete and pushed on commit `8c19c26`. The execution artifact map is `docs/qc/2026-05-14/README.md`; final readiness evidence is `docs/qc/2026-05-14/operating-spine-final-readiness/`; runbooks are `docs/runbooks/agentic-company-operating-cadence.md` and `docs/runbooks/provider-sync-and-recovery.md`. Phase numbering drift is reconciled in the QC index: current chat Phase 8 is Mission Control provider ops / Hermes tool catalog, and Phase 9 is final QC/readiness/runbooks/living docs. After operator instruction, HubSpot portal customization itself was live-applied and verified in `docs/qc/2026-05-14/hubspot-live-buildout/`: Ares property groups/properties are present and all 12 Ares stages were added to the existing single HubSpot `Sales Pipeline`. A later operator-approved synthetic record-sync canary plus provider-links migration is verified in `docs/qc/2026-05-14/hubspot-record-sync-canary/`. No Instantly enrollment/send, Vapi call, source-provider pull, Slack send, batch HubSpot sync, or deploy was executed; the pushed branch still needs review/merge before promotable/deployed claims.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` or `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make HubSpot the operator-facing CRM mirror while Ares remains the canonical AI-native business runtime controlled by Hermes, with Instantly and Vapi connected through approval-gated provider adapters.

**Architecture:** Ares/Supabase is the system of record. Hermes is the operator shell, agent supervisor, approval surface, and natural-language command layer. HubSpot is a high-visibility CRM mirror for people/deals/tasks; Instantly is the outbound email execution layer; Vapi is the voice/call execution layer; Trigger.dev owns durable schedules, delays, retries, and reconciliation jobs. No provider owns canonical business state.

**Tech Stack:** FastAPI, Pydantic settings, Supabase/Postgres, Trigger.dev, React Mission Control, HubSpot Service Key REST API, Instantly API, Vapi API, Hermes tools/skills/delegation, provider webhooks.

---

## Why this matters

This is the operating spine for an AI-native real-estate company. The right design is not “sync random tools together.” The right design is:

```text
Martin / Hermes
  -> typed Ares command or tool
  -> Ares policy + source-of-truth state
  -> Trigger.dev durable job when async/scheduled
  -> provider adapter: HubSpot / Instantly / Vapi / TextGrid / Resend / Tracerfy
  -> webhook/result back into Ares
  -> HubSpot + Mission Control read models updated
  -> Hermes gets next-best-action context
```

The same rule applies everywhere: **Ares decides, providers execute/mirror, Hermes supervises.**

---

## Current evidence and constraints

### Confirmed

- HubSpot Service Key is configured locally as `HUBSPOT_ACCESS_TOKEN` and read-only probes passed for:
  - owners
  - contacts / companies / deals
  - contact / company / deal properties
  - deal pipelines via `/crm/v3/pipelines/deals`
  - deal pipelines via `/crm/pipelines/2026-03/deals`
- HubSpot Service Keys are public beta REST bearer tokens. They are good for direct REST integration.
- HubSpot Service Keys do **not** authenticate HubSpot webhooks, UI extensions, or other app-only platform features.
- If we later need HubSpot-to-Ares push events, a private app / app webhook path is still needed.
- Ares already has strong foundations for:
  - canonical CRM records
  - opportunities
  - tasks
  - provider webhooks
  - lead events
  - Trigger.dev callbacks
  - Instantly provider client
  - Mission Control records/tasks/pipeline/read models
- Ares now has active runtime code for HubSpot and Vapi providers, with dry-run/read surfaces first and live apply/dispatch behind explicit gates.
- HubSpot portal customization has been live-applied: Ares custom properties are present on contacts/companies/deals and Ares stages are present in the existing single HubSpot deal pipeline.

### Source docs read

- HubSpot Service Keys: `https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/account-service-keys`
- HubSpot Contacts API: `https://developers.hubspot.com/docs/api-reference/latest/crm/objects/contacts/guide`
- HubSpot Properties API: `https://developers.hubspot.com/docs/api-reference/latest/crm/properties/guide`
- HubSpot Pipelines API: `https://developers.hubspot.com/docs/api-reference/latest/crm/pipelines/guide`
- HubSpot private-app webhooks: `https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/create-and-edit-webhook-subscriptions-in-private-apps`
- Instantly docs index: `https://developer.instantly.ai/`
- Vapi call API docs index observed at: `https://docs.vapi.ai/api-reference/calls/create`

---

## Source-of-truth decision

### Canonical store

**Supabase through Ares remains canonical for all business state.**

Canonical tables/models already present or expected:

- Existing:
  - `crm_records`
  - `crm_source_records`
  - `crm_record_source_memberships`
  - `crm_record_status_history`
  - `crm_record_promotions`
  - `crm_record_saved_views`
  - `leads`
  - `lead_events`
  - `campaigns`
  - `campaign_memberships`
  - `provider_webhooks`
  - `tasks`
  - `opportunities`
  - `commands`
  - `approvals`
  - `runs`
  - `artifacts`
- Add:
  - `provider_object_links`
  - `provider_sync_cursors`
  - `provider_sync_runs`
  - `call_records`
  - `call_events`
  - `agent_work_items`

### Provider mirrors

Provider IDs should never be primary keys in Ares. Store them as links:

```text
Ares CRM record / opportunity / task
  -> provider_object_links(provider='hubspot', object_type='deal', provider_object_id='...')
  -> provider_object_links(provider='instantly', object_type='lead', provider_object_id='...')
  -> provider_object_links(provider='vapi', object_type='call', provider_object_id='...')
```

### Conflict rule

- Ares wins for source lane, score, task policy, approval status, suppression, and legal/title state.
- HubSpot can update contact details, owner assignment, notes, and human-entered dispositions only after Ares imports them through a controlled reconciliation job.
- Instantly can update outreach activity state, reply state, bounce state, and campaign membership state.
- Vapi can update call transcript, call outcome, recording URL, summary, and disposition.
- Hermes can trigger commands, approve actions, and write agent artifacts, but does not become the business database.

---

## HubSpot role

### Use HubSpot for

- CRM mirror visible in a normal sales/operator interface.
- Deals pipeline for opportunity-level view.
- Contact pages for owners/heirs/sellers/attorneys/agents.
- Human owner assignment.
- Basic task visibility if scope support is confirmed later.
- Quick manual notes/dispositions that Ares can reconcile.

### Do not use HubSpot for

- Curative-title truth.
- Probate/tax source-of-truth records.
- Agent run history.
- Trigger scheduling state.
- Provider webhooks as canonical events.
- Approval gates.
- Outreach/call automation policy.

### HubSpot object model

#### Contacts

HubSpot Contact = one reachable person.

Examples:

- heir
- seller
- executor
- spouse/co-owner
- attorney
- agent
- buyer/dispo contact later

Core Ares mapping:

- `crm_records.record_type = contact_record`
- `leads.email`, `leads.phone`, `crm_records.email`, `crm_records.phone`
- linked to property/opportunity through Ares relationships and HubSpot associations.

#### Companies

HubSpot Company = optional organization/entity.

Use only when the record is clearly an entity:

- LLC
- trust
- estate entity if needed
- title company
- attorney office
- vendor

Avoid forcing every property into Company. Real estate opportunities belong as Deals.

#### Deals

HubSpot Deal = one property/opportunity thread.

Ares canonical source:

- `opportunities`
- or promoted `crm_records` linked to `opportunities`

Suggested pipeline label:

```text
Ares Acquisitions
```

Suggested stages:

1. `New Lead`
2. `Data QC`
3. `Needs Skiptrace`
4. `Contact Ready`
5. `Outreach Queued`
6. `Outreach Active`
7. `Engaged`
8. `Appointment Set`
9. `Offer / Title Review`
10. `Contracting`
11. `Closed Won`
12. `Closed Lost / Dead`

### Initial custom property set

Property group:

```text
ares_information
```

Contact properties:

```text
ares_contact_id
ares_record_id
ares_source_lane
ares_contact_role
ares_contact_status
ares_skiptrace_status
ares_email_verification_status
ares_phone_verification_status
ares_last_outreach_channel
ares_last_outreach_at
ares_next_best_action
ares_last_agent_summary
```

Deal properties:

```text
ares_opportunity_id
ares_primary_record_id
ares_property_address
ares_county
ares_hcad_account
ares_source_lane
ares_lead_temperature
ares_lead_score
ares_tax_delinquency_status
ares_title_complexity
ares_occupancy_hint
ares_equity_hint
ares_skiptrace_status
ares_outreach_status
ares_instantly_campaign_id
ares_vapi_last_call_status
ares_vapi_last_call_outcome
ares_next_best_action
ares_last_agent_summary
ares_sync_hash
```

Company properties:

```text
ares_entity_id
ares_entity_role
ares_source_lane
ares_last_agent_summary
```

HubSpot property gotchas:

- Use `fieldType="booleancheckbox"` for boolean properties.
- Use internal enum values, not labels, when writing enumerations.
- Create unique identifier properties for Ares IDs where supported.
- Capture HubSpot-generated pipeline/stage IDs after creation.

---

## Instantly role

### Use Instantly for

- Cold email campaign execution.
- Campaign/subsequence management.
- Lead upload only after approval.
- Reply, bounce, unsubscribe, completed-campaign events.
- Email verification signal if useful, but Ares should still persist its own verification evidence.

### Do not use Instantly for

- Canonical lead storage.
- Deal stage truth.
- Title/legal status.
- Suppression truth outside Ares.
- Automatic activation without approval.

### Instantly flow

```text
Ares lead/opportunity selected
  -> Hermes/Mission Control asks approval
  -> Ares validates: contactable, not suppressed, email verified enough, campaign draft exists
  -> Trigger job uploads/enrolls to Instantly
  -> Instantly webhook returns activity
  -> Ares records lead_event/provider_webhook
  -> Ares updates CRM/opportunity/read model
  -> HubSpot mirror updates deal/contact fields
  -> Hermes gets next-best-action context
```

---

## Vapi role

### Use Vapi for

- AI voice calls after explicit approval.
- Inbound or outbound call handling.
- Qualification calls.
- Call transcripts/summaries.
- Disposition extraction.
- Optional tool calls back into Ares for safe actions.

### Do not use Vapi for

- Canonical task state.
- Canonical CRM state.
- Direct provider writes to HubSpot/Instantly.
- Unsandboxed tool execution.

### Vapi flow

```text
Ares task/opportunity qualifies for call
  -> Hermes or Mission Control approval
  -> Trigger job dispatches Vapi call through Ares provider adapter
  -> Vapi webhook sends call status/transcript/summary/tool events
  -> Ares stores call_records/call_events/provider_webhook
  -> Ares updates task/opportunity/contact state
  -> HubSpot mirror adds last call outcome / note field / task closure signal
  -> Hermes reviews transcript and next-best-action
```

Vapi is possible, but it is a later phase because Ares currently has no Vapi provider code. The existing `manual_call` task type is the seam to reuse.

---

## Hermes role

Hermes is the command shell and agent supervisor.

Use Hermes for:

- Natural-language operator commands.
- Skill-backed repeatable workflows.
- Multi-agent research and coding runs.
- Approval prompts.
- Status reports.
- QC review.
- Nightly loop steering.
- Explaining why an agent took an action.

Do not use Hermes as:

- lead database
- CRM truth
- provider state store
- hidden automation runtime

Every Hermes action should map to a typed Ares command or a documented local research artifact.

Suggested Hermes-facing tool names:

```text
crm.search_records
crm.create_task
crm.complete_task
crm.promote_record
hubspot.preview_sync
hubspot.apply_sync
hubspot.reconcile_changes
instantly.preview_enrollment
instantly.enqueue_approved_batch
vapi.preview_call
vapi.dispatch_approved_call
lead_machine.run_daily_pull
lead_machine.score_batch
lead_machine.prepare_outreach_packet
agent.run_qc_gate
```

---

## Scheduled task model

### Scheduling ownership

- Ares declares job contracts and stores run state.
- Trigger.dev runs durable background jobs, retries, delays, and schedules.
- Hermes cron may start research/watchdog loops, but long-term business jobs should graduate into Ares + Trigger.

### Core recurring jobs

1. **Daily source pull**
   - Harris probate filings
   - HCAD Estate Of scans
   - HCTax delinquency overlay
   - Harris land-record evidence where needed
   - Future counties after Harris is stable

2. **Daily dedupe + scoring**
   - normalize owners/addresses/accounts
   - merge duplicate source records
   - score deterministic signals
   - create or update `crm_records` and `opportunities`

3. **Daily HubSpot mirror sync**
   - push Ares changes to HubSpot contacts/deals/companies
   - store provider object links and sync hashes
   - no writes unless `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true`

4. **Hourly provider reconciliation**
   - Instantly campaign/member/reply/bounce state
   - Vapi call states when Vapi exists
   - HubSpot human updates if private-app/webhook or polling import is enabled

5. **Task escalation**
   - overdue manual review
   - overdue manual call
   - stale skiptrace required
   - reply needs human review
   - hot lead no next action

6. **Nightly AI review loop**
   - summarize new high-value leads
   - identify blocked tasks
   - draft next-day outreach packets
   - propose tests/experiments
   - stop at approval gate

7. **Weekly QC / hygiene loop**
   - provider sync drift
   - duplicate lead audit
   - suppression audit
   - stale deal audit
   - campaign result synthesis

---

## Manual task model

Ares tasks should be first-class, not just UI reminders.

Task fields needed or already present:

```text
task_id
business_id
environment
record_id
opportunity_id
contact_id
provider
provider_object_id
type
status
priority
due_at
assigned_to
created_by_agent_id
created_by_run_id
completed_by
completed_at
blocked_reason
next_step
raw_context
```

Minimum task types:

```text
manual_review
manual_call
follow_up
suppression_review
data_enrichment
hubspot_reconciliation
instantly_reply_review
vapi_transcript_review
title_review
offer_review
```

Manual task rules:

- A task can be created by agent or system, but completion must be auditable.
- Provider events may auto-complete narrow tasks only when deterministic, e.g. Vapi call completed closes `manual_call` and opens `vapi_transcript_review` if the outcome is ambiguous.
- Hermes can create and complete tasks through typed Ares tools.
- HubSpot tasks can be a mirror later, but Ares task table remains canonical.

---

## Agentic-native operating model

### Named agents

Use named agents with narrow jobs instead of one giant assistant.

1. **Lead Sourcer Agent**
   - pulls public records
   - writes source artifacts
   - never contacts leads

2. **Dedupe + Scoring Agent**
   - normalizes names/addresses/accounts
   - assigns deterministic score labels
   - flags ambiguous records for QC

3. **CRM Steward Agent**
   - maintains Ares canonical CRM hygiene
   - prepares HubSpot mirror payloads
   - detects provider drift

4. **Outreach Strategist Agent**
   - drafts email/SMS/direct-mail/call angles
   - never sends without approval

5. **Provider Sync Agent**
   - reconciles HubSpot/Instantly/Vapi states
   - records provider deltas
   - raises tasks for conflicts

6. **Voice Triage Agent**
   - reviews Vapi transcripts
   - extracts disposition and next step
   - proposes task updates

7. **QC Gate Agent**
   - reviews outputs before live writes/sends/calls
   - produces QC artifacts and failure reasons

8. **Operator Chief-of-Staff Agent**
   - summarizes daily state to Martin
   - answers “what should I do next?” from Ares state
   - never bypasses provider gates

### Required run artifact pattern

Every non-trivial agent run creates:

```text
run record
input manifest
output artifact
decision summary
provider writes attempted = yes/no
provider writes succeeded = count
next tasks created
QC verdict
```

---

## Implementation plan

### Phase 1: HubSpot provider adapter and dry-run mirror

**Files:**

- Create: `app/providers/hubspot.py`
- Create: `app/services/hubspot_mirror_service.py`
- Create: `app/api/hubspot.py` or add bounded routes to `app/api/mission_control.py`
- Modify: `app/core/config.py`
- Modify: `app/main.py`
- Test: `tests/providers/test_hubspot.py`
- Test: `tests/services/test_hubspot_mirror_service.py`
- Test: `tests/api/test_hubspot_mirror.py`

Steps:

- [ ] Add settings fields:
  - `hubspot_access_token`
  - `hubspot_base_url`
  - `hubspot_provider_live_writes_enabled`
  - `hubspot_default_pipeline_id`
  - `hubspot_default_deal_stage_id`
  - `hubspot_owner_id`
- [ ] Create a HubSpot client with:
  - bearer auth
  - timeout
  - safe error type
  - read-only methods for owners/properties/pipelines
  - write methods behind service-level gates only
- [ ] Create a mirror service that builds payloads for contacts/deals/companies from Ares records.
- [ ] Add `dry_run=true` as default.
- [ ] Add route:
  - `POST /mission-control/providers/hubspot/customization/preview`
- [ ] Add route:
  - `POST /mission-control/providers/hubspot/records/preview-sync`
- [ ] Add tests proving no provider call happens during preview.
- [ ] Add tests proving missing token fails before provider calls.
- [ ] Add tests proving live-write gates must both be enabled before mutation.

Acceptance:

- Dry-run payloads include exact property/pipeline/contact/deal payloads.
- No live HubSpot writes occur in tests unless explicitly mocked.
- Existing Service Key probe remains green.

### Phase 2: Provider object links and sync cursors

**Files:**

- Create: `supabase/migrations/<timestamp>_provider_object_links.sql`
- Create: `app/models/provider_links.py`
- Create: `app/db/provider_links.py`
- Test: `tests/db/test_provider_links_repository.py`

Add tables:

```sql
provider_object_links(
  id uuid primary key,
  business_id text not null,
  environment text not null,
  provider text not null,
  provider_object_type text not null,
  provider_object_id text not null,
  ares_object_type text not null,
  ares_object_id text not null,
  sync_hash text,
  last_synced_at timestamptz,
  raw_payload jsonb default '{}'::jsonb,
  unique(business_id, environment, provider, provider_object_type, provider_object_id),
  unique(business_id, environment, provider, ares_object_type, ares_object_id, provider_object_type)
)
```

```sql
provider_sync_cursors(
  id uuid primary key,
  business_id text not null,
  environment text not null,
  provider text not null,
  sync_name text not null,
  cursor_value text,
  last_success_at timestamptz,
  last_error text,
  unique(business_id, environment, provider, sync_name)
)
```

Acceptance:

- Same Ares record cannot create duplicate HubSpot object links.
- Same provider object cannot link to multiple canonical records without explicit conflict state.

### Phase 3: HubSpot customization live apply

**Files:**

- Modify: `app/services/hubspot_mirror_service.py`
- Test: `tests/services/test_hubspot_mirror_service.py`
- QC: `docs/qc/YYYY-MM-DD/hubspot-customization-live-apply/`

Steps:

- [ ] Build property group/property upsert plan.
- [ ] Build pipeline upsert plan by label.
- [ ] Require:
  - `PROVIDER_LIVE_SENDS_ENABLED=true`
  - `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true`
  - valid `HUBSPOT_ACCESS_TOKEN`
  - explicit operator approval from Hermes/Mission Control
- [ ] Run live apply once only after Martin approves.
- [ ] Capture returned pipeline/stage IDs.
- [ ] Store defaults in local env / deployment env, not tracked docs.
- [ ] Turn live-write gates back off after setup unless continuous sync is explicitly approved.

Acceptance:

- HubSpot has Ares property group and deal pipeline.
- Ares has captured HubSpot IDs.
- QC says exact mutation counts and proves no outreach/calls happened.

### Phase 4: Canonical CRM-to-HubSpot sync

**Files:**

- Modify: `app/services/hubspot_mirror_service.py`
- Create: `trigger/src/hubspot/syncHubSpotMirror.ts`
- Modify: `trigger/src/index.ts` or task registry file used by current Trigger setup
- Test: `tests/services/test_hubspot_mirror_service.py`
- Test: `trigger` typecheck

Rules:

- Create/update HubSpot Contact for contactable people.
- Create/update HubSpot Deal for opportunity/property thread.
- Optionally create/update Company only for entities.
- Persist provider links and sync hashes.
- Skip unchanged records.
- Do not write suppressed records except to update suppression status if already mirrored.

Acceptance:

- One Ares opportunity maps to one HubSpot Deal.
- Multiple contacts can associate to that Deal.
- Re-running sync is idempotent.
- Dry-run and live modes share payload builder.

### Phase 5: Instantly enrollment from Ares CRM

**Files:**

- Modify: `app/services/lead_outbound_service.py`
- Create: `app/services/campaign_enrollment_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `app/services/hermes_tools_service.py`
- Test: `tests/services/test_campaign_enrollment_service.py`
- Test: `tests/api/test_mission_control.py`

Add routes/tools:

```text
POST /mission-control/campaign-enrollments/preview
POST /mission-control/campaign-enrollments/approve
crm.instantly.preview_enrollment
crm.instantly.enqueue_approved_batch
```

Rules:

- Ares chooses eligible records.
- Hermes/Mission Control approves batch.
- Trigger handles upload/enrollment.
- Instantly webhooks update Ares lead events.
- HubSpot mirror updates `ares_outreach_status`, `ares_instantly_campaign_id`, and next-best-action.

Acceptance:

- No Instantly upload happens from preview.
- Approval creates a run and queued Trigger task.
- Reply/bounce/completed events create Ares events and update HubSpot mirror payloads.

### Phase 6: Vapi call layer

**Files:**

- Create: `app/providers/vapi.py`
- Create: `app/models/calls.py`
- Create: `app/db/calls.py`
- Create: `app/services/vapi_call_service.py`
- Create: `app/api/vapi.py`
- Create: `trigger/src/vapi/dispatchCall.ts`
- Create: `trigger/src/vapi/reconcileCalls.ts`
- Test: `tests/providers/test_vapi.py`
- Test: `tests/services/test_vapi_call_service.py`
- Test: `tests/api/test_vapi.py`

Add env:

```env
VAPI_PRIVATE_KEY=
VAPI_PUBLIC_KEY=
VAPI_BASE_URL=https://api.vapi.ai
VAPI_PROVIDER_LIVE_SENDS_ENABLED=false
VAPI_DEFAULT_ASSISTANT_ID=
VAPI_DEFAULT_PHONE_NUMBER_ID=
```

Routes/tools:

```text
POST /mission-control/providers/vapi/calls/preview
POST /mission-control/providers/vapi/calls/dispatch
POST /provider-webhooks/vapi
crm.vapi.preview_call
crm.vapi.dispatch_approved_call
```

Rules:

- Live call requires global provider gate + Vapi-specific gate + explicit approval.
- Store call transcript/summary/outcome in Ares.
- Close or update manual-call task when deterministic.
- Create review task when call result is ambiguous.
- Mirror last call status/outcome to HubSpot Deal/Contact.

Acceptance:

- No Vapi call from preview.
- Webhook ingestion is idempotent.
- Transcript review creates next-step task.

### Phase 7: Scheduled source pulls and nightly lead machine

**Files:**

- Create: `trigger/src/lead-machine/dailySourcePull.ts`
- Create: `trigger/src/lead-machine/dailyScoreAndPromote.ts`
- Create: `app/services/source_pull_service.py`
- Create: `app/services/lead_scoring_orchestrator.py`
- Modify: existing HCAD/HCTax worker integration points when promoting from scripts into Ares
- Test: source pull unit tests and service tests

Schedule lanes:

```text
daily_harris_probate_pull
daily_hcad_estate_scan
daily_hctax_overlay
nightly_dedupe_score_promote
morning_operator_brief
```

Rules:

- Keep source lanes separate.
- Dedupe into canonical records only after deterministic keys match.
- Promote ambiguous matches to manual QC task.
- Do not auto-enroll outreach.
- Generate next-day ranked queue and campaign packet.

Acceptance:

- Daily run produces input/output manifests.
- Every promoted record has source provenance.
- Every ambiguous match has a task.
- Morning brief can be generated for Hermes.

### Phase 8: Hermes tool expansion

**Files:**

- Modify: `app/services/hermes_tools_service.py`
- Modify: `app/services/command_service.py`
- Modify: `app/models/commands.py`
- Test: `tests/services/test_hermes_tools_service.py`
- Test: `tests/services/test_command_service.py`

Add typed commands/tools:

```text
search_crm_records
create_crm_task
complete_crm_task
preview_hubspot_sync
apply_hubspot_sync
preview_instantly_enrollment
enqueue_instantly_batch
preview_vapi_call
dispatch_vapi_call
run_daily_lead_pull
run_nightly_scoring
prepare_operator_brief
```

Rules:

- Read/search tools can be safe autonomous.
- Provider writes require approval.
- Calls/sends/uploads require approval.
- Every tool returns a run/task/artifact handle.

Acceptance:

- Hermes can operate the company without directly calling provider APIs.
- Ares policy gates are enforced even if Hermes asks for something risky.

### Phase 9: Mission Control surfaces

**Files:**

- Modify: `apps/mission-control/src/pages/RecordsPage.tsx`
- Modify: `apps/mission-control/src/pages/PipelinePage.tsx`
- Modify: `apps/mission-control/src/pages/TasksPage.tsx`
- Create: `apps/mission-control/src/pages/ProviderSyncPage.tsx`
- Create: `apps/mission-control/src/pages/CallsPage.tsx`
- Modify: `apps/mission-control/src/lib/api.ts`
- Test: relevant frontend tests

Add screens/sections:

- Provider sync status.
- HubSpot mirror status per record/deal.
- Instantly enrollment/reply status.
- Vapi call transcript/disposition.
- Agent work queue.
- Overdue/manual tasks.
- Approval queue.

Acceptance:

- Martin can see what is blocked and why.
- Provider state is visible but not treated as canonical.
- Every live action shows the required gate state.

### Phase 10: Observability, QC, and operating cadence

**Files:**

- Create: `docs/runbooks/agentic-company-operating-cadence.md`
- Create: `docs/runbooks/provider-sync-and-recovery.md`
- Create: `docs/qc/YYYY-MM-DD/<slice>/...` per implementation slice
- Modify: `CONTEXT.md`
- Modify: `memory.md`

Required dashboards/reports:

- Daily morning brief.
- Provider drift report.
- Outreach performance report.
- Call outcome report.
- Task overdue report.
- Lead source quality report.
- Agent failure/retry report.

Acceptance:

- Every provider mutation is auditable.
- Every nightly run produces an artifact.
- Every blocked provider sync opens a task or alert.
- No plan/docs drift after implementation.

---

## Tool-call ceiling / Hermes runtime budget plan

The installed Hermes source and config show these relevant keys:

```yaml
agent:
  max_turns: 60

delegation:
  max_iterations: 50
  child_timeout_seconds: 600

code_execution:
  max_tool_calls: 50
```

Source-code evidence from installed Hermes:

- `agent.max_turns` maps to `HERMES_MAX_ITERATIONS` in gateway startup.
- `AIAgent` uses `max_iterations` in its conversation loop.
- `delegation.max_iterations` caps each subagent independently.
- `code_execution.max_tool_calls` caps internal Hermes tool calls made by one `execute_code` script.

Recommendation:

```yaml
agent:
  max_turns: 200
  gateway_timeout: 3600
  gateway_timeout_warning: 1800
  gateway_notify_interval: 600
  restart_drain_timeout: 300

delegation:
  max_iterations: 100
  child_timeout_seconds: 1800
  max_concurrent_children: 3

code_execution:
  max_tool_calls: 200
```

Do **not** set normal Telegram runs to `1000` by default. It is technically possible, but it can create runaway cost, provider rate-limit problems, multi-hour turns, and amplified tool loops. Use `1000` only as a supervised special profile/temporary setting for a known long-running run.

If Martin approves a config change, implement as a Hermes config slice, not inside the Ares plan:

1. Snapshot `/root/.hermes/config.yaml`.
2. Patch the keys above.
3. Restart the Telegram/gateway service.
4. Verify startup log reports the new `max_iterations`.
5. Run a tiny tool-use smoke test.

---

## First execution slice recommendation

Start with the smallest slice that unlocks everything else:

```text
HubSpot Mirror Preview Slice
```

Build only:

- HubSpot settings in `app/core/config.py`
- `app/providers/hubspot.py`
- `app/services/hubspot_mirror_service.py`
- dry-run routes under Mission Control
- tests proving no provider writes
- QC artifacts

Do not build Vapi yet. Do not build HubSpot webhooks yet. Do not enroll Instantly yet. Get the CRM mirror contract right first, because it becomes the object model that Instantly, Vapi, tasks, and Hermes tools all reference.

---

## Readiness checklist before live provider writes

- [ ] Ares has HubSpot dry-run payloads reviewed.
- [ ] HubSpot Service Key rotated if the current chat-pasted key is considered exposed.
- [ ] `PROVIDER_LIVE_SENDS_ENABLED=true` is intentional for the test window.
- [ ] `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true` is intentional for the test window.
- [ ] The exact HubSpot properties/pipeline/stages are listed in QC before applying.
- [ ] After live apply, returned IDs are captured and live gates are turned off.
- [ ] No Instantly uploads or Vapi calls are bundled into the same slice.

---

## Open decisions

1. Should the first HubSpot pipeline be only acquisitions, or should we also create a separate long-nurture pipeline later?
2. Should HubSpot Contacts include attorneys/vendors now, or only reachable seller-side people in the first pass?
3. Do we want HubSpot human edits to reconcile back into Ares by polling first, or wait until a private app/webhook is justified?
4. Should Vapi begin as manual-call replacement only, or also handle inbound calls from the landing page later?
5. Should the Hermes ceiling be raised to the recommended 200/100/200 profile now, or kept at 60 until this plan enters implementation?
