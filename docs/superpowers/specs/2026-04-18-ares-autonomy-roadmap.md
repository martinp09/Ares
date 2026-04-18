# Ares Autonomy Roadmap

## Summary

Ares is not becoming a full autonomous operator in one shot. It is becoming one in phases.

The right shape is:

- keep the deterministic runtime and control plane as the backbone
- add agentic planning on top of it
- then let Ares execute bounded tools
- then let it run narrow workflows with guardrails
- only later widen autonomy across markets and lead types

The current probate + tax-delinquent MVP is the first real vertical slice. This roadmap explains how that slice evolves into an autonomous real-estate agent over time.

## Goal

Turn Ares into a phased autonomous real-estate operator that can:

- choose a market or county slice
- find and rank leads
- draft outreach
- execute bounded actions with guardrails
- learn from outcomes
- expand autonomy without losing control

## Core Principle

Autonomy should grow from the inside out:

1. **deterministic control plane**
2. **planner**
3. **bounded executor**
4. **workflow agent**
5. **guardrailed autonomous operator**

Do not jump straight to full autonomy. That is how you build expensive chaos.

## Current Baseline

Ares already has the right foundation in this repo:

- typed commands and policy classification
- approvals and run records
- replay-safe lifecycle handling
- Mission Control surfaces
- a stable runtime / tool boundary
- the probate + tax-delinquent lead wedge

That means Ares does *not* need a rewrite. It needs an autonomy layer on top of the current runtime.

## Phase 0: Assistant and Lead Machine

**What it is:**
Ares finds leads, ranks them, and drafts outreach. Humans still approve the important stuff.

**Current behaviors:**

- pull probate leads
- overlay tax delinquency
- prioritize probate + tax delinquent overlaps
- separately screen tax-delinquent `estate of` properties
- generate lead briefs
- generate SMS / email / voicemail / direct-mail drafts

**Autonomy level:**
None. This is still human-led.

**Exit criteria for Phase 0:**

- lead sourcing works across the target counties
- lead ranking is deterministic
- outreach drafts are useful enough that an operator would actually use them
- the operator can review the entire result without hunting through raw data

## Phase 1: Planner Agent

**What it is:**
Ares can understand a goal and turn it into a concrete plan, but it does not yet execute risky actions on its own.

**Responsibilities:**

- accept a goal like "find probate + tax-delinquent leads in Harris and Travis"
- choose the correct source lanes
- decide which checks to run
- produce a step-by-step execution plan
- explain why the plan makes sense
- ask for approval before any side-effecting action

**Allowed actions:**

- read data
- rank data
- summarize data
- generate drafts
- create tasks for humans

**Not allowed yet:**

- sending outbound messages automatically
- changing contracts
- opening escrow
- closing deals
- making irreversible external changes without approval

**Needed repo capabilities:**

- a planner output schema
- explicit task decomposition
- Mission Control view for proposed plans
- per-plan confidence and scope metadata

**Exit criteria:**

- Ares can turn a user goal into a structured plan
- the plan is understandable by an operator in under a minute
- the operator can approve or reject the plan cleanly

## Phase 2: Bounded Executor

**What it is:**
Ares can execute safe, narrow steps without asking a human every time, but it still operates inside hard limits.

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

**Not allowed yet:**

- auto-send without policy
- contract execution
- escrow handoff
- disposition automation
- changing strategy without explicit scope update

**Needed repo capabilities:**

- durable task state
- action provenance
- execution logs tied to runs
- confidence thresholds for tool calls
- better Mission Control visibility into each step

**Exit criteria:**

- Ares can execute a full lead-generation pass end-to-end inside a narrow scope
- failures are visible and recoverable
- the operator can interrupt or override at any point

## Phase 3: Semi-Autonomous Workflow Agent

**What it is:**
Ares runs an entire narrow playbook with human oversight at the risky gates.

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

**Needed repo capabilities:**

- revisioned agent registry
- durable memory/state model
- run summaries and step traces
- evaluation harness for workflow outcomes
- Mission Control views for autonomy status and exceptions

**Exit criteria:**

- Ares can run a narrow county workflow repeatedly with low operator overhead
- outputs are consistent enough to trust
- failures are explainable and testable
- the system improves from results instead of just repeating the same mistakes

## Phase 4: Guardrailed Autonomous Operator

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

**Guardrails that still stay in place:**

- no free-form spending
- no unbounded outreach
- no contract signing without policy gates
- no silent escalations
- no cross-market sprawl without scope change

**Needed repo capabilities:**

- strong policy engine
- per-action budget and scope controls
- rollback / replay support
- durable memory and outcome learning
- operator override on every mission

**Exit criteria:**

- Ares can run a bounded business objective with minimal supervision
- operators trust its logs, decisions, and exceptions
- it improves over time without becoming opaque

## Cross-Cutting Systems Required for Every Phase

### 1) Agent Registry
Ares needs versioned agents, not one giant mutable blob.

Each agent should have:

- a name
- a purpose
- a revision
- allowed tools
- risk policy
- output contract
- current active revision

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
Autonomy without evaluation is just improvisation with a budget.

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

## Recommended Sequence

1. **Finish the current probate + tax-delinquent MVP**
   - keep it deterministic
   - keep it human-approved
   - make it actually useful

2. **Add planner mode**
   - Ares proposes execution steps before it acts

3. **Add bounded execution**
   - Ares can do safe steps on its own

4. **Add workflow memory and evaluation**
   - Ares learns from actual outcomes

5. **Expand autonomy one lane at a time**
   - only after the previous lane is boringly reliable

## Blunt Recommendation

Do not try to build "the autonomous real estate agent" as a single monolith.

Build:

- a good lead machine first
- a planner next
- a bounded executor after that
- then a semi-autonomous workflow agent
- then the full operator

That path is slower on a slide deck and faster in real life. Which is usually the part people get wrong.
