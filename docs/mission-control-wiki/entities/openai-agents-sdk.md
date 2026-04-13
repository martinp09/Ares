---
title: OpenAI Agents SDK
created: 2026-04-13
updated: 2026-04-13
type: entity
tags: [agentic, orchestration, workflow, observability, voice]
sources:
  - raw/articles/2026-04-13-openai-agents-sdk.md
---

# OpenAI Agents SDK

The SDK is useful as a reference architecture for how a production agent stack should be organized: agent definitions, orchestration, guardrails, results/state, integrations, observability, and voice agents.

Hermes takeaways:
- Agents need explicit orchestration, not just prompts.
- Guardrails belong at the runtime boundary.
- Observability and tracing must be first-class.
- Voice is part of the stack, not a separate novelty feature.

Related pages:
- [[agentic-first-command-center]]
- [[ai-first-platform-criteria]]
- [[agent-to-agent-architecture]]