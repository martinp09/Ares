---
title: Control Plane vs CRM
created: 2026-04-13
updated: 2026-04-13
type: comparison
tags: [comparison, control-plane, crm, mission-control, architecture]
sources:
  - raw/articles/2026-04-13-microsoft-ai-strategy.md
  - raw/articles/2026-04-13-github-agentic-workflows.md
  - raw/articles/2026-04-13-openai-agents-sdk.md
---

# Control Plane vs CRM

A CRM is usually a record system with workflows attached.
A control plane is a system that can govern, deploy, monitor, and recover agents and business actions.

For Hermes, the right answer is control plane first.

| Dimension | CRM | Hermes Control Plane |
|---|---|---|
| Source of truth | Usually vendor-owned objects and workflows | Hermes-owned state and policy |
| Main value | Sales pipeline visibility | Agentic execution + operator control |
| Automation | Attached workflows | Native orchestration and approvals |
| Observability | Often activity logs | Runs, artifacts, events, transcripts, inboxes |
| Flexibility | Vendor constrained | Protocol-driven and swappable |

Why this matters:
- A CRM can be a sink, but it should not own the future operating model.
- Hermes should own the control plane and optionally sync out later.
- This is why the UI should be native to Hermes and not a separate product.

Related pages:
- [[agentic-first-command-center]]
- [[mission-control-ui]]
- [[ai-first-platform-criteria]]