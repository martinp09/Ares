---
title: Mission Control UI
created: 2026-04-13
updated: 2026-04-13
type: concept
tags: [ui, inbox, comms, observability, mission-control, control-plane]
sources:
  - raw/articles/2026-04-13-github-agentic-workflows.md
  - raw/articles/2026-04-13-openai-agents-sdk.md
---

# Mission Control UI

The UI should be the operator cockpit for Hermes, not a separate CRM clone.

What it needs on day one:
- inbox / conversation view
- lead and contact context
- call and message history
- approvals queue
- run timeline
- live agent status
- sequence enrollment state
- exceptions / retries
- a way to launch or supervise agents

The UI should render what Hermes knows, not invent its own truth.
It should make it easy to intervene when agents need help and easy to trust the system when they do not.

Related pages:
- [[agentic-first-command-center]]
- [[control-plane-vs-crm]]
- [[ai-first-platform-criteria]]