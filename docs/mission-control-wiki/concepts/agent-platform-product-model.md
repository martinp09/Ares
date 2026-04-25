---
title: Agent Platform Product Model
created: 2026-04-15
updated: 2026-04-25
type: concept
tags: [agents, product-model, runtime, host-adapters, mission-control]
sources:
  - ../../superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md
  - ../../superpowers/specs/2026-04-15-agent-platform-product-model.md
---

# Agent Platform Product Model

Ares should be described as an agent platform, not as a collection of apps.

The model is:
- agents are the product unit
- agent revisions are the deployable release
- skills are reusable procedures
- host runtimes are adapters
- Mission Control is the operator cockpit
- apps are operator surfaces, not the product unit

Current branch note: Trigger.dev is the active execution infrastructure, but it is not the platform identity. Supabase-backed production wiring is live for the runtime/provider lanes proven in `docs/rollout-evidence/production-2026-04-25.json`; local development can still use memory-backed stores.

Related pages:
- [[agentic-first-command-center]]
- [[managed-agent-runtime-patterns]]
- [[enterprise-agent-governance]]
- [[mission-control-ui]]
