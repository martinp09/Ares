---
title: "Ares CRM Control Plane"
created: 2026-04-25
updated: 2026-04-25
type: concept
tags: [ares, crm, control-plane, mission-control, real-estate, agents]
sources:
  - ../raw/articles/2026-04-25-ghl-datasift-crm-research.md
---

# Ares CRM Control Plane

Ares should become a CRM-backed control plane for a real-estate operating business.

The CRM layer owns durable business state: owners, properties, contacts, opportunities, pipelines, stages, tasks, activities, communications, files, and research sources.

The control-plane layer owns execution: agents, runs, approvals, provider callbacks, audit, replay, release state, and operator supervision.

The Mission Control UI should merge those layers into one working system.

## Product Spine

1. **Research creates source records.**
   - county data, SiftMap-style pulls, uploaded lists, owner/property lookups, web research, and agent findings enter as raw evidence-backed source records.

2. **Source records resolve into the CRM graph.**
   - owners, properties, contacts, companies/trusts/estates, phone numbers, email addresses, and mailing addresses stay separate but linked.

3. **Qualified work becomes opportunities.**
   - opportunities are the moving business process, not the raw property or the owner.

4. **Pipelines and stages govern motion.**
   - stage transitions trigger tasks, reminders, agent runs, follow-up, approvals, and reporting.

5. **Activities explain what happened.**
   - calls, texts, emails, agent runs, imports, exports, skip traces, direct mail, notes, stage moves, and provider events are normalized into timeline read models.

6. **Agents operate through the CRM.**
   - agents spawn research, enrichment, follow-up drafting, task creation, and status movement through typed commands with human approval where risk requires it.

## Core Rule

Do not flatten the real-estate model into "contacts." Ares needs four separate but linked primitives:

- **Owner:** legal or human decision-maker.
- **Property:** asset and address.
- **Contact:** reachable person/channel entry.
- **Opportunity:** active business process.

## MVP Workflow

1. Operator opens dashboard.
2. Dashboard shows priority cards: stale hot leads, due tasks, failed provider events, new replies, research gaps, agent runs needing approval.
3. Operator opens pipeline board.
4. Board shows configurable stages for inbound lease-option and outbound probate lanes.
5. Operator opens an opportunity.
6. Opportunity detail shows linked owner, property, contacts, timeline, notes, tasks, agent findings, and next best action.
7. Operator can spawn an agent from the detail page with scoped context.
8. Agent creates research findings and proposed actions.
9. Human approves high-risk actions before outreach, provider changes, or irreversible state changes.
10. Every action writes to the timeline.

## Build Order

1. CRM graph and configurable pipeline foundation.
2. Opportunity board and detail workspace.
3. Multi-entity tasks, reminders, and activity timeline.
4. Agent workbench embedded into CRM records.
5. Owner/property research cockpit.
6. Map-backed research and farm-area acquisition.

Related:
- [[mission-control-ui]]
- [[control-plane-vs-crm]]
