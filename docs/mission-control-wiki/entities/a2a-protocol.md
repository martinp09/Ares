---
title: A2A Protocol
created: 2026-04-13
updated: 2026-04-13
type: entity
tags: [agent-to-agent, protocol, architecture, integration]
sources:
  - raw/articles/2026-04-13-a2a-protocol.md
  - raw/articles/2026-04-13-google-a2a-blog.md
---

# A2A Protocol

A2A is the emerging standard for agent-to-agent communication. In Hermes terms, it is what you reach for when one agent needs to hand off work, request help, or collaborate with another agent that may run in a different framework or vendor stack.

Why it matters:
- Hermes is not only coordinating tools; it is coordinating workers.
- A2A gives Hermes a clean inter-agent communication layer.
- It complements [[model-context-protocol]] rather than replacing it.

Hermes focus:
- Define when an internal task becomes an agent handoff.
- Preserve identity, authorization, and traceability across agent boundaries.
- Make inter-agent messages visible in [[mission-control-ui]].

Related pages:
- [[agent-to-agent-architecture]]
- [[mcp-vs-a2a]]
- [[ai-first-platform-criteria]]