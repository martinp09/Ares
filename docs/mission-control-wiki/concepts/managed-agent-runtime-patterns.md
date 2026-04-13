---
title: Managed Agent Runtime Patterns
created: 2026-04-13
updated: 2026-04-13
type: concept
tags: [managed-agents, runtime, versioning, permissions, evaluation, sessions]
sources:
  - raw/articles/2026-04-13-claude-managed-agents.md
  - raw/articles/2026-04-13-openai-agents-sdk.md
  - raw/articles/2026-04-13-github-agentic-workflows.md
---

# Managed Agent Runtime Patterns

This note extracts the reusable patterns Hermes should carry forward from Claude Managed Agents and similar agent runtimes.

## 1. Versioned agent identity
An agent should be a versioned artifact, not a mutable prompt fragment.

Hermes implication:
- store an agent registry
- keep a stable agent ID
- allow revisions without losing historical runs
- make production launches reference a published revision

## 2. Environment and session separation
The runtime environment is not the same thing as the agent definition.
The session is the live execution instance.

Hermes implication:
- separate configuration from execution
- keep the environment as an operational substrate
- keep sessions isolated so delegated work does not blur contexts

## 3. Explicit permission policies
Tools should be governed by policy, not implicit trust.

Hermes implication:
- mark actions as always allow, always ask, or forbidden
- surface risky actions for approval
- keep custom integrations under Hermes control

## 4. Event streams instead of silent black boxes
Agent execution should produce a visible timeline of state transitions.

Hermes implication:
- emit run started / tool called / tool finished / run completed / run failed events
- expose live operator visibility
- make replay and audit trails straightforward

## 5. Outcomes and rubrics
A good agent loop knows what done looks like and can grade itself against it.

Hermes implication:
- define outcome artifacts explicitly
- attach rubrics to quality-sensitive tasks
- add a separate evaluator context for QC
- iterate until the rubric is satisfied or escalation is required

## 6. Delegation with isolated threads
Specialist work should happen in isolated threads with a coordinator.

Hermes implication:
- let a coordinator dispatch specialist agents
- keep the handoff log visible
- preserve prior thread state for follow-up
- avoid mixing contexts across unrelated subagents

Related pages:
- [[claude-managed-agents]]
- [[agentic-first-command-center]]
- [[ai-first-platform-criteria]]