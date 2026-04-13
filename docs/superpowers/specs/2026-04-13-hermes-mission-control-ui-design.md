# Hermes Mission Control UI Design

> Native operator cockpit for Hermes Central Command. React/TypeScript frontend. This spec defines the visible surface for inbox, calls, approvals, runs, sequences, and agent control.

## Goal

Build a high-density, agent-first Mission Control UI that gives Martin a single cockpit for leads, conversations, calls, approvals, runs, sequences, and agent supervision, without turning Hermes into a separate CRM product.

## Architecture Summary

The UI lives inside the Hermes Central Command repo as `apps/mission-control/`. It talks to the FastAPI backend through typed API routes and read models. It should feel like an operator workbench: fast, dense, visible, and action-oriented.

The UI is not the source of truth. It renders Hermes state and sends commands back to Hermes. Trigger.dev, Twilio, Vapi, and Supabase remain behind the curtain.

## Design Benchmarks

The design should borrow the following patterns from the research set:

- Ramp Labs: productized experiments, visible AI behavior, named experiences
- Sierra: multi-channel communications, one agent across many surfaces
- Cognition AI: teammate-like agents with bounded jobs
- Harvey AI: source-grounded domain workflows and multiple product surfaces
- Glean: search + assistant + agents + governance in one platform

This means the UI should not look like a generic admin panel. It should look like a control cockpit with multiple specialized work surfaces.

## UI Principles

1. High-density, low-friction
- The operator should see a lot without clicking a lot.
- Use compact information hierarchies, persistent context, and fast navigation.

2. Productized surfaces, not widgets
- Dashboard, Inbox, Calls, Approvals, Runs, Sequences, Agents, Search are all real product surfaces.
- Each surface should have a clear job.

3. Agent-first visibility
- Every agent action should be visible somewhere in the UI.
- If the system is doing work, the operator should be able to see it.

4. Context stays on screen
- The operator should not lose the lead, thread, transcript, or run while taking action.
- Side panels and drawers are preferred over full navigation jumps.

5. Fast feedback loops
- The UI should make it easy to approve, reject, retry, launch, pause, and inspect.
- Search and command palette should be available everywhere.

## Information Architecture

### Primary sections
- Dashboard
- Inbox
- Calls
- Approvals
- Runs
- Sequences
- Agents
- Search
- Settings / Integrations

### Default layout philosophy
Use a shell with persistent navigation and high-context work areas.
A strong default is:
- left rail: global nav and queue counts
- center: current workspace
- right rail: context / details / actions

For inbox-heavy work, a three-pane view should be the default because it matches the way communications are actually reviewed.

## Core Screens

### 1. Global Dashboard
The dashboard should answer:
- what is active now
- what needs approval
- what is stuck
- what finished recently
- what agents are currently live
- what channels are currently busy

Suggested dashboard widgets:
- active runs
- approval queue
- unread conversations
- recent calls
- due follow-ups
- failed automations
- agent health
- system status

### 2. Inbox
The inbox is the most important screen.
It should include:
- left pane: lead/conversation list, filters, queues, unread counts
- center pane: thread / conversation timeline
- right pane: lead detail, tags, stage, sequence state, next-best-action, notes

The inbox should support:
- SMS
- calls
- voicemail
- email where relevant
- internal notes
- approval-required replies
- quick actions like assign, snooze, tag, launch sequence, launch agent

### 3. Call Center
The call view should show:
- active calls
- recent calls
- call outcome
- transcript
- recording link if available
- voicemail / missed call handling
- Vapi tool-call history when relevant

The call center should feel like a live operations view, not a static log table.

### 4. Approvals Queue
This screen should show:
- what action is pending
- why it needs approval
- risk level / policy trigger
- the exact payload being approved
- approve / reject / annotate controls

### 5. Runs and Agents
This screen should show:
- active runs
- failed runs
- retriable jobs
- agent registry
- delegated work
- agent handoffs
- logs and artifacts

This is where the operator can inspect the autonomous machinery.

### 6. Sequences / Nurture
This screen should show:
- sequence definitions
- enrolled leads
- next step timing
- delay status
- branch status
- retries
- stop / pause / resume controls

### 7. Search / Command Palette
Search should let the operator:
- find a lead
- find a conversation
- find a call
- find a run
- launch an agent
- trigger a workflow
- jump to a record instantly

The command palette should support quick actions and should be available globally.

## Component Model

The UI should be built from focused, reusable components. Suggested top-level components:

- `MissionControlShell`
- `GlobalNav`
- `DashboardSummary`
- `InboxList`
- `ConversationThread`
- `ContextPanel`
- `LeadHeader`
- `CallTimeline`
- `ApprovalCard`
- `RunInspector`
- `SequenceBoard`
- `AgentLauncher`
- `CommandPalette`
- `FilterBar`
- `ActivityFeed`

The exact file layout can evolve, but each component should have one clear job.

## Interaction Model

### From the operator’s perspective
1. Open dashboard.
2. See unread items, approvals, runs, and active agents.
3. Drill into a lead or conversation.
4. Inspect the full thread, transcript, and context.
5. Approve or edit the next action.
6. Launch or supervise an agent if needed.
7. Watch the result flow back into the inbox and dashboard.

### Important interaction rules
- Keep context visible while acting.
- Prefer drawers, side panels, and inline actions over page hops.
- Do not require the user to switch between multiple unrelated screens to complete one task.
- Use optimistic feedback when the backend supports it, but keep Hermes as the source of truth.

## Data Flow

### Read path
- UI requests current state from Hermes read APIs.
- Hermes serves projections for dashboard, inbox, calls, approvals, runs, and sequences.
- UI caches and refreshes data frequently enough to feel live.

### Write path
- User actions become Hermes commands.
- Hermes evaluates policy and creates runs / approvals as needed.
- Trigger.dev handles long-running work.
- Provider callbacks update Hermes.
- UI refreshes from Hermes state.

### Realtime behavior
The spec should allow for:
- polling at first if needed for simplicity
- realtime push later if it materially improves operator experience

The important rule is that the UI must remain eventually consistent with Hermes, not with providers.

## Visual Tone

The UI should feel:
- dense
- calm
- confident
- operational
- agentic
- modern, but not flashy

It should avoid looking like a generic SaaS admin dashboard.
It should look like a professional workbench where the human supervises a fleet of agents.

## What Not To Do

- Do not build a separate CRM UI.
- Do not hide the automation behind a single chat input.
- Do not make the layout so sparse that important operational context disappears.
- Do not put business logic in the frontend.
- Do not let provider-specific UI shape the product.
- Do not over-index on aesthetics at the expense of control and speed.

## Build Order

1. Build the shell and navigation.
2. Build the dashboard summary.
3. Build the inbox and conversation thread.
4. Build the approvals queue.
5. Build the runs / agents surface.
6. Build the call center view.
7. Build sequence views.
8. Add command palette and global search.
9. Add polish only after the core cockpit works.

## Success Criteria

The UI is successful if:
- Martin can see messages, calls, approvals, and runs in one place.
- The operator can act without context loss.
- Agent work is visible, not hidden.
- The UI feels like a cockpit for Hermes, not a separate CRM.
- The UI directly reflects the agent-first architecture and benchmark lessons from Ramp, Sierra, Cognition, Harvey, and Glean.