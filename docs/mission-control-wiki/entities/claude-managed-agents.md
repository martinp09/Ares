---
title: Claude Managed Agents
created: 2026-04-13
updated: 2026-04-13
type: entity
tags: [claude, managed-agents, orchestration, permissions, evaluation, multiagent]
sources:
  - raw/articles/2026-04-13-claude-managed-agents.md
---

# Claude Managed Agents

Claude Managed Agents is a strong reference model for Hermes because it packages an agent as a versioned configuration with explicit environment, session, tool, and skill boundaries.

Current branch note: Hermes now mirrors the same shape in its managed-agent scaffold so the runtime can grow without turning into a chat-only console.

What matters most for Hermes:
- versioned agent configs with a stable agent ID
- agent vs environment separation
- session/thread isolation for delegated work
- permission policies for tool execution
- event streams for visibility
- outcomes and rubrics for evaluation loops

What not to copy directly:
- any Claude-specific product flow that duplicates Trigger.dev
- any dependency on their managed environment instead of Hermes-native orchestration
- any UI pattern that drifts back toward a separate chat-only agent console

Related pages:
- [[managed-agent-runtime-patterns]]
- [[agentic-first-command-center]]
- [[ai-first-platform-criteria]]