---
title: Curative Title Wiki
status: active
updated_at: 2026-04-24
repo: martinp09/Ares
branch: test/production-readiness-handoff
---

# Curative Title Wiki

This is the single hub for the Ares/Hermes curative-title lead workflow.

Core doctrine:

- Curative title is **land-record-first**.
- Probate is one source of party clues, not the whole strategy.
- The target is a defensible evidence graph that identifies living heirs, descendants, owners, and partial-rights holders.
- Hermes browser harness is the foundational research method.
- Ares is the deterministic system of record, scoring layer, and Mission Control surface.

## Topic map

1. [[Curative Title Operating Model]]
   - why land records are primary
   - how probate, HCAD, tax, skiptrace, and outreach fit together

2. [[Browser Harness Research Workflow]]
   - how Hermes should work county portals
   - when scripts/adapters are allowed
   - how to capture evidence without faking precision

3. [[County Land Records Playbook]]
   - Harris County Clerk Real Property
   - Montgomery County PublicSearch
   - document/image access rules
   - instrument types and search patterns

4. [[Evidence Graph Data Model]]
   - property/person/document/probate/contact graph
   - source lineage
   - confidence and status model

5. [[Skiptrace Workflow]]
   - free-source skiptrace first
   - paid skiptrace later
   - suppression and outreach-readiness gates

6. [[Tangie Williams Field Test]]
   - first browser-harness field test
   - Fallbrook property thread
   - Perkins/Otis Williams estate thread
   - image-access boundary

7. [[Contact Candidate Packet Test]]
   - normalizes probate/land-record evidence into paid-skiptrace-ready inputs
   - excludes decedents as live targets
   - preserves candidate roles, addresses, confidence, and source lineage

8. [[HCAD Property Match Test]]
   - matches candidate packets to HCAD taxable property records
   - keeps HCAD matching separate from tax overlay and outreach readiness
   - records ambiguity instead of inventing property certainty

## Source evidence

- [[../curative-title-data-pipeline|Curative Title Data Pipeline]]
- [[../production-readiness-handoff|Production Readiness Handoff]]
- [[../rollout-evidence/land-records-recon-2026-04-24/REPORT|Tangie Williams Land-Records Recon Report]]
- [[../rollout-evidence/contact-candidate-packets-2026-04-24/REPORT|Contact Candidate Packet Test]]
- [[../rollout-evidence/hcad-match-test-2026-04-24/REPORT|HCAD Property Match Test]]
- `docs/rollout-evidence/land-records-recon-2026-04-24/tangie-williams-field-test.json`
- `docs/rollout-evidence/probate-smoke-2026-04-24/priority_keep_now_enriched.json`
- `docs/rollout-evidence/contact-candidate-packets-2026-04-24/contact_candidate_packets.json`
- `docs/rollout-evidence/hcad-match-test-2026-04-24/hcad_match_results.json`

## Current open gates

- Harris Clerk document images require authorized login; do not bypass CAPTCHA/login.
- HCAD account/property matching still needs to resolve legal descriptions like `FALLBROOK Sec 3 Lot 1181 Block 24`.
- Free people-search sites may block cloud/browser-automation environments; treat this as an access gate.
- Paid skiptrace should receive normalized contact-candidate packets, not raw probate rows.
- HCAD/property matching must stay separate from tax overlay; if tax parser output is weak, mark it soft instead of storing fake delinquency certainty.
- Ares needs first-class evidence graph models before this becomes a repeatable operator workflow.

## Links

- [[Curative Title Operating Model]]
- [[Browser Harness Research Workflow]]
- [[County Land Records Playbook]]
- [[Evidence Graph Data Model]]
- [[Skiptrace Workflow]]
- [[Tangie Williams Field Test]]
- [[Contact Candidate Packet Test]]
- [[HCAD Property Match Test]]
