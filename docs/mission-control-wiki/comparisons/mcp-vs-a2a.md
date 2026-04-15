---
title: MCP vs A2A
created: 2026-04-13
updated: 2026-04-13
type: comparison
tags: [comparison, protocol, agent-to-agent, integration, tool]
sources:
  - raw/articles/2026-04-13-anthropic-mcp-intro.md
  - raw/articles/2026-04-13-a2a-protocol.md
  - raw/articles/2026-04-13-google-a2a-blog.md
---

# MCP vs A2A

These are complementary, not competing layers.

| Dimension | MCP | A2A |
|---|---|---|
| Primary purpose | Tool/context access | Agent collaboration |
| Who talks to whom | Agent to tools/services | Agent to agent |
| Best for | APIs, files, data sources, internal utilities | Delegation, handoffs, specialist coordination |
| Hermes use | Give agents standard tools | Let agents cooperate across boundaries |

Rule of thumb:
- If an agent needs a tool, use [[model-context-protocol]].
- If an agent needs another agent, use [[a2a-protocol]].
- If Mission Control needs both, wire both in and keep them visible in [[mission-control-ui]].

Related pages:
- [[agent-to-agent-architecture]]
- [[agentic-first-command-center]]