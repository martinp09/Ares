# Hermes Mission Control Architecture Design

> Native Mission Control inside Hermes Central Command. FastAPI remains the backend. React/TypeScript is the frontend. The system is AI-first, agentic-first, and designed for inbox visibility, approvals, orchestration, and multi-agent delegation.

## Goal

Build a native Mission Control experience inside Hermes Central Command that becomes the operator cockpit for the business: a single place to see conversations, calls, leads, sequences, agent runs, approvals, and system status, while also allowing Hermes to deploy, supervise, and recover agents.

## Architecture Summary

Hermes Central Command stays the control plane and source of truth. The backend remains FastAPI. The frontend is a React/TypeScript app inside the same repo, not a separate product. Trigger.dev handles durable jobs, delayed sequences, retries, and background orchestration. Supabase stores canonical state. Twilio and Vapi remain transport/provider layers. MCP is the tool bridge. A2A is the agent-to-agent communication layer.

Implementation status:
- The current branch already ships the Mission Control read models and native shell scaffold from phase 6.
- Supabase remains the canonical target, but live wiring is still deferred on this machine.

Rust is not the primary stack for this phase. It may be introduced later for narrow performance-critical workers or adapters only if profiling proves it is necessary.

## Benchmark-Informed Product Direction

The research set points to six useful product patterns:

| Company | What to steal | Hermes implication |
|---|---|---|
| Ramp Labs | Productized experiments and visible AI surfaces | Mission Control should ship named, visible agent experiences instead of vague AI features |
| Sierra | One agent across chat, SMS, WhatsApp, email, voice, ChatGPT | Hermes should be channel-aware and comms-first, not chat-only |
| Cognition AI | AI teammate for a single valuable job | Hermes should deploy specialist agents with bounded responsibility |
| Harvey AI | Domain-specific workflow agents grounded in sources | Hermes should support deep vertical workflows and source-grounded outputs |
| Glean | Search + assistant + agents + governance | Hermes should unify knowledge, action, and governance in one command surface |
| Claude Managed Agents | Versioned agent configs, isolated sessions, permission policies, outcome/rubric loops | Hermes should treat agents as versioned runtime packages with explicit environments and QC loops |

The strategic takeaway is that Mission Control should feel like an operator cockpit with real workflows and named agent surfaces, not a generic CRM or a generic chat dashboard.

Claude Managed Agents adds a second important lesson: Hermes should treat each agent as a versioned runtime package, not as an ad hoc prompt. That implies explicit environment separation, session/thread isolation, permission policies, and rubric-driven evaluation loops.

## Core Principles

1. Native, not separate
- Mission Control must live inside Hermes Central Command.
- It should share identity, state, approvals, and runtime surfaces with Hermes.
- No parallel CRM backend and no detached dashboard app.

2. Agentic-first
- The UI is not just a reporting screen.
- The system must deploy agents, route work to agents, supervise runs, and recover from failures.
- The operator should be able to see what agents are doing and intervene when needed.

3. Control plane before CRM
- Hermes owns the command surface, policy, orchestration, and audit trail.
- External CRMs may be optional sync targets later, but not the source of truth.

4. Tool access vs agent collaboration
- Use MCP for external tool access.
- Use A2A for agent-to-agent handoffs and delegation.
- Do not blur these layers.

5. Visibility over magic
- Every meaningful action should appear in the dashboard, logs, or run history.
- Background automation must be observable and replayable.

6. Domain-specific agent surfaces
- Mission Control should support named, bounded agent experiences.
- Do not collapse everything into one general-purpose assistant.
- Product surfaces should map to jobs: inbox, calls, sequences, approvals, runs, search, launch.

## System Boundaries

### Hermes Backend, FastAPI
Hermes backend owns:
- tenant/business scoping
- command ingestion
- approvals and policy gates
- run creation and status updates
- event and artifact logging
- contact and conversation identity
- lead state and pipeline state
- agent deployment requests
- provider adapter orchestration
- webhook normalization for SMS/calls/email/events
- read APIs for the dashboard

### Mission Control UI, React/TypeScript
The UI owns:
- operator cockpit layout
- inbox and thread visualization
- call/message timeline visualization
- lead and contact detail panes
- approvals queue
- run timeline and exception queue
- pipeline board and sequence monitor
- agent launcher and agent supervision surface
- search, filters, and queue management

### Trigger.dev
Trigger.dev owns:
- scheduled nurture sequences
- delayed follow-ups
- retries
- long-running background tasks
- fan-out/fan-in orchestration
- automation steps that should survive process restarts

### Supabase
Supabase owns:
- canonical persistence
- realtime-friendly projections where useful
- RLS-enforced tenant data
- audit-oriented tables for commands, runs, tasks, artifacts, events, contacts, conversations, messages, calls, and sequence enrollment

### Provider Layers
Twilio and Vapi own transport and execution only:
- Twilio: SMS, phone numbers, inbound/outbound telephony plumbing
- Vapi: conversational voice agent execution, transcripts, call summaries, tool calls
- Neither should be the system of record

## Repo Layout Direction

The implementation should keep a clean monorepo-style shape inside the existing repo:

- `app/` — FastAPI backend and business logic
- `apps/mission-control/` — React/TypeScript Mission Control app
- `trigger/` — Trigger.dev jobs and orchestration
- `supabase/` — schema, migrations, and database config
- later optional `packages/` only if shared code becomes necessary

## What Goes Where

### Backend responsibilities
- validate all inbound commands
- decide whether an action is autonomous or approval-required
- create run records and task records
- persist events, transcripts, messages, and call summaries
- dispatch jobs to Trigger.dev
- expose read models for the UI
- enforce business rules, guardrails, and tenant boundaries
- own the agent registry and handoff rules

### UI responsibilities
- show the truth the backend already knows
- make it obvious what is happening right now
- let the operator inspect, approve, retry, pause, resume, and launch
- show the life of a lead or conversation in one place
- present a dashboard that feels like a cockpit, not a CRM clone

### Trigger.dev responsibilities
- wait, retry, schedule, continue, and branch
- do not become the source of truth for business state
- do not own the UI
- do not own policy decisions

### Rust responsibilities
- defer for now
- only consider later for focused performance work such as parsers, batch processors, or high-throughput workers

## Data Model Shape

The spec assumes Hermes will expose and persist these core objects:

- Businesses / tenants
- Commands
- Approvals
- Runs
- Tasks
- Artifacts
- Events
- Contacts
- Conversations
- Messages
- Calls
- Sequences / enrollment state
- Agent registry / agent runs

These objects must support:
- tenant isolation
- timestamps
- status transitions
- replayability
- traceability
- linking from lead -> conversation -> message/call -> run -> artifact

## Mission Control UI Surfaces

### 1. Global dashboard
The landing page should answer:
- what is happening right now
- what needs approval
- what is stuck
- what just completed
- what agents are currently running
- what conversations need attention

### 2. Inbox
A three-pane or comparable high-density layout:
- left: inbox / lead list / queue
- center: conversation thread and activity timeline
- right: lead detail, status, tags, sequence state, and next actions

### 3. Call center view
- inbound and outbound calls
- call state and transcript
- recording link if available
- Vapi tool-call events
- outcomes and follow-up actions

### 4. Approvals queue
- show commands needing approval
- show why they need approval
- allow approve / reject / annotate

### 5. Runs and agents view
- active runs
- failed runs
- retriable work
- agent registry
- agent-to-agent handoffs
- run artifacts and logs

### 6. Pipeline / nurture view
- sequence enrollment
- step progress
- delay timers
- retries
- branching outcomes

### 7. Search and command palette
- search across people, leads, conversations, commands, runs, and artifacts
- launch common actions without hunting through menus
- support agent launch and operator shortcuts

## Agent-First Workflow Rules

1. Operator intent becomes a typed command.
2. The backend evaluates policy.
3. If allowed autonomously, Hermes creates a run and dispatches work.
4. If approval is required, the UI surfaces the approval request.
5. Trigger.dev executes long-running or delayed steps.
6. Provider callbacks write back into Hermes.
7. The UI reflects state changes from Hermes, not from provider-specific logic.

## Voice and SMS Flow

### SMS
- inbound SMS hits Hermes through a provider webhook
- Hermes resolves contact/conversation context
- Hermes decides whether to auto-reply, queue for approval, or schedule follow-up
- Trigger.dev handles sequence steps if needed
- UI shows the message and outcome in the inbox

### Voice
- inbound call reaches the telephony provider
- Hermes decides whether to answer with Vapi, route to human, or fall back
- Vapi performs the call and tool calls against Hermes-approved actions
- Hermes stores transcript, summary, outcome, and next-step tasks
- UI shows the call in the call center / inbox view

## Interoperability Strategy

### MCP
Use MCP for:
- tool access
- integrations
- files
- data sources
- internal services
- provider adapters

### A2A
Use A2A for:
- delegating tasks between agents
- agent handoffs
- specialist collaboration
- inter-agent visibility

### Guardrails
Use explicit guardrails for:
- destructive actions
- financial changes
- customer-facing messages that need review
- outbound voice actions that could create risk

## What Not To Do

- Do not make Mission Control a separate CRM product.
- Do not put the backend in a new language just because the UI is modern.
- Do not use Trigger.dev as the source of truth.
- Do not hide agent work from the operator.
- Do not let Twilio or Vapi own canonical business state.
- Do not introduce Rust as the main application stack for the UI or backend before there is a proven need.
- Do not collapse product surfaces into one generic chat box.

## Build Order

1. Lock backend and UI boundaries.
2. Define the data model and tenant scoping.
3. Define the command / approval / run flow.
4. Define inbox and call visibility surfaces.
5. Define agent deployment and delegation surfaces.
6. Define Trigger.dev sequence boundaries.
7. Define provider adapter contracts.
8. Only then write the implementation plan.

## Success Criteria

The architecture is successful if:
- Mission Control is clearly native to Hermes Central Command.
- The operator can see every important message, call, run, and approval.
- The backend remains FastAPI and the frontend remains React.
- Autonomous work is possible without losing visibility or control.
- Agents can hand off work to other agents in a controlled way.
- Trigger.dev handles durable automation without becoming the business state layer.
- The stack stays simple enough to ship, but strong enough to become the long-term operating system.