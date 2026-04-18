# Ares Probate + Tax Delinquent MVP Design

## Summary

Ares will start with a narrow real-estate investment wedge:

- **Counties:** Harris, Tarrant, Montgomery, Dallas, Travis
- **Primary source lane:** probate
- **Secondary source lane:** tax delinquency
- **Priority rule:** probate leads that also verify as tax delinquent rank highest
- **Tax-only lane rule:** when tax delinquency is used as its own source lane, filter for `estate of` properties first, then confirm true delinquency
- **Output:** ranked lead briefs plus outreach drafts for human approval

This is not a full autonomous operator yet. It is a focused lead-finding and outreach-drafting machine for one real workflow.

## Goal

Build the smallest useful version of Ares that can:

1. pull probate leads across the five target Texas counties,
2. verify whether any of those leads are also tax delinquent,
3. separately pull tax-delinquent properties that look like `estate of` properties,
4. rank and explain the best opportunities,
5. generate outreach drafts without sending anything automatically.

## Non-Goals

Do **not** build these in the MVP:

- auto-sending SMS, email, or mail
- contract generation or e-signature flows
- escrow management
- dispo automation
- buyer matching automation
- a generic CRM
- a county-agnostic national search engine
- a fully autonomous deal-closing agent

The first release should help the operator find good leads and move faster, not pretend to replace the whole business.

## Source Lanes

### Lane 1: Probate-first pipeline

This is the main lane.

Process:

1. ingest probate records for the five target counties,
2. normalize the lead into a common property/person record,
3. verify owner / property context,
4. run a tax-delinquent overlay search against the probate set,
5. promote any probate record that also verifies as tax delinquent.

Priority order in this lane:

- probate + verified tax delinquent
- probate only

### Lane 2: Tax-delinquent `estate of` pipeline

This is the secondary lane.

Process:

1. ingest tax-delinquent records,
2. filter to properties that appear to be `estate of` properties,
3. verify they are truly delinquent,
4. score them as a separate lead source.

Priority order in this lane:

- tax delinquent + `estate of` + strong owner/property match
- tax delinquent + `estate of`

### Important rule

Tax delinquency is **not** treated as a blanket source of equal quality. The system should first ask:

- Is this probate?
- If yes, does it also verify as tax delinquent?
- If tax delinquent is its own source lane, does it look like an `estate of` property?

That keeps the pipeline clean and avoids garbage leads.

## Counties

The MVP covers exactly these five counties:

- Harris
- Tarrant
- Montgomery
- Dallas
- Travis

County should be a configurable input, not hardcoded into logic, but these are the first supported markets.

## Lead Ranking Rules

Ares should rank leads using a simple tier system instead of trying to be clever too early.

### Tier A

- probate lead
- verified tax delinquent

This is the best lead class.

### Tier B

- probate lead only

Still valuable, still worth outreach.

### Tier C

- tax delinquent
- `estate of` property
- probate not confirmed yet

Useful, but lower priority than probate overlap leads.

### Tie-breakers

Within a tier, sort by:

- county
- clarity of owner / estate match
- recency / freshness of the source record
- amount owed or distress severity when available
- quality of contact data when available

## User Flow

1. Operator picks one or more of the five counties.
2. Ares runs the probate pull.
3. Ares overlays tax-delinquent verification on those probate leads.
4. Ares separately runs the tax-delinquent `estate of` lane.
5. Ares ranks all results into lead tiers.
6. Ares produces a lead brief for each worthwhile record.
7. Ares generates outreach drafts based on the lead type.
8. Operator reviews drafts and decides what to send manually.

## Lead Brief Output

Each lead brief should answer:

- Why is this lead in the system?
- Which source lane triggered it?
- Is it probate, tax delinquent, or both?
- Is `estate of` involved?
- What county is it in?
- Why does it rank where it ranks?
- What outreach angle should be used?

The brief should be readable by a human in under a minute.

## Outreach Draft Output

Ares should generate draft copy for:

- SMS
- email
- voicemail script
- direct-mail copy

The drafts should be specific to the lead class:

- probate + tax delinquent
- probate only
- tax delinquent `estate of`

The drafts should be written for human approval, not auto-send.

## System Shape

The MVP should be organized as a small pipeline with clear boundaries:

### 1) Source ingest
Collect probate and tax records from the target counties.

### 2) Normalization
Convert county-specific records into a shared lead shape.

### 3) Matching and overlay
Match tax delinquency against probate leads, and match `estate of` properties inside the tax lane.

### 4) Scoring
Assign the lead tier and tie-break order.

### 5) Brief generation
Explain why the lead matters.

### 6) Draft generation
Generate outreach drafts for review.

Each step should be separately testable.

## Data Quality and Error Handling

The system should assume county data will be messy.

Handle these cases explicitly:

- missing owner names
- inconsistent estate naming
- duplicate records across pulls
- partial property-address matches
- delinquency data that does not cleanly map to the probate record
- false `estate of` hits

When data is ambiguous, the system should lower confidence instead of guessing.

## Success Criteria

The MVP is successful if it can:

- run across all five counties,
- find probate leads reliably,
- correctly elevate probate + tax delinquent overlaps,
- identify `estate of` tax-delinquent leads,
- generate usable outreach drafts,
- and keep manual approval before any outbound send.

## Phase 2 Later

Once this MVP is working, the next expansion could add:

- actual outbound sending
- response tracking
- follow-up automation
- richer skiptracing
- disposition workflows
- buyer-list matching

But none of that is needed to prove the wedge.
