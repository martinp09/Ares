---
title: Enterprise Agent Governance
created: 2026-04-15
updated: 2026-04-25
type: concept
tags: [governance, approvals, audit, agents, enterprise, mission-control]
sources:
  - ../../superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md
  - ../../superpowers/specs/2026-04-15-agent-platform-product-model.md
---

# Enterprise Agent Governance

Enterprise governance should attach to agents and agent revisions, not to UI apps.

What needs governance:
- who can create, publish, archive, clone, and run an agent
- which skills an agent can bind to
- which host adapter a revision can execute on
- which actions are always allowed, approval-gated, or forbidden
- which sessions, runs, artifacts, and outcomes are visible to operators

Mission Control is the operator cockpit for that governance. It should expose approvals, run state, session history, artifacts, and operator intervention without redefining the product model.

Current branch note: governance seams exist through revisions, sessions, permissions, outcomes, assets, and Mission Control read models. Production Ares now runs with Supabase-backed runtime state and live provider wiring; remaining governance hardening is monitoring, alerting, and deeper operator workflow polish.

Related pages:
- [[agent-platform-product-model]]
- [[managed-agent-runtime-patterns]]
- [[agentic-first-command-center]]
- [[ai-first-platform-criteria]]
