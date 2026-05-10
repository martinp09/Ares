---
title: "GoHighLevel Mission Control UI Reference"
created: 2026-05-10
type: design-reference
tags: [ares, mission-control, crm, gohighlevel, ui-ux, pipeline, opportunities, records, inbox]
sources:
  - https://help.gohighlevel.com/support/solutions/articles/155000001982
  - https://help.gohighlevel.com/support/solutions/articles/155000007528
  - https://help.gohighlevel.com/support/solutions/articles/155000003910-customize-opportunity-cards-in-board-view
  - https://help.gohighlevel.com/support/solutions/articles/155000007688-opportunity-forecasting-in-highlevel
  - https://help.gohighlevel.com/support/solutions/articles/155000006610-getting-started-with-the-new-conversations-experience
  - https://help.gohighlevel.com/support/solutions/articles/155000006504-contacts-revamped-list-view-smartlists
  - https://ideas.gohighlevel.com/changelog/pipeline-navigation-improvements-stage-colors
  - https://ideas.gohighlevel.com/changelog/smartlists-20-revamped-list-view
---

# GoHighLevel Mission Control UI Reference

This is a public-source UI/UX extraction for upgrading Ares Mission Control. It is based on HighLevel help docs and changelog pages available on 2026-05-10, not private account access.

## Product Shape

GoHighLevel's current CRM surfaces are converging on a compact, high-density operating shell:

- left global navigation for modules
- module-level top bar for account, search, filters, and primary create actions
- saved views and tabs near the object surface
- board/list/forecast mode switching for opportunities
- right-side drawers or context panels for record edits and linked data
- persistent per-user layout preferences for board card fields, stage widths, sorting, and filters
- safer admin workflows for stage edits, including remapping opportunities when a stage is deleted

For Ares, the useful target is not a visual clone. The target is a Mission Control shell with GHL's CRM ergonomics plus Ares-specific runtime state: records, owners, properties, contacts, opportunities, agents, runs, approvals, provider events, and typed commands.

## Reverse-Engineered Patterns

### Opportunities And Pipelines

GHL treats opportunities as active deal objects inside ordered pipelines. The main workspace supports visual Kanban management, list-style cleanup, and a newer forecast workspace.

Patterns to copy:

- pipeline selector stays close to the object controls, not buried in settings
- board columns are stages; stages move left to right
- columns show stage name, count, value, and stage color
- stages can collapse, expand, and resize
- sort controls prioritize cards by timing, value, or custom fields
- board layout preferences persist per user/browser
- cards expose contact, opportunity value, source, status, next task, and quick counters
- card quick counters include conversations, tasks, notes, tags, calls, and appointments
- card field layout has default, compact, and unlabeled modes
- stage colors can render as dots or background tints and appear across board and details
- stage management allows rename, reorder, dashboard/reporting visibility, colors, add, delete, and safe remap
- opportunity status remains distinct from stage: open, won, lost, abandoned
- forecast view adds maximum/expected/won revenue, expected close date, probability, risk, data hygiene, and time grouping

Ares translation:

- keep Pipeline as active deal execution, not raw record inventory
- add board/list/forecast tabs before adding heavier custom pipelines
- show source lane and strategy lane on every opportunity card
- make stage age, SLA risk, next task, and missing data first-class card signals
- use colored stage bands for visual scan but keep Ares' operator theme restrained
- treat "Won/Lost/Abandoned" as status outcomes, not regular stage columns
- make stage remaps append-only events

### Records / Contacts / SmartLists

GHL's revamped Contacts list and SmartLists 2.0 are a reusable pattern for any CRM object list: Contacts, Opportunities, Companies, Tasks, and Custom Objects.

Patterns to copy:

- saved lists are visible at the top of the table
- advanced filters support nested AND/OR logic
- quick search helps jump across lists/views
- fields can be managed inline in a drawer
- columns support reorder, resize, alignment, sorting, and persistence
- unsaved changes and save states are visible inline
- share and permissions are attached to saved views
- filters, sorting, and field management are consistent across CRM modules

Ares translation:

- Records should feel like GHL SmartLists plus REISift-style inventory controls
- use saved views for "Needs skip trace", "Marketable", "No phone", "Promoted", "Suppressed", and source lists
- keep bulk actions sticky above the table when rows are selected
- add Manage Fields, Filter, Sort, and Share View controls as reusable components across Records, Opportunities, Tasks, and future Owners/Properties
- preserve record quality signals: no phone, low confidence, duplicate candidate, incomplete owner, stale source

### Conversations And Inbox

GHL's redesigned Conversations module uses four flexible panels:

- Inbox panel: My Inbox, Team Inbox, Internal Chat
- Chat list panel: conversation queue, search, unread, assigned owner, tags, channel, last message
- Message history panel: timeline, SMS/email/calls/notes, inline reply
- Right panel: contact context, custom fields, files, payments, activities, and related records

Patterns to copy:

- panels collapse so users can trade queue space for reading/composing space
- tag filters use AND/OR logic like SmartLists
- conversation context does not force navigation to Contacts
- email composer can be full-screen or inline
- call transcripts can open in the message history while contact details remain editable
- right panel is the operational context panel, not a passive profile card

Ares translation:

- Inbox needs a four-panel version: queue selector, conversation list, conversation timeline, linked owner/property/opportunity/action panel
- conversations should expose linked opportunity, record, owner, property, tasks, and agent findings
- replies should support internal note, SMS, email, and task creation from one composer area
- agent actions should live in the right panel: summarize thread, draft reply, classify intent, suggest stage move, create task

### Dashboard

GHL dashboard/reporting emphasizes opportunity count, pipeline value, conversion rate, funnel distribution, stage drop-off, and forecast timing.

Ares translation:

- lead with "what needs action today" over vanity totals
- show stale stage, no next task, reply needs review, provider callback failure, no phone, DNC risk, and agent approval needed
- include compact stage distribution and forecast bands for inbound lease-option and outbound probate lanes
- make each metric a route into the filtered CRM workspace

## Ares Upgrade Targets

### PipelinePage

- Add top object tabs: `Board`, `List`, `Forecast`, `Stage Config`.
- Add compact control bar: pipeline selector, saved view, filter, sort, manage fields, create opportunity.
- Replace fixed equal stage columns with resizable/collapsible columns.
- Add stage color dot/tint and visible per-stage totals.
- Add card layout presets: default, compact, unlabeled.
- Add quick action counter row on cards: conversation, tasks, notes, tags, calls, appointments.
- Move selected-opportunity detail into a right drawer pattern that can later share code with Records and Inbox context panels.

### RecordsPage

- Convert saved views into a GHL-style SmartList bar.
- Add reusable filter builder affordance with AND/OR grouping.
- Add Manage Fields drawer affordance even before full persistence exists.
- Show table column density closer to GHL: checkbox, owner/property anchor, status badges, source/list, phone/email, quality, tasks, promotion, last activity.
- Make selected bulk action state visually persistent.

### InboxPage

- Expand from two columns to four panels:
  - inbox scope selector
  - thread list
  - message timeline/composer
  - right context panel
- Add channel tabs or composer selector for SMS, email, note, task.
- Add linked opportunity/stage movement summary in the right panel.
- Add agent action strip scoped to the selected thread.

## Standalone HTML/CSS Reference

Save the block below as a static `.html` file if a browser reference is needed. It is intentionally static and dependency-free so it can be compared against the React Mission Control implementation without build tooling.

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ares Mission Control CRM Reference</title>
  <style>
    :root {
      color-scheme: light;
      --page: #f5f7fb;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --surface-blue: #eef6ff;
      --border: #d9e1ea;
      --border-strong: #bdc9d7;
      --text: #17202a;
      --muted: #5f6f82;
      --muted-soft: #8a98a8;
      --blue: #1f7ae0;
      --blue-dark: #155fb1;
      --teal: #0f9f8f;
      --green: #24a148;
      --amber: #d97706;
      --red: #d13438;
      --violet: #6d5bd0;
      --rail: #101827;
      --rail-soft: #172235;
      --shadow: 0 18px 40px rgba(16, 24, 39, 0.10);
      font-family: "IBM Plex Sans", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-width: 1180px;
      min-height: 100vh;
      background: var(--page);
      color: var(--text);
    }

    button,
    input,
    select,
    textarea {
      font: inherit;
    }

    button {
      cursor: pointer;
    }

    .app {
      min-height: 100vh;
      display: grid;
      grid-template-columns: 244px minmax(0, 1fr);
    }

    .rail {
      background: linear-gradient(180deg, var(--rail), #0b1220);
      color: #d8e2ee;
      padding: 18px 14px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .brand {
      padding: 8px 8px 18px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.10);
    }

    .brand strong {
      display: block;
      font-size: 24px;
      letter-spacing: 0;
      color: #ffffff;
    }

    .brand span {
      display: block;
      margin-top: 5px;
      font-size: 12px;
      color: #94a3b8;
    }

    .nav-group {
      display: grid;
      gap: 4px;
    }

    .nav-title {
      padding: 0 8px 6px;
      font-size: 11px;
      font-weight: 700;
      color: #7f8da3;
      text-transform: uppercase;
    }

    .nav-item {
      width: 100%;
      border: 0;
      border-radius: 7px;
      padding: 10px 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: transparent;
      color: #cbd5e1;
      text-align: left;
    }

    .nav-item.active {
      background: #24324a;
      color: #ffffff;
      box-shadow: inset 3px 0 0 var(--blue);
    }

    .nav-item b {
      min-width: 23px;
      padding: 1px 6px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.10);
      font-size: 11px;
      text-align: center;
    }

    .main {
      min-width: 0;
      display: grid;
      grid-template-rows: auto 1fr;
    }

    .topbar {
      height: 62px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 12px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .search {
      width: min(460px, 42vw);
      height: 38px;
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 0 12px;
      color: var(--text);
      background: var(--surface-soft);
    }

    .top-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .btn {
      height: 36px;
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 0 12px;
      background: var(--surface);
      color: var(--text);
      font-weight: 650;
    }

    .btn.primary {
      border-color: var(--blue-dark);
      background: var(--blue);
      color: #ffffff;
    }

    .workspace {
      min-width: 0;
      padding: 18px 20px 22px;
      display: grid;
      gap: 14px;
    }

    .module-head {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
    }

    .module-head h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.15;
      letter-spacing: 0;
    }

    .module-head p {
      margin: 5px 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .tabs,
    .smartlists,
    .toolbar,
    .metric-grid {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .tab,
    .chip,
    .select-pill {
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--muted);
      border-radius: 7px;
      min-height: 34px;
      padding: 7px 10px;
      font-size: 13px;
      font-weight: 650;
    }

    .tab.active,
    .chip.active {
      color: var(--blue-dark);
      border-color: #9cc7f8;
      background: var(--surface-blue);
    }

    .select-pill {
      display: flex;
      align-items: center;
      gap: 10px;
      color: var(--text);
    }

    .metric-card {
      min-width: 148px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      padding: 12px;
      box-shadow: 0 1px 0 rgba(16, 24, 39, 0.02);
    }

    .metric-card span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }

    .metric-card strong {
      display: block;
      margin-top: 4px;
      font-size: 24px;
      line-height: 1;
    }

    .metric-card small {
      display: block;
      margin-top: 5px;
      color: var(--muted-soft);
      font-size: 11px;
    }

    .crm-grid {
      min-height: 676px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 344px;
      gap: 14px;
      align-items: stretch;
    }

    .board-panel,
    .side-panel,
    .records-panel,
    .inbox-panel {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .board-head,
    .panel-head {
      min-height: 54px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      background: var(--surface);
    }

    .board-head h2,
    .panel-head h2 {
      margin: 0;
      font-size: 15px;
      letter-spacing: 0;
    }

    .board-head span,
    .panel-head span {
      color: var(--muted);
      font-size: 12px;
    }

    .kanban {
      height: 402px;
      padding: 12px;
      display: grid;
      grid-template-columns: 260px 300px 260px 92px;
      gap: 10px;
      overflow-x: auto;
      background: #f6f8fb;
    }

    .stage {
      min-width: 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #fdfefe;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .stage.collapsed {
      align-items: center;
      justify-content: flex-start;
      background: #f0f5fb;
    }

    .stage-head {
      padding: 10px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
    }

    .stage-title {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .dot {
      width: 10px;
      height: 10px;
      flex: 0 0 auto;
      border-radius: 999px;
      background: var(--blue);
    }

    .dot.green { background: var(--green); }
    .dot.amber { background: var(--amber); }
    .dot.violet { background: var(--violet); }

    .stage-title strong {
      display: block;
      font-size: 13px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .stage-title span {
      display: block;
      margin-top: 2px;
      color: var(--muted-soft);
      font-size: 11px;
    }

    .stage-count {
      border-radius: 999px;
      padding: 2px 7px;
      background: #eef2f7;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }

    .stage.collapsed .stage-head {
      width: 100%;
      min-height: 402px;
      writing-mode: vertical-rl;
      justify-content: center;
      align-items: center;
    }

    .cards {
      padding: 10px;
      display: grid;
      gap: 9px;
      overflow: auto;
    }

    .opp-card {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #ffffff;
      padding: 10px;
      display: grid;
      gap: 8px;
      box-shadow: 0 1px 3px rgba(16, 24, 39, 0.05);
    }

    .opp-card.active {
      border-color: #8dbdf4;
      box-shadow: 0 0 0 2px #d9ecff;
    }

    .opp-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
    }

    .opp-top strong {
      font-size: 13px;
      line-height: 1.25;
    }

    .opp-top span {
      color: var(--green);
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }

    .opp-meta {
      display: grid;
      gap: 3px;
      color: var(--muted);
      font-size: 12px;
    }

    .badges,
    .quick-actions {
      display: flex;
      align-items: center;
      gap: 5px;
      flex-wrap: wrap;
    }

    .badge {
      border-radius: 999px;
      padding: 3px 7px;
      background: #edf2f7;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
    }

    .badge.hot {
      background: #fff4df;
      color: #975a16;
    }

    .badge.risk {
      background: #ffe8e8;
      color: #a4262c;
    }

    .badge.clean {
      background: #def7ec;
      color: #047857;
    }

    .quick-actions {
      border-top: 1px solid var(--border);
      padding-top: 7px;
      color: var(--muted);
      font-size: 11px;
    }

    .quick-actions b {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 24px;
      height: 22px;
      border-radius: 5px;
      background: #f1f5f9;
      color: var(--muted);
    }

    .below-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
      gap: 14px;
    }

    .records-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }

    .records-table th,
    .records-table td {
      border-bottom: 1px solid var(--border);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }

    .records-table th {
      background: #f8fafc;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
    }

    .records-table td strong {
      display: block;
      font-size: 12px;
    }

    .records-table td span {
      display: block;
      margin-top: 2px;
      color: var(--muted);
    }

    .side-panel {
      display: grid;
      grid-template-rows: auto 1fr;
    }

    .drawer-body {
      padding: 14px;
      overflow: auto;
      display: grid;
      gap: 12px;
    }

    .field-card {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      background: var(--surface-soft);
    }

    .field-card h3 {
      margin: 0 0 8px;
      font-size: 13px;
    }

    .field-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 6px 0;
      border-top: 1px solid rgba(217, 225, 234, 0.75);
      font-size: 12px;
    }

    .field-row:first-of-type {
      border-top: 0;
    }

    .field-row span {
      color: var(--muted);
    }

    .field-row strong {
      text-align: right;
    }

    .timeline {
      display: grid;
      gap: 8px;
    }

    .event {
      border-left: 3px solid var(--blue);
      padding: 2px 0 2px 9px;
      font-size: 12px;
    }

    .event strong {
      display: block;
    }

    .event span {
      display: block;
      margin-top: 2px;
      color: var(--muted);
    }

    .inbox-shell {
      height: 280px;
      display: grid;
      grid-template-columns: 128px 240px minmax(0, 1fr) 240px;
      border-top: 1px solid var(--border);
    }

    .inbox-nav,
    .thread-list,
    .message-pane,
    .context-pane {
      min-width: 0;
      border-right: 1px solid var(--border);
      overflow: auto;
    }

    .context-pane {
      border-right: 0;
    }

    .inbox-nav {
      background: #f8fafc;
      padding: 10px;
      display: grid;
      align-content: start;
      gap: 7px;
    }

    .queue {
      border: 0;
      border-radius: 7px;
      padding: 8px;
      background: transparent;
      color: var(--muted);
      text-align: left;
      font-size: 12px;
      font-weight: 700;
    }

    .queue.active {
      background: #e8f2ff;
      color: var(--blue-dark);
    }

    .thread {
      width: 100%;
      border: 0;
      border-bottom: 1px solid var(--border);
      background: #ffffff;
      padding: 10px;
      text-align: left;
    }

    .thread.active {
      background: #f0f7ff;
    }

    .thread strong {
      display: block;
      font-size: 12px;
    }

    .thread span {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 11px;
    }

    .message-pane {
      padding: 12px;
      display: grid;
      grid-template-rows: 1fr auto;
      gap: 10px;
      background: #fbfdff;
    }

    .messages {
      display: grid;
      align-content: start;
      gap: 8px;
    }

    .bubble {
      max-width: 76%;
      border-radius: 8px;
      padding: 9px 10px;
      background: #edf2f7;
      font-size: 12px;
    }

    .bubble.me {
      justify-self: end;
      background: #dcecff;
    }

    .composer {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      background: #ffffff;
      display: grid;
      gap: 8px;
    }

    .composer-tabs {
      display: flex;
      gap: 5px;
    }

    .composer-tabs span {
      border-radius: 999px;
      padding: 3px 7px;
      background: #edf2f7;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
    }

    .composer textarea {
      width: 100%;
      min-height: 42px;
      resize: none;
      border: 0;
      outline: 0;
    }

    .context-pane {
      padding: 10px;
      display: grid;
      align-content: start;
      gap: 10px;
      background: #ffffff;
    }

    .mini-card {
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 9px;
      font-size: 12px;
    }

    .mini-card strong {
      display: block;
      margin-bottom: 4px;
    }

    .mini-card span {
      color: var(--muted);
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="rail">
      <div class="brand">
        <strong>Ares</strong>
        <span>Mission Control CRM</span>
      </div>

      <div class="nav-group">
        <div class="nav-title">CRM</div>
        <button class="nav-item active">Opportunities <b>48</b></button>
        <button class="nav-item">Records <b>482</b></button>
        <button class="nav-item">Conversations <b>17</b></button>
        <button class="nav-item">Tasks <b>31</b></button>
        <button class="nav-item">Activity <b>9</b></button>
      </div>

      <div class="nav-group">
        <div class="nav-title">Runtime</div>
        <button class="nav-item">Agents <b>6</b></button>
        <button class="nav-item">Runs <b>14</b></button>
        <button class="nav-item">Approvals <b>5</b></button>
        <button class="nav-item">Settings</button>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <input class="search" value="" placeholder="Search records, owners, properties, conversations..." />
        <div class="top-actions">
          <button class="btn">Import</button>
          <button class="btn">Manage fields</button>
          <button class="btn primary">Create opportunity</button>
        </div>
      </header>

      <section class="workspace">
        <div class="module-head">
          <div>
            <h1>Opportunities</h1>
            <p>GHL-style board, records inventory, and conversations context adapted for Ares operators.</p>
          </div>
          <div class="tabs" aria-label="Opportunity views">
            <button class="tab active">Board</button>
            <button class="tab">List</button>
            <button class="tab">Forecast</button>
            <button class="tab">Stage config</button>
          </div>
        </div>

        <div class="toolbar">
          <div class="select-pill">Pipeline: Outbound Probate</div>
          <button class="chip active">All open</button>
          <button class="chip">My opportunities</button>
          <button class="chip">Reply needs review</button>
          <button class="chip">No next task</button>
          <button class="chip">Filter</button>
          <button class="chip">Sort: stage age</button>
        </div>

        <div class="metric-grid">
          <article class="metric-card"><span>Open pipeline</span><strong>48</strong><small>$1.92M max value</small></article>
          <article class="metric-card"><span>Expected profit</span><strong>$412k</strong><small>weighted forecast</small></article>
          <article class="metric-card"><span>Stale stage</span><strong>11</strong><small>over SLA</small></article>
          <article class="metric-card"><span>Reply review</span><strong>7</strong><small>new conversations</small></article>
          <article class="metric-card"><span>No next task</span><strong>9</strong><small>needs owner</small></article>
        </div>

        <div class="crm-grid">
          <section class="board-panel">
            <div class="board-head">
              <div>
                <h2>Pipeline board</h2>
                <span>Resizable stages, colored stage cues, custom card fields, quick counters</span>
              </div>
              <button class="btn">Card layout</button>
            </div>

            <div class="kanban">
              <section class="stage">
                <div class="stage-head">
                  <div class="stage-title">
                    <i class="dot"></i>
                    <div><strong>Contact candidate ready</strong><span>6 opps | $204k</span></div>
                  </div>
                  <span class="stage-count">6</span>
                </div>
                <div class="cards">
                  <article class="opp-card active">
                    <div class="opp-top"><strong>Estate of M. Williams</strong><span>$42k</span></div>
                    <div class="opp-meta">
                      <span>Property: 1814 Silver St, Houston</span>
                      <span>Owner type: Estate | Source: probate</span>
                    </div>
                    <div class="badges"><span class="badge hot">Hot</span><span class="badge">Phone ready</span><span class="badge risk">2d stale</span></div>
                    <div class="quick-actions"><b>C 3</b><b>T 2</b><b>N 5</b><b>Tag</b><b>Call</b></div>
                  </article>

                  <article class="opp-card">
                    <div class="opp-top"><strong>J. Rios vacant probate</strong><span>$31k</span></div>
                    <div class="opp-meta">
                      <span>Property: 223 W Donovan Ave</span>
                      <span>Owner type: Person | Source: tax/probate</span>
                    </div>
                    <div class="badges"><span class="badge">Needs approval</span><span class="badge">No email</span></div>
                    <div class="quick-actions"><b>C 1</b><b>T 1</b><b>N 2</b><b>Tag</b><b>Call</b></div>
                  </article>
                </div>
              </section>

              <section class="stage">
                <div class="stage-head">
                  <div class="stage-title">
                    <i class="dot green"></i>
                    <div><strong>Outreach active</strong><span>13 opps | $530k</span></div>
                  </div>
                  <span class="stage-count">13</span>
                </div>
                <div class="cards">
                  <article class="opp-card">
                    <div class="opp-top"><strong>Harris probate lead 392</strong><span>$57k</span></div>
                    <div class="opp-meta">
                      <span>Property: 4318 Kress St</span>
                      <span>Assigned: Martin | Next: SMS follow-up</span>
                    </div>
                    <div class="badges"><span class="badge clean">Clean data</span><span class="badge">SMS sent</span></div>
                    <div class="quick-actions"><b>C 4</b><b>T 1</b><b>N 1</b><b>Tag</b><b>Call</b></div>
                  </article>

                  <article class="opp-card">
                    <div class="opp-top"><strong>Johnson heirs list</strong><span>$76k</span></div>
                    <div class="opp-meta">
                      <span>Property: 7202 Avenue P</span>
                      <span>Agent finding: heir contact mismatch</span>
                    </div>
                    <div class="badges"><span class="badge risk">Research gap</span><span class="badge">Email ready</span></div>
                    <div class="quick-actions"><b>C 2</b><b>T 4</b><b>N 8</b><b>Tag</b><b>Call</b></div>
                  </article>
                </div>
              </section>

              <section class="stage">
                <div class="stage-head">
                  <div class="stage-title">
                    <i class="dot amber"></i>
                    <div><strong>Reply needs review</strong><span>7 opps | $281k</span></div>
                  </div>
                  <span class="stage-count">7</span>
                </div>
                <div class="cards">
                  <article class="opp-card">
                    <div class="opp-top"><strong>F. Grant seller reply</strong><span>$48k</span></div>
                    <div class="opp-meta">
                      <span>Latest: "What would you offer?"</span>
                      <span>Next task due today</span>
                    </div>
                    <div class="badges"><span class="badge hot">Inbound reply</span><span class="badge">Call suggested</span></div>
                    <div class="quick-actions"><b>C 6</b><b>T 1</b><b>N 3</b><b>Tag</b><b>Call</b></div>
                  </article>
                </div>
              </section>

              <section class="stage collapsed">
                <div class="stage-head">
                  <div class="stage-title">
                    <i class="dot violet"></i>
                    <div><strong>Title open</strong><span>collapsed | 5</span></div>
                  </div>
                  <span class="stage-count">5</span>
                </div>
              </section>
            </div>

            <div class="below-grid">
              <section class="records-panel">
                <div class="panel-head">
                  <div>
                    <h2>Records SmartLists</h2>
                    <span>Saved views, AND/OR filters, field management, bulk actions</span>
                  </div>
                  <button class="btn">Filter builder</button>
                </div>
                <div class="smartlists" style="padding: 10px 12px; border-bottom: 1px solid var(--border);">
                  <button class="chip active">All records 482</button>
                  <button class="chip">Needs skip trace 72</button>
                  <button class="chip">Marketable 260</button>
                  <button class="chip">No phone 88</button>
                  <button class="chip">Promoted 48</button>
                </div>
                <table class="records-table">
                  <thead>
                    <tr>
                      <th><input type="checkbox" /></th>
                      <th>Owner / Property</th>
                      <th>Status</th>
                      <th>Source</th>
                      <th>Quality</th>
                      <th>Next work</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><input type="checkbox" checked /></td>
                      <td><strong>Estate of M. Williams</strong><span>1814 Silver St</span></td>
                      <td><span class="badge clean">Marketable</span></td>
                      <td>Probate import</td>
                      <td>92</td>
                      <td>Approve outreach</td>
                    </tr>
                    <tr>
                      <td><input type="checkbox" /></td>
                      <td><strong>Johnson heirs list</strong><span>7202 Avenue P</span></td>
                      <td><span class="badge risk">Research gap</span></td>
                      <td>Tax + probate</td>
                      <td>61</td>
                      <td>Resolve heir contact</td>
                    </tr>
                    <tr>
                      <td><input type="checkbox" /></td>
                      <td><strong>R. Nguyen vacant</strong><span>8922 Madera Rd</span></td>
                      <td><span class="badge">Needs skip trace</span></td>
                      <td>County list</td>
                      <td>48</td>
                      <td>Queue skip trace</td>
                    </tr>
                  </tbody>
                </table>
              </section>

              <section class="inbox-panel">
                <div class="panel-head">
                  <div>
                    <h2>Conversations</h2>
                    <span>Four-panel inbox with right-side record context</span>
                  </div>
                </div>
                <div class="inbox-shell">
                  <nav class="inbox-nav">
                    <button class="queue active">My Inbox 7</button>
                    <button class="queue">Team 17</button>
                    <button class="queue">Internal 3</button>
                    <button class="queue">Unread 12</button>
                  </nav>
                  <div class="thread-list">
                    <button class="thread active"><strong>F. Grant</strong><span>SMS | What would you offer?</span></button>
                    <button class="thread"><strong>M. Williams</strong><span>Email | Probate docs received</span></button>
                    <button class="thread"><strong>J. Rios</strong><span>Call | Missed callback</span></button>
                  </div>
                  <div class="message-pane">
                    <div class="messages">
                      <div class="bubble">I got your letter. What would you offer for the house?</div>
                      <div class="bubble me">Thanks. I can review the property today and call with a range.</div>
                      <div class="bubble">Call after 4.</div>
                    </div>
                    <div class="composer">
                      <div class="composer-tabs"><span>SMS</span><span>Email</span><span>Note</span><span>Task</span></div>
                      <textarea>Draft seller callback confirmation...</textarea>
                    </div>
                  </div>
                  <aside class="context-pane">
                    <div class="mini-card"><strong>Linked opportunity</strong><span>Reply needs review | 1d in stage</span></div>
                    <div class="mini-card"><strong>Owner</strong><span>F. Grant | phone verified</span></div>
                    <div class="mini-card"><strong>Property</strong><span>3907 Yellowstone Blvd | vacant flag</span></div>
                    <div class="mini-card"><strong>Agent actions</strong><span>Draft reply, suggest stage, create task</span></div>
                  </aside>
                </div>
              </section>
            </div>
          </section>

          <aside class="side-panel">
            <div class="panel-head">
              <div>
                <h2>Opportunity drawer</h2>
                <span>Edit without leaving the board</span>
              </div>
              <button class="btn">Open full</button>
            </div>
            <div class="drawer-body">
              <section class="field-card">
                <h3>Estate of M. Williams</h3>
                <div class="field-row"><span>Status</span><strong>Open</strong></div>
                <div class="field-row"><span>Stage</span><strong>Contact candidate ready</strong></div>
                <div class="field-row"><span>Value</span><strong>$42,000</strong></div>
                <div class="field-row"><span>Owner</span><strong>Martin</strong></div>
                <div class="field-row"><span>Expected close</span><strong>May 28</strong></div>
                <div class="field-row"><span>Risk</span><strong>Missing heir consent</strong></div>
              </section>

              <section class="field-card">
                <h3>Linked records</h3>
                <div class="field-row"><span>Owner</span><strong>M. Williams Estate</strong></div>
                <div class="field-row"><span>Property</span><strong>1814 Silver St</strong></div>
                <div class="field-row"><span>Contacts</span><strong>3 candidates</strong></div>
                <div class="field-row"><span>Tasks</span><strong>2 open</strong></div>
              </section>

              <section class="field-card">
                <h3>Agent workbench</h3>
                <button class="btn" style="width: 100%; margin-bottom: 8px;">Summarize evidence</button>
                <button class="btn" style="width: 100%; margin-bottom: 8px;">Draft outreach</button>
                <button class="btn" style="width: 100%;">Audit next task</button>
              </section>

              <section class="field-card">
                <h3>Recent activity</h3>
                <div class="timeline">
                  <div class="event"><strong>Stage moved</strong><span>Promoted from record to contact candidate ready</span></div>
                  <div class="event"><strong>Agent finding</strong><span>Probate contact candidate scored 0.82 confidence</span></div>
                  <div class="event"><strong>Task created</strong><span>Call verified heir before outreach</span></div>
                </div>
              </section>
            </div>
          </aside>
        </div>
      </section>
    </main>
  </div>
</body>
</html>
```

