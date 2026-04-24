---
title: Evidence Graph Data Model
status: active
updated_at: 2026-04-24
---

# Evidence Graph Data Model

Curative-title leads need an evidence graph, not a flat row.

## Entities

Minimum entities:

- `PropertyThread`
- `Property`
- `LegalDescription`
- `RecordedDocument`
- `DocumentParty`
- `ProbateCase`
- `Person`
- `PersonAlias`
- `Estate`
- `ContactCandidate`
- `ContactPoint`
- `EvidenceEdge`
- `ResearchTask`
- `OutreachEligibilityDecision`

## Core relationships

Examples:

```text
Person -> alias -> PersonAlias
Person -> party_on -> RecordedDocument
RecordedDocument -> describes -> LegalDescription
LegalDescription -> maps_to -> Property
ProbateCase -> references -> Estate
Estate -> decedent -> Person
Person -> candidate_heir_of -> Person
Person -> may_control_interest_in -> PropertyThread
ContactCandidate -> backed_by -> EvidenceEdge
```

## Evidence edge fields

Each evidence edge should preserve:

- source system;
- source URL;
- source record ID / document number;
- observed text snippet;
- extraction method;
- extracted_at timestamp;
- confidence;
- reviewer status;
- notes.

## Research statuses

Useful statuses:

- `needs_land_record_search`
- `needs_document_image_review`
- `needs_hcad_match`
- `needs_tax_overlay`
- `needs_heir_graph`
- `ready_for_free_skiptrace`
- `ready_for_paid_skiptrace`
- `ready_for_manual_review`
- `ready_for_direct_mail`
- `blocked_low_confidence`
- `blocked_suppressed`

## Confidence principles

Higher confidence:

- same person appears across probate + land record + appraisal;
- exact legal description match;
- recorded document states relationship or capacity;
- recent active property instrument;
- multiple aliases converge on the same property thread.

Lower confidence:

- name-only match;
- no property/legal description tie;
- stale unrelated family-chain record;
- common surname without address/property support;
- OCR-only evidence without document review.

## Why this matters

The outreach target is not “the probate lead.”

The outreach target is the living person with a plausible and evidenced relationship to the property interest.

Ares must be able to explain why that person matters before the lead leaves research mode.

## Cross-links

- [[Curative Title Operating Model]]
- [[Skiptrace Workflow]]
- [[Tangie Williams Field Test]]
