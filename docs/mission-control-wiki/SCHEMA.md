# Wiki Schema

## Domain
Hermes Mission Control: AI-first command center architecture, agent orchestration, comms/inbox visibility, and backend control-plane design.

## Conventions
- File names: lowercase, hyphens, no spaces.
- Every wiki page starts with YAML frontmatter.
- Use [[wikilinks]] with at least 2 outbound links per page.
- Update `updated` on every content change.
- Add every new page to `index.md`.
- Append every ingest/update batch to `log.md`.
- Raw source captures in `raw/` are immutable after creation.

## Frontmatter
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
---

## Tag Taxonomy
- architecture
- agentic
- agent-to-agent
- control-plane
- command-center
- mission-control
- orchestration
- workflow
- protocol
- tool
- ui
- inbox
- comms
- voice
- sms
- approval
- observability
- security
- comparison
- vendor
- evaluation
- memory
- automation
- crm
- integration

## Page Thresholds
- Create a page when an entity/concept is central to the research.
- Add to an existing page when it fits an existing topic.
- Avoid pages for passing mentions.
- Split pages over ~200 lines.

## Update Policy
- Prefer newer sources for current platform direction.
- If sources conflict, keep both claims and note the contradiction.
- Mark contradictions in frontmatter and flag them in `log.md`.