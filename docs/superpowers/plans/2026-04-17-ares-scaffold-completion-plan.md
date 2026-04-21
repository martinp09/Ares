# Ares Scaffold Completion (P0–P2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the Ares scaffold into a clean, operator-usable runtime without touching Supabase wiring, so Hermes can point at it, Mission Control can act on it, and the async boundary stays sane.

**Architecture:** Keep one portable runtime boundary: Hermes talks to Ares over HTTP, Ares owns deterministic state and policy, and Trigger.dev stays the only async orchestrator. P0 makes the operator console actionable, P1 makes the async boundary and smoke path real, and P2 hardens the bootstrap/docs and stage model so the scaffold feels like a system instead of a demo.

**Tech Stack:** FastAPI, Pydantic, pytest, Trigger.dev, React/Vite, TypeScript, existing in-memory repositories and read models.

---

## Scope Guard

- Do **not** wire live Supabase persistence in this plan.
- Do **not** introduce Redis or a second queue layer.
- Do **not** move Hermes chat logic into Ares.
- Do **not** build a full enterprise-control or release-management suite yet.
- This plan is only for finishing the scaffold already on the branch.

---

## P0 — Make the operator console actually do things

### Task 1: Add task completion and lead action endpoints to Mission Control

**Files:**
- Modify: `app/api/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/models/mission_control.py`
- Modify: `app/services/lead_task_service.py`
- Modify: `app/services/lead_suppression_service.py`
- Modify: `app/services/inbound_sms_service.py`
- Test: `tests/api/test_mission_control.py`
- Test: `tests/services/test_mission_control_service.py`

- [ ] **Step 1: Write the failing API tests**

```python
def test_complete_task_marks_task_done_and_records_note() -> None:
    client = build_client()
    response = client.post(
        "/mission-control/tasks/task_123/complete",
        json={"notes": "Called back, left voicemail"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["notes"] == "Called back, left voicemail"
```

```python
def test_suppress_lead_sets_global_suppression_and_removes_from_queue() -> None:
    client = build_client()
    response = client.post(
        "/mission-control/leads/lead_123/suppress",
        json={"reason": "replied"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["suppressed"] is True
```

- [ ] **Step 2: Run the targeted tests and confirm they fail**

Run:

```bash
uv run pytest tests/api/test_mission_control.py tests/services/test_mission_control_service.py -q
```

Expected: route or service failures for the new actions.

- [ ] **Step 3: Implement the minimal task/lead action flow**

Add request/response models such as:

```python
class TaskCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str | None = None

class LeadSuppressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str
```

Implement service methods that:
- mark tasks complete
- store operator notes
- create suppression records
- clear a lead from the active queue when suppressed
- optionally write a follow-up note onto the selected lead/thread context

- [ ] **Step 4: Run the tests and confirm they pass**

Run:

```bash
uv run pytest tests/api/test_mission_control.py tests/services/test_mission_control_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/mission_control.py app/services/mission_control_service.py app/models/mission_control.py app/services/lead_task_service.py app/services/lead_suppression_service.py app/services/inbound_sms_service.py tests/api/test_mission_control.py tests/services/test_mission_control_service.py
git commit -m "feat: add mission control lead actions"
```

### Task 2: Surface the new operator actions in Mission Control UI

**Files:**
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/lib/api.ts`
- Modify: `apps/mission-control/src/pages/TasksPage.tsx`
- Modify: `apps/mission-control/src/pages/InboxPage.tsx`
- Modify: `apps/mission-control/src/pages/SuppressionPage.tsx`
- Test: `apps/mission-control/src/pages/TasksPage.test.tsx`
- Test: `apps/mission-control/src/pages/SuppressionPage.test.tsx`

- [ ] **Step 1: Write failing UI tests for the new actions**

```tsx
it("shows a complete-task button and sends the completion note", async () => {
  render(<TasksPage ... />)
  await user.click(screen.getByRole("button", { name: /complete task/i }))
  expect(api.completeTask).toHaveBeenCalledWith("task_123", { notes: "Called back" })
})
```

- [ ] **Step 2: Run the Mission Control UI tests and confirm they fail**

Run:

```bash
npm --prefix apps/mission-control run test -- --run TasksPage.test.tsx SuppressionPage.test.tsx
```

Expected: missing handler / missing button failures.

- [ ] **Step 3: Implement the minimal UI wiring**

Add a compact action strip to task/thread cards with:
- complete task
- add notes
- suppress lead
- unsuppress lead
- mark follow-up outcome

Wire those actions into the API client and preserve the existing fixture fallback behavior.

- [ ] **Step 4: Run typecheck, tests, and build**

Run:

```bash
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/mission-control/src/App.tsx apps/mission-control/src/lib/api.ts apps/mission-control/src/pages/TasksPage.tsx apps/mission-control/src/pages/InboxPage.tsx apps/mission-control/src/pages/SuppressionPage.tsx apps/mission-control/src/pages/TasksPage.test.tsx apps/mission-control/src/pages/SuppressionPage.test.tsx
git commit -m "feat: wire mission control task actions"
```

---

## P1 — Normalize async boundaries and prove the loop end to end

### Task 3: Add one job boundary interface and route all async dispatch through it

**Files:**
- Create: `app/services/job_boundary.py`
- Create: `app/services/local_job_boundary.py`
- Create: `app/services/trigger_job_boundary.py`
- Modify: `app/services/marketing_lead_service.py`
- Modify: `app/services/probate_write_path_service.py`
- Modify: `app/services/lead_outbound_service.py`
- Modify: `app/services/lead_sequence_runner.py`
- Test: `tests/services/test_job_boundary.py`
- Test: `tests/host_adapters/test_trigger_job_boundary.py`

- [ ] **Step 1: Write the failing boundary tests**

```python
def test_local_boundary_logs_without_trigger_dependency() -> None:
    boundary = LocalJobBoundary()
    result = boundary.enqueue("lead-intake", {"lead_id": "lead_1"})
    assert result.job_id.startswith("job_")
```

```python
def test_trigger_boundary_posts_to_runtime_api() -> None:
    boundary = TriggerJobBoundary(base_url="http://127.0.0.1:8000", api_key="dev-runtime-key")
    result = boundary.enqueue("lead-intake", {"lead_id": "lead_1"})
    assert result.endpoint == "/lead-machine/internal/lead-intake"
```

- [ ] **Step 2: Run the new tests and confirm they fail**

Run:

```bash
uv run pytest tests/services/test_job_boundary.py tests/host_adapters/test_trigger_job_boundary.py -q
```

Expected: missing module / missing method failures.

- [ ] **Step 3: Implement the boundary and swap call sites**

The boundary should expose:
- `enqueue(job_name, payload)`
- `schedule(job_name, payload, run_at)`
- `status(job_id)`

The Trigger adapter should translate those calls to the current runtime API; the local adapter should no-op or log.

- [ ] **Step 4: Run targeted tests and typecheck**

Run:

```bash
uv run pytest tests/services/test_job_boundary.py tests/host_adapters/test_trigger_job_boundary.py -q
npm --prefix trigger run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/job_boundary.py app/services/local_job_boundary.py app/services/trigger_job_boundary.py app/services/marketing_lead_service.py app/services/probate_write_path_service.py app/services/lead_outbound_service.py app/services/lead_sequence_runner.py tests/services/test_job_boundary.py tests/host_adapters/test_trigger_job_boundary.py
git commit -m "refactor: normalize async job boundary"
```

### Task 4: Add a single end-to-end smoke harness for the lead machine loop

**Files:**
- Create: `tests/e2e/test_lead_machine_smoke.py`
- Create: `scripts/smoke/lead_machine_smoke.py`
- Modify: `README.md`
- Modify: `docs/hermes-ares-integration-runbook.md`

- [ ] **Step 1: Write the failing smoke test**

```python
def test_lead_machine_smoke_harness_covers_duplicate_submission_and_replay() -> None:
    result = run_smoke()
    assert result["duplicate_submission"] == "deduped"
    assert result["webhook_replay"] == "idempotent"
    assert result["manual_call_task"] == "single"
```

- [ ] **Step 2: Run it and confirm it fails**

Run:

```bash
uv run pytest tests/e2e/test_lead_machine_smoke.py -q
```

Expected: missing smoke helper.

- [ ] **Step 3: Implement the smoke helper**

The helper should cover:
- duplicate intake
- webhook replay
- `email.sent` -> exactly one manual call task
- `email.failed` -> exception, not a call task
- suppression on reply / bounce / unsubscribe

- [ ] **Step 4: Run the smoke test and the backend suite**

Run:

```bash
uv run pytest tests/e2e/test_lead_machine_smoke.py -q
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_lead_machine_smoke.py scripts/smoke/lead_machine_smoke.py README.md docs/hermes-ares-integration-runbook.md
git commit -m "feat: add lead machine smoke harness"
```

---

## P2 — Make the scaffold feel like a system

### Task 5: Finish the stage model and pain-stack prioritization

**Files:**
- Modify: `app/models/opportunities.py`
- Modify: `app/services/opportunity_service.py`
- Modify: `app/services/probate_lead_score_service.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `apps/mission-control/src/pages/PipelinePage.tsx`
- Test: `tests/services/test_opportunity_service.py`
- Test: `tests/services/test_probate_lead_score_service.py`
- Test: `tests/services/test_mission_control_service.py`

- [ ] **Step 1: Write tests for stage ordering and pain-stack prioritization**

```python
def test_keep_now_leads_rank_above_generic_tax_delinquent_leads() -> None:
    score = score_probate_lead(lead_with_estate_and_tax)
    assert score > score_probate_lead(lead_with_only_tax)
```

```python
def test_opportunity_summary_keeps_lanes_separate_by_source_and_stage() -> None:
    dashboard = service.get_dashboard(business_id="limitless", environment="dev")
    assert dashboard.opportunity_stage_summaries is not None
```

- [ ] **Step 2: Run the scoring and opportunity tests and confirm failures**

Run:

```bash
uv run pytest tests/services/test_opportunity_service.py tests/services/test_probate_lead_score_service.py tests/services/test_mission_control_service.py -q
```

Expected: coverage failures or assertion failures for the new ordering rules.

- [ ] **Step 3: Implement explicit stage / scoring rules**

Keep the stage model simple and explicit:
- source lane stays separate from stage
- pain-stack inputs affect score, not identity
- keep-now beats generic distress when the facts support it

- [ ] **Step 4: Run the tests again**

Run:

```bash
uv run pytest tests/services/test_opportunity_service.py tests/services/test_probate_lead_score_service.py tests/services/test_mission_control_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models/opportunities.py app/services/opportunity_service.py app/services/probate_lead_score_service.py app/services/mission_control_service.py apps/mission-control/src/pages/PipelinePage.tsx tests/services/test_opportunity_service.py tests/services/test_probate_lead_score_service.py tests/services/test_mission_control_service.py
git commit -m "feat: tighten stage model and scoring"
```

### Task 6: Add one obvious launch path for the whole scaffold

**Files:**
- Create: `Makefile`
- Create: `scripts/dev/boot-local.sh`
- Create: `scripts/dev/smoke.sh`
- Modify: `README.md`
- Modify: `docs/hermes-ares-integration-runbook.md`

- [ ] **Step 1: Write the bootstrap target tests**

```bash
make help
make dev
make smoke
```

Expected: deterministic output and no missing-target failures.

- [ ] **Step 2: Add the launcher scripts**

`make dev` should start or describe:
- Ares API
- Mission Control UI
- Trigger worker
- Hermes connector env

`make smoke` should run the smoke harness.

- [ ] **Step 3: Verify the scripts are executable and documented**

Run:

```bash
chmod +x scripts/dev/boot-local.sh scripts/dev/smoke.sh
make help
make smoke
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add Makefile scripts/dev/boot-local.sh scripts/dev/smoke.sh README.md docs/hermes-ares-integration-runbook.md
git commit -m "docs: add local bootstrap paths"
```

---

## Self-Review Checklist

- [ ] Mission Control can act, not just display.
- [ ] Async dispatch goes through one boundary.
- [ ] The smoke path proves duplicate suppression and replay safety.
- [ ] Stage / scoring still separate identity from priority.
- [ ] Local boot is copy/pasteable.
- [ ] No Supabase wiring was added.
- [ ] No Redis or duplicate queue infrastructure was added.
- [ ] The plan keeps Hermes as the shell and Ares as the runtime.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-ares-scaffold-completion-plan.md`.

Two execution options:

1. **Subagent-Driven** — fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute task-by-task in this session with checkpoint verification.

Which approach?
