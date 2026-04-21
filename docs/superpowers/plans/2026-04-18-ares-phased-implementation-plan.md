# Ares Phased Super Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the probate/tax-delinquent MVP and the autonomy roadmap into one execution plan that turns Ares from a lead-finding operator into a phased autonomous real-estate agent.

**Architecture:** Keep the current Hermes Central Command runtime as the deterministic backbone. Phase 1 delivers the probate + tax-delinquent lead machine. Later phases add planning, bounded execution, workflow autonomy, and finally a guardrailed operator loop on top of the same runtime and Mission Control surface. Do not rewrite the repo; add autonomy layers in order.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, uv, Trigger.dev, in-memory control plane first, Supabase when persistence is explicitly introduced.

---

## Merge Note

This document supersedes and merges:

- `docs/superpowers/plans/2026-04-18-ares-probate-tax-delinquent-mvp-plan.md`
- `docs/superpowers/specs/2026-04-18-ares-autonomy-roadmap.md`

The key merge rule is simple:

- the probate + tax-delinquent MVP becomes **Phase 1** of the autonomy journey
- the autonomy roadmap becomes the **phase structure** that follows it
- one plan, one sequence, no parallel universe nonsense

## Working Rules

- Keep the runtime/app split explicit: Hermes shell and operator UX outside the core runtime, deterministic execution inside it.
- Do not add autonomy by sneaking in magic behavior to routers.
- Prefer pure model/service logic with thin API wrappers.
- Keep each phase shippable on its own.
- Human approval stays mandatory until a later phase explicitly removes it.
- Commit after each task once its tests pass.
- Do not auto-send, auto-contract, auto-close, or auto-dispo in the MVP phase.

## Repo Fit Check

This repo already has the right spine for autonomy:

- typed commands, approvals, runs, replays
- Mission Control operator surfaces
- a marketing execution lane
- WAT architecture for workflows / agents / tools
- current runtime surface in `app/main.py`
- in-memory control plane services that can be extended without rewrite

That means the work is additive:

1. keep the runtime stable
2. add the lead wedge
3. add planner/executor layers
4. add autonomy guardrails and memory

---

## Phase 0: Baseline Lock and Runtime Readiness

**What it is:**
A short baseline phase that confirms the current runtime surface is stable enough to host autonomy.

**Current baseline files that matter:**

- `app/main.py`
- `app/core/config.py`
- `app/core/dependencies.py`
- `app/models/commands.py`
- `app/models/approvals.py`
- `app/models/runs.py`
- `app/models/mission_control.py`
- `app/services/command_service.py`
- `app/services/approval_service.py`
- `app/services/run_service.py`
- `app/services/mission_control_service.py`
- `app/api/commands.py`
- `app/api/approvals.py`
- `app/api/runs.py`
- `app/api/replays.py`
- `app/api/mission_control.py`
- `app/api/marketing.py`
- `app/api/hermes_tools.py`
- `tests/api/test_commands.py`
- `tests/api/test_runs.py`
- `tests/api/test_replays.py`
- `tests/api/test_mission_control_phase3.py`
- `tests/domains/marketing/test_marketing_flow.py`

### Phase 0 checklist

- Verify the runtime still boots cleanly on the current branch.
- Verify the current command/approval/run/replay surface is still intact.
- Verify Mission Control still renders the lead-machine shell and read models.
- Verify the marketing lane still works as a separate execution path.
- Verify the WAT architecture doc remains the operating-model reference.
- Verify the baseline still uses the in-memory control plane where it already does.

**Exit criteria:**
The repo is stable, the current runtime surface is green, and the merged plan can be executed without first untangling the baseline.

---

## Phase 1: Probate + Tax-Delinquent MVP

**What it is:**
The first real Ares slice. Ares finds probate leads across the five target Texas counties, overlays tax delinquency, separately screens tax-delinquent `estate of` properties, ranks the best opportunities, and generates outreach drafts for human approval.

**Counties:**

- Harris
- Tarrant
- Montgomery
- Dallas
- Travis

**Lead rules:**

- probate is the primary source lane
- tax delinquency is the overlay filter on probate
- overlap wins: probate + verified tax delinquent ranks highest
- tax-only work must focus on `estate of` properties and then confirm true delinquency

### Phase 1 file map

- Create: `app/models/ares.py`
- Create: `app/services/ares_service.py`
- Create: `app/services/ares_copy_service.py`
- Create: `app/api/ares.py`
- Create: `tests/domains/ares/test_models.py`
- Create: `tests/services/test_ares_service.py`
- Create: `tests/services/test_ares_copy_service.py`
- Create: `tests/api/test_ares_runtime.py`
- Modify: `app/main.py`
- Modify: `tests/test_package_layout.py`
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`

### Task 1: Lock the Ares lead models and county/source contracts

**Files:**
- Create: `app/models/ares.py`
- Create: `tests/domains/ares/test_models.py`
- Modify: `tests/test_package_layout.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.models.ares import AresCounty, AresLeadRecord, AresRunRequest, AresSourceLane


def test_counties_cover_the_five_target_markets() -> None:
    assert [county.value for county in AresCounty] == [
        "harris",
        "tarrant",
        "montgomery",
        "dallas",
        "travis",
    ]


def test_run_request_coerces_counties_and_defaults_to_briefs_and_drafts() -> None:
    request = AresRunRequest(counties=["harris", "travis"])
    assert request.counties == [AresCounty.HARRIS, AresCounty.TRAVIS]
    assert request.include_briefs is True
    assert request.include_drafts is True


def test_estate_of_detection_is_explicit_on_the_record() -> None:
    lead = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
    )
    assert lead.estate_of is True
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/domains/ares/test_models.py tests/test_package_layout.py -q
```

Expected: fail because the Ares model module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement the county enum, source lane enum, lead record, run request, and run response in `app/models/ares.py`. Keep the model set small, explicit, and serialization-friendly.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/domains/ares/test_models.py tests/test_package_layout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models/ares.py tests/domains/ares/test_models.py tests/test_package_layout.py
git commit -m "feat: add ares county and lead models"
```

### Task 2: Implement probate-first matching, tax overlays, and tiering

**Files:**
- Create: `app/services/ares_service.py`
- Create: `tests/services/test_ares_service.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.models.ares import AresCounty, AresLeadRecord, AresLeadTier, AresSourceLane
from app.services.ares_service import overlay_tax_delinquency, rank_ares_leads


def test_tax_overlay_marks_probate_leads_when_county_and_address_match() -> None:
    probate = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
    )
    tax = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.TAX_DELINQUENT_ESTATE_OF,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
        tax_delinquent=True,
        tax_amount_due=7123,
    )

    merged = overlay_tax_delinquency([probate], [tax])
    assert merged[0].tax_delinquent is True
    assert merged[0].tax_amount_due == 7123
    assert merged[0].estate_of is True


def test_rank_ares_leads_prioritizes_overlap_then_probate_then_tax_estate() -> None:
    probate_overlap = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
        tax_delinquent=True,
        tax_amount_due=7123,
        estate_of=True,
    )
    probate_only = AresLeadRecord(
        county=AresCounty.DALLAS,
        source_lane=AresSourceLane.PROBATE,
        property_address="44 Elm St, Dallas, TX",
        owner_name="Estate of John Smith",
    )
    tax_estate = AresLeadRecord(
        county=AresCounty.TRAVIS,
        source_lane=AresSourceLane.TAX_DELINQUENT_ESTATE_OF,
        property_address="88 River Rd, Austin, TX",
        owner_name="Estate of Maria Lopez",
        tax_delinquent=True,
        tax_amount_due=4888,
        estate_of=True,
    )

    ranked = rank_ares_leads([probate_only, tax_estate, probate_overlap])
    assert [item.tier for item in ranked] == [AresLeadTier.TIER_A, AresLeadTier.TIER_B, AresLeadTier.TIER_C]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/services/test_ares_service.py -q
```

Expected: fail because the matching and ranking functions do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement deterministic match keys, the probate overlay, and a simple tiering system. The rules should stay blunt:

- Tier A: probate + verified tax delinquent
- Tier B: probate only
- Tier C: tax-delinquent `estate of` lane

Also add the pipeline function that pulls county data from a source gateway, overlays tax delinquency, removes duplicate overlap records, and returns a ranked response.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/services/test_ares_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/ares_service.py tests/services/test_ares_service.py
git commit -m "feat: rank ares probate and tax leads"
```

### Task 3: Add lead briefs and outreach drafts

**Files:**
- Create: `app/services/ares_copy_service.py`
- Create: `tests/services/test_ares_copy_service.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.models.ares import AresCounty, AresLeadRecord, AresSourceLane
from app.services.ares_copy_service import build_lead_brief, build_outreach_drafts
from app.services.ares_service import RankedAresLead


def test_tier_a_brief_names_the_overlap_and_the_county() -> None:
    ranked = RankedAresLead(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
        estate_of=True,
        tax_delinquent=True,
        tax_amount_due=7123,
        source_id="probate-001",
        notes=["tax overlay matched"],
        confidence=1.0,
        tier="tier_a",
        score=100,
        reasons=["probate source", "verified tax delinquent"],
    )

    brief = build_lead_brief(ranked)
    assert brief.headline == "Tier A: probate + tax delinquent"
    assert "Harris County" in brief.summary
    assert brief.outreach_angle == "inheritance and property pressure"


def test_outreach_drafts_cover_sms_email_voicemail_and_direct_mail() -> None:
    ranked = RankedAresLead(
        county=AresCounty.DALLAS,
        source_lane=AresSourceLane.PROBATE,
        property_address="44 Elm St, Dallas, TX",
        owner_name="Estate of John Smith",
        estate_of=False,
        tax_delinquent=False,
        source_id="probate-002",
        notes=[],
        confidence=1.0,
        tier="tier_b",
        score=70,
        reasons=["probate source"],
    )

    drafts = build_outreach_drafts(ranked)
    assert [draft.channel for draft in drafts] == ["sms", "email", "voicemail", "direct_mail"]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/services/test_ares_copy_service.py -q
```

Expected: fail because the copy-generation module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create deterministic brief and outreach draft builders. Keep them template-based for now. No LLM dependency yet.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/services/test_ares_copy_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/ares_copy_service.py tests/services/test_ares_copy_service.py
git commit -m "feat: generate ares lead briefs and drafts"
```

### Task 4: Add the Ares API route and wire it into the app

**Files:**
- Create: `app/api/ares.py`
- Modify: `app/main.py`
- Create: `tests/api/test_ares_runtime.py`
- Modify: `tests/test_package_layout.py`

- [ ] **Step 1: Write the failing tests**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ares import get_ares_source_gateway, router as ares_router
from app.models.ares import AresCounty, AresLeadRecord, AresSourceLane
from app.services.ares_service import StaticAresSourceGateway

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client(gateway: StaticAresSourceGateway) -> TestClient:
    app = FastAPI()
    app.include_router(ares_router)
    app.dependency_overrides[get_ares_source_gateway] = lambda: gateway
    return TestClient(app)


def test_ares_run_returns_ranked_leads_and_drafts() -> None:
    gateway = StaticAresSourceGateway(
        probate_by_county={
            AresCounty.HARRIS: [
                AresLeadRecord(
                    county=AresCounty.HARRIS,
                    source_lane=AresSourceLane.PROBATE,
                    property_address="123 Main St, Houston, TX",
                    owner_name="Estate of Jane Doe",
                )
            ],
            AresCounty.TRAVIS: [
                AresLeadRecord(
                    county=AresCounty.TRAVIS,
                    source_lane=AresSourceLane.PROBATE,
                    property_address="88 River Rd, Austin, TX",
                    owner_name="Estate of Maria Lopez",
                )
            ],
        },
        tax_by_county={
            AresCounty.HARRIS: [
                AresLeadRecord(
                    county=AresCounty.HARRIS,
                    source_lane=AresSourceLane.TAX_DELINQUENT_ESTATE_OF,
                    property_address="123 Main St, Houston, TX",
                    owner_name="Estate of Jane Doe",
                    tax_delinquent=True,
                    tax_amount_due=7123,
                )
            ],
            AresCounty.TRAVIS: [],
        },
    )
    client = build_client(gateway)

    response = client.post(
        "/ares/run",
        json={"counties": ["harris", "travis"]},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counties"] == ["harris", "travis"]
    assert body["lead_count"] == 2
    assert body["leads"][0]["tier"] == "tier_a"
    assert body["leads"][0]["brief"]["headline"] == "Tier A: probate + tax delinquent"
    assert body["leads"][0]["drafts"][0]["channel"] == "sms"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/api/test_ares_runtime.py tests/test_package_layout.py -q
```

Expected: fail because the router, dependency, and Ares API wiring do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create a thin router at `app/api/ares.py`. It should accept a county list, pull records from the gateway dependency, run the Ares pipeline, and return the ranked response. Mount the router in `app/main.py`.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/api/test_ares_runtime.py tests/test_package_layout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/ares.py app/main.py tests/api/test_ares_runtime.py tests/test_package_layout.py
git commit -m "feat: add ares api runtime"
```

### Task 5: Update repo docs and memory with the merged phase-1 scope

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`

- [ ] **Step 1: Update the repo-facing docs**

Add the merged Ares runtime surface to the repo docs and update the router/memory notes so the next session understands that:

- Ares is a self-hosted operating system for distressed real-estate lead management
- probate is the primary lane
- tax delinquency is the overlay on probate
- tax-only work should focus on `estate of` properties
- outreach drafts are generated but not auto-sent
- this lead wedge is Phase 1 of a larger autonomy journey

- [ ] **Step 2: Run the relevant tests**

Run:

```bash
uv run pytest tests/api/test_ares_runtime.py tests/domains/ares/test_models.py tests/services/test_ares_service.py tests/services/test_ares_copy_service.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md CONTEXT.md memory.md
git commit -m "docs: align Ares repo notes with merged phase 1 scope"
```

**Exit criteria for Phase 1:**
Ares can find, rank, explain, and draft outreach for probate + tax-delinquent opportunities across the five counties with human approval before sending.

---

## Phase 2: Planner Agent

**What it is:**
Ares can understand a goal and turn it into a concrete execution plan, but it still does not do risky actions on its own.

**Responsibilities:**

- accept a goal like "find probate + tax-delinquent leads in Harris and Travis"
- choose the source lanes
- decide which checks to run
- produce a step-by-step plan
- explain why the plan makes sense
- ask for approval before any side-effecting action

**Files to create or modify:**

- Create: `app/models/ares_planning.py`
- Create: `app/services/ares_planner_service.py`
- Create: `app/api/ares_plans.py`
- Create: `tests/domains/ares_planning/test_planner_models.py`
- Create: `tests/services/test_ares_planner_service.py`
- Create: `tests/api/test_ares_plans.py`
- Modify: `app/main.py`
- Modify: `app/api/mission_control.py`
- Modify: `tests/test_package_layout.py`

**Allowed actions:**

- read data
- rank data
- summarize data
- generate drafts
- create human tasks

**Not allowed yet:**

- sending outbound messages automatically
- changing contracts
- opening escrow
- closing deals
- making irreversible external changes without approval

**Exit criteria:**
Ares can turn a goal into a structured plan that an operator can approve or reject in one glance.

---

## Phase 3: Bounded Executor

**What it is:**
Ares can execute safe, narrow steps without asking a human every time, but it still operates inside explicit limits.

**Responsibilities:**

- fetch county data
- normalize and dedupe records
- enrich records with available data
- run overlay matching
- produce ranked lead outputs
- generate drafts and task suggestions
- queue follow-up work

**Guardrails:**

- action budgets
- retry limits
- county / market scope limits
- approved tool allowlists
- audit trail for every action
- kill switch for operators

**Files to create or modify:**

- Create: `app/models/ares_execution.py`
- Create: `app/services/ares_execution_service.py`
- Create: `app/services/ares_policy_service.py`
- Create: `tests/services/test_ares_execution_service.py`
- Create: `tests/services/test_ares_policy_service.py`
- Modify: `app/services/ares_service.py`
- Modify: `app/api/ares.py`
- Modify: `app/api/mission_control.py`

**Exit criteria:**
Ares can execute a full lead-generation pass end-to-end inside a narrow scope. Failures are visible, recoverable, and interruptible.

---

## Phase 4: Semi-Autonomous Workflow Agent

**What it is:**
Ares runs an entire narrow playbook with human oversight at risky gates.

For real estate, this is where it starts to feel like an actual operator:

- choose county / market slice
- pull probate and tax signals
- enrich and score leads
- generate outreach
- create follow-up tasks
- monitor responses
- suggest next actions

**Responsibilities:**

- own a workflow from intake to next-best-action
- maintain state across steps
- remember what already happened
- handle retries and fallbacks
- surface exceptions instead of silently dropping them

**Guardrails:**

- human approval before send / contract / disposition actions
- policy checks on every high-risk step
- drift detection
- evaluation after each run
- operator-visible rationale for major decisions

**Files to create or modify:**

- Create: `app/models/ares_workflows.py`
- Create: `app/services/ares_playbook_service.py`
- Create: `app/services/ares_state_service.py`
- Create: `app/services/ares_eval_service.py`
- Create: `tests/services/test_ares_playbook_service.py`
- Create: `tests/services/test_ares_state_service.py`
- Create: `tests/services/test_ares_eval_service.py`
- Modify: `app/services/ares_execution_service.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`

**Exit criteria:**
Ares can run a narrow county workflow repeatedly with low operator overhead. Outputs are consistent enough to trust, and failures are explainable and testable.

---

## Phase 5: Guardrailed Autonomous Operator

**What it is:**
Ares can operate with minimal supervision inside approved boundaries.

This is the point where it is more than an assistant and more than a workflow engine. It is a real operator with limits.

**Responsibilities:**

- pick up approved objectives
- execute playbooks
- monitor results
- adapt within bounds
- escalate only when needed
- keep a full record of what it did and why

**Guardrails that stay in place:**

- no free-form spending
- no unbounded outreach
- no contract signing without policy gates
- no silent escalations
- no cross-market sprawl without scope change

**Files to create or modify:**

- Create: `app/models/ares_agent_registry.py`
- Create: `app/services/ares_agent_registry_service.py`
- Create: `app/services/ares_memory_service.py`
- Create: `app/services/ares_eval_loop_service.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `app/main.py`
- Modify: `tests/api/test_mission_control_phase3.py`

**Exit criteria:**
Ares can run a bounded business objective with minimal supervision. Operators trust the logs, decisions, and exceptions.

---

## Cross-Cutting Systems Required for Every Phase

### 1) Agent Registry
Ares needs versioned agents, not one mutable blob.

Each agent should have:

- name
- purpose
- revision
- allowed tools
- risk policy
- output contract
- active revision

### 2) Durable Memory
Ares needs state that survives past a single run.

That state should capture:

- market preferences
- county defaults
- lead history
- outreach history
- operator decisions
- outcomes
- exceptions

### 3) Tool Policy
Every tool call should be deterministic and auditable.

That means:

- explicit allowlists
- typed inputs and outputs
- no magical side effects
- hard approvals for risky calls

### 4) Evaluation Loop
Autonomy without evaluation is improvisation with a budget.

Ares should measure:

- lead quality
- response quality
- conversion quality
- false positives
- duplicate work
- operator corrections

### 5) Mission Control Visibility
Operators need to see:

- current phase
- active run
- pending approvals
- failed steps
- lead quality
- confidence
- what the agent is about to do next

---

## Recommended Execution Order

1. Finish Phase 1 first.
2. Add planner mode.
3. Add bounded execution.
4. Add workflow memory and evaluation.
5. Expand autonomy one lane at a time.

Do not skip the boring phases. Boring is how this stops being cosplay.

---

## Risks and Gaps That Must Be Explicit

- Data source specifics for counties and tax/probate feeds
- Canonical lead schema and dedupe rules
- Data quality / validation for messy county records
- Compliance review for probate outreach and tax-delinquent marketing
- Unit economics and spend controls
- Approval scaling once the agent starts doing more work
- Testing / replay strategy for full workflows
- Failure modes for source outages and provider rate limits
- Observability and alerting for autonomous runs
- Rollback plan for any auto-executed action
- Multi-tenancy / multi-market boundaries
- Disaster recovery for autonomous operation
- Human intervention protocol when things drift

---

## Self-Review Checklist

Before handing this to the next implementer, verify:

1. The old MVP and autonomy docs are fully merged here.
2. Phase 1 is the probate + tax-delinquent wedge, not a separate side project.
3. The five counties are explicitly named.
4. Probate-first + tax overlay is the governing rule.
5. `estate of` is the tax-only source filter.
6. Human approval is still required in Phase 1.
7. Planner, bounded executor, workflow agent, and guardrailed operator phases are all present.
8. Every phase has concrete exit criteria.
9. Every phase points to actual repo files or modules that can be created or modified.
10. No phase quietly sneaks in auto-send / contract / dispo behavior too early.
