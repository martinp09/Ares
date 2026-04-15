# Claude Managed Agents

URL: https://platform.claude.com/docs/en/managed-agents/quickstart

Key references:
- https://platform.claude.com/docs/en/managed-agents/quickstart
- https://platform.claude.com/docs/en/managed-agents/agent-setup
- https://platform.claude.com/docs/en/managed-agents/permission-policies
- https://platform.claude.com/docs/en/managed-agents/multi-agent
- https://platform.claude.com/docs/en/managed-agents/define-outcomes

Key points:
- An agent is a reusable, versioned configuration composed of model, system prompt, tools, MCP servers, and skills.
- An environment is a configured container template with packages and network access.
- A session is a running agent instance inside an environment.
- Events are the messages and status updates exchanged between the application and the agent.
- Permission policies control whether server-executed tools run automatically or wait for approval.
- Multiagent sessions use isolated threads so a coordinator can delegate specialized work without mixing context.
- Outcomes attach a rubric and a separate grader context so the agent can iterate until the artifact satisfies the requirements.

Hermes takeaways:
- Treat the agent definition as a versioned asset, not an ad hoc prompt blob.
- Keep runtime environment concerns separate from agent identity.
- Expose thread/session boundaries so delegation stays coherent.
- Use explicit permission policies for risky tools.
- Build QC loops around outcomes and rubrics instead of eyeballing output.
- Stream events so the operator can see what the agent is doing in real time.