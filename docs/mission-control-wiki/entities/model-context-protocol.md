---
title: Model Context Protocol
created: 2026-04-13
updated: 2026-04-13
type: entity
tags: [protocol, tool, integration, architecture]
sources:
  - raw/articles/2026-04-13-anthropic-mcp-intro.md
---

# Model Context Protocol

MCP is the tool bridge. Use it when an agent needs standardized access to external systems: files, APIs, databases, internal tools, or vendor services.

In Hermes:
- MCP belongs in the adapter layer.
- MCP should power tool access, not control-plane policy.
- It pairs with A2A: [[a2a-protocol]] handles agent collaboration, MCP handles tool access.

Why Hermes cares:
- Avoid bespoke one-off integrations everywhere.
- Keep tools swappable.
- Make agent behavior consistent across different providers.

Related pages:
- [[agent-to-agent-architecture]]
- [[mcp-vs-a2a]]
- [[agentic-first-command-center]]