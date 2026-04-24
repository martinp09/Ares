---
title: Contact Candidate Packet Test
status: active
updated_at: 2026-04-24
---

# Contact Candidate Packet Test

This page defines the bridge between raw curative-title research and a paid skiptrace provider.

## Rule

Do **not** feed paid skiptrace raw probate rows, decedent names, or unverified title theories.

First build a contact-candidate packet with:

- decedent/estate context
- living candidate names only
- candidate role: applicant, executor, respondent, heir candidate, attorney ad litem, etc.
- known addresses extracted from public case detail
- land-record/property context when available
- aliases that need resolution
- source files and evidence lineage
- explicit “do not skiptrace” decedent field
- requested paid-provider outputs

## Why

Free skiptrace sources were blocked/unreliable in the browser harness. That means paid skiptrace is likely required, but paid data is only useful when the input is clean.

Bad input gives expensive bad output. Garbage in, subscription-funded raccoon fire out.

## Current test output

- Report: `docs/rollout-evidence/contact-candidate-packets-2026-04-24/REPORT.md`
- JSON: `docs/rollout-evidence/contact-candidate-packets-2026-04-24/contact_candidate_packets.json`

The first test generated 12 packets from the Harris County probate keep-now set.

Top packets:

1. `543678` — Tangie Renee Williams
   - strongest because it includes probate parties, respondent/heir candidates, Harris Clerk land-record metadata, aliases, and two property threads.
2. `525833-401` — Daniel R. Montoya
   - strong because the filing is an heir-property partition case and includes multiple respondents.
3. `543652` — Janet Marie Mcmahan
   - useful probate/heirship packet with applicant address and publication/ad-litem friction, but still needs land-record matching.

## Provider input shape

Each packet exposes `next_paid_skiptrace_inputs`:

- `names`
- `addresses`
- `county_context`
- `decedent_context`
- `property_context`
- `requested_outputs`

Requested outputs from a paid provider:

- current phone numbers
- current mailing addresses
- email when available
- living/deceased status
- relatives/associates
- address history
- property ownership hints

## Gates before outreach

A packet being `ready_for_paid_skiptrace` does **not** mean ready for outreach.

Before outreach:

1. resolve HCAD/property match when possible
2. confirm land-record/title relevance
3. run tax overlay only after property/account match
4. dedupe candidate identities
5. apply suppression/compliance checks
6. require operator review for ambiguous heirship/contact claims

## Ares/Hermes boundary

Hermes:

- browser-harness county research
- document-image review when authorized login is available
- extraction and interpretation from public records

Ares:

- stores packet JSON and evidence graph
- tracks state: `ready_for_paid_skiptrace`, `needs_land_record_search`, `needs_hcad_match`, `ready_for_manual_review`
- stores paid-provider response lineage
- controls outreach readiness and suppression
