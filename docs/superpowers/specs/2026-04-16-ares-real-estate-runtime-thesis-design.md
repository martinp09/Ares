---
title: "Ares Real Estate Runtime Thesis"
status: draft
updated_at: "2026-04-16T21:45:00-05:00"
---

# Ares Real Estate Runtime Thesis

## Thesis

Ares should be built as a reusable real-estate operating runtime for agent-driven work across:

- data gathering
- prospecting
- acquisitions
- transaction coordination
- title
- dispo

Hermes is the current primary driver, not the product boundary.
Ares must be able to support other future agent drivers, human operators, and scheduled workflow entrypoints without changing its core model.

In short:

- Hermes thinks, researches, browses, and decides
- Ares records, routes, enforces, and orchestrates
- providers transport messages, files, and events

## Product Position

Ares is not:

- a probate app
- a cold email app
- a lease-option app
- a chat agent pretending to be a CRM

Ares is:

- the canonical state layer for the business
- the execution runtime agents can call into
- the replay-safe workflow engine for acquisition and operations
- the operator cockpit backend behind Mission Control

## Core Boundary

### Hermes and other agent drivers

Agent drivers own:

- browser automation
- public-data gathering
- ambiguous record interpretation
- lead research
- segmentation judgment
- nuanced copy decisions
- exception analysis
- recommendations on what to do next

### Ares runtime

Ares owns:

- typed command intake
- lead state
- dedupe and identity
- source-lane classification
- pain-stack scoring
- channel routing
- campaign enrollment
- provider webhooks
- suppression
- operator task creation
- run lineage
- replay safety
- Mission Control read models

### Providers

Providers are transport only:

- Instantly for cold outbound
- Resend for transactional or opt-in email
- TextGrid for SMS where compliant and appropriate
- future mail, title, dispo, and TC vendors through adapter seams

Providers must never become the source of truth.

## Business Runtime Domains

### 1. Data Gathering

Purpose:
collect and normalize raw public and operator-discovered signals.

Examples:

- probate filings
- tax delinquency
- ownership data
- absentee indicators
- code violations
- expired and FSBO listings
- title and lien signals

### 2. Prospecting

Purpose:
turn qualified records into channel-safe outreach and response tracking.

Examples:

- cold email
- direct mail
- consented SMS follow-up
- future call and buyer outreach

### 3. Acquisitions

Purpose:
qualify opportunities, route strategy, and hand work to the operator.

Examples:

- reply triage
- seller qualification
- offer-path recommendation
- opportunity queue

### 4. Transaction Coordination

Purpose:
track contract-to-close workflow state and deadlines.

Examples:

- contract sent / signed
- earnest money
- inspections
- contingencies
- follow-up deadlines
- coordination tasks

### 5. Title

Purpose:
track curative work, exceptions, and title-file progression.

Examples:

- lien discovery
- probate/title mismatch
- missing heirs
- payoff issues
- exception state
- curative milestone tracking

### 6. Dispo

Purpose:
route deals to buyers and manage monetization workflows.

Examples:

- buyer matching
- dispo outreach
- asset packets
- blast state
- buyer replies
- close-or-fallout tracking

## Three-Layer Lane Model

To stay reusable, Ares should separate three kinds of lanes.

### Source lanes

These describe where the opportunity came from.

Examples:

- probate
- tax delinquent
- absentee
- tired landlord
- expired
- FSBO
- code violation

### Strategy lanes

These describe how the opportunity may be solved or monetized.

Examples:

- wholesale
- novation
- subto
- seller finance
- wrap
- lease option
- curative title

### Operational stages

These describe where the record is in the business process.

Examples:

- gathered
- prospecting
- acquisition review
- under contract
- title
- dispo
- closed
- dead

This separation is critical.
Probate is not a channel.
Curative title is not a source lane.
Cold email is not a strategy.

## Pain-Stack Model

Ares should support both pure source lanes and composite pain stacks.

Examples:

- probate only
- tax delinquent only
- probate plus tax delinquent
- absentee plus tax delinquent
- estate of plus tax delinquent

Important early composite:

- `estate_of + tax_delinquent`

This should be treated as a high-priority pain-stack signal because it combines estate friction with financial distress and likely operational neglect.

## Contract-to-Close Skeleton

Phase 1 should include a minimal but explicit contract-to-close skeleton.

The first version does not need full TC/title/dispo automation.
It does need first-class state so Ares does not trap itself in lead-gen only.

Recommended initial downstream stages:

- qualified_opportunity
- offer_path_selected
- under_negotiation
- contract_sent
- contract_signed
- title_open
- curative_review
- dispo_ready
- closed
- dead

Recommended first-class work items:

- operator task
- title issue
- coordination milestone
- dispo packet

## Tonight's MVP

Tonight's MVP should stay narrow while preserving the full-business shape.

### Primary lane

- source lane: probate
- outbound method: cold email

### Early scoring priority

Within the probate lane, prioritize overlap with tax distress and estate signals when available.

Examples:

- probate plus tax delinquent
- estate of plus tax delinquent

### MVP loop

1. Hermes gathers and structures Harris probate leads.
2. Ares normalizes, dedupes, and scores them.
3. Ares boosts or tags records with tax-delinquent and estate-of overlap when present.
4. Ares enrolls prioritized records into Instantly.
5. Ares ingests replies, bounces, and unsubscribes.
6. Ares suppresses and creates operator tasks.
7. Mission Control shows queue, reply state, exceptions, and priority signals.

### Required thin downstream placeholders

Even in tonight's MVP, preserve placeholder fields or statuses for:

- acquisitions stage
- title stage
- TC stage
- dispo stage

That keeps the runtime extensible without forcing full downstream implementation tonight.

## Architectural Principles

### 1. Any agent can drive the runtime

Hermes is the first driver, not the only one.

### 2. State lives in Ares

No provider should own lead truth, task truth, or suppression truth.

### 3. Deterministic guarantees stay in code

Important rules must not depend on prompts.

Examples:

- dedupe
- suppression
- idempotency
- task creation guards
- replay safety

### 4. Agents handle ambiguity

Ambiguous or high-judgment work belongs in the driver layer, not the provider adapter layer.

### 5. Source lanes matter as much as channels

Routing and scoring should be source-aware first, then strategy-aware, then channel-aware.

### 6. Downstream operations are first-class

Ares should not stop conceptually at lead generation.
The runtime must be able to grow through contract, title, and dispo.

## Initial Shared Runtime Primitives

The reusable runtime should center on these primitives:

- lead
- lead event
- source lane
- pain-stack signal
- campaign
- campaign membership
- suppression
- task
- automation run
- title issue
- coordination milestone
- dispo packet
- provider adapter

## Recommendation

Build Ares as the shared runtime for a one-person generalist real-estate business, starting with the probate cold-email lane tonight, but with explicit support for future tax-delinquent, title, TC, and dispo workflows.

That keeps the MVP narrow without making the product narrow.
