---
title: AI-First Platform Criteria
created: 2026-04-13
updated: 2026-04-13
type: concept
tags: [architecture, evaluation, security, observability, automation, integration]
sources:
  - raw/articles/2026-04-13-microsoft-ai-strategy.md
  - raw/articles/2026-04-13-github-agentic-workflows.md
  - raw/articles/2026-04-13-openai-agents-sdk.md
---

# AI-First Platform Criteria

If Hermes is going to be built for the next phase of the market, it should optimize for these criteria:

- agent deployment, not just prompting
- interoperability, not lock-in
- observability, not black-box behavior
- security and scoped permissions, not broad ambient access
- approvals and policy, not unchecked autonomy
- durable state and replayability, not ephemeral chat
- operator visibility, not hidden background magic
- tool abstraction, not one-off integrations
- agent-to-agent collaboration, not single-agent bottlenecks

Microsoft-style governance + GitHub-style guardrails + OpenAI-style orchestration + Claude-style managed agents give a useful north star for what Hermes should become.

Related pages:
- [[agentic-first-command-center]]
- [[mission-control-ui]]
- [[github-agentic-workflows]]
- [[managed-agent-runtime-patterns]]
- [[claude-managed-agents]]
- [[agent-to-agent-architecture]]