---
title: Curative Title Operating Model
status: active
updated_at: 2026-04-24
---

# Curative Title Operating Model

Curative-title work is not a probate workflow with extra steps. It is an evidence workflow centered on land records.

## Core principle

The question is:

> Who owns, inherited, controls, claims, or may have partial rights in this property, and what evidence proves enough of that chain to contact the right living people?

Probate can identify a decedent, applicant, executor, administrator, heir, attorney, or ad litem. It does not by itself prove the full property-rights picture.

## Pipeline

```text
Lead clue
  -> property identity
  -> land-record document review
  -> party/alias/legal-description extraction
  -> evidence graph
  -> HCAD/property match
  -> tax overlay
  -> living contact candidates
  -> free skiptrace
  -> paid skiptrace if needed
  -> suppression/compliance
  -> outreach readiness
```

## Source types

Lead clues can come from:

- land records;
- appraisal records showing `ESTATE OF` / deceased-owner patterns;
- probate cases;
- affidavits of heirship;
- deeds involving estates, executors, administrators, heirs, trustees, or family members;
- tax delinquency overlays;
- liens, releases, foreclosures, and distressed filings;
- mailing-address / owner-name anomalies.

## Why land records come first

Land records expose:

- vesting language;
- grantor/grantee chains;
- identity aliases;
- legal descriptions;
- heirship affidavits;
- family/estate relationship statements;
- co-borrower, spouse, trustee, or entity clues;
- related documents and document numbers;
- historical ownership chains that probate filings may omit.

## Ares output target

Ares should not flatten curative-title work into one generic lead row too early.

Minimum output per lead:

- property identity;
- title/ownership issue;
- candidate living contacts;
- why each contact may matter;
- source evidence for that claim;
- confidence score;
- suppression state;
- next recommended action.

## Cross-links

- [[Browser Harness Research Workflow]]
- [[County Land Records Playbook]]
- [[Evidence Graph Data Model]]
- [[Skiptrace Workflow]]
