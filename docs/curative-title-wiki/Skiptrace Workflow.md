---
title: Skiptrace Workflow
status: active
updated_at: 2026-04-24
---

# Skiptrace Workflow

Skiptrace comes after evidence graph construction, not before.

## Rule

Do not skiptrace the decedent as a contact target.

Use decedent data to identify living candidate contacts:

- heirs;
- descendants;
- devisees;
- surviving spouse;
- executor / administrator;
- applicant;
- trustee;
- entity principal;
- current record owner;
- co-owner or co-borrower.

## Free-source first

Free/open-source skiptrace can use:

- TruePeopleSearch;
- CyberBackgroundChecks;
- appraisal mailing address;
- recorded document mailing/vesting addresses;
- probate applicant addresses;
- obituaries and funeral-home pages;
- Secretary of State / registered agent clues;
- public social/web profiles;
- USPS/address normalization where available.

## Access warning

In the Tangie Williams field test, TruePeopleSearch, CyberBackgroundChecks, and Bing blocked the cloud/browser environment with Cloudflare/challenge pages.

Interpretation:

- free-source skiptrace is still useful;
- access may require a residential/manual browser session or alternate source;
- do not treat blocked access as no-match;
- do not bypass site protections.

## Paid skiptrace later

Paid skiptrace should receive living candidate contacts, not raw property/probate rows.

The current tested input layer is the [[Contact Candidate Packet Test]]. Build that packet first, then send only the candidate-contact fields to a provider.

Inputs:

- full name;
- aliases;
- role in evidence graph;
- last known address;
- associated property address or legal description;
- source document IDs;
- decedent/estate context for disambiguation;
- confidence basis;
- explicit `do_not_skiptrace` decedent list.

Outputs should normalize into Ares-owned contact models, not raw vendor payload dependencies.

## Suppression before outreach

Before outreach, Ares should check:

- internal opt-out;
- deceased flag;
- DNC / TCPA risk;
- bad confidence;
- attorney/represented-party policy;
- previous outreach cooldown;
- wrong-number/reassigned-number evidence;
- household/property-level opt-out.

## Outreach readiness

A contact is ready only when Ares can explain:

- who the person is;
- why the person may matter to the property rights;
- what evidence supports that relationship;
- what contact channels are available;
- what suppression/compliance checks passed;
- what next action is recommended.

## Cross-links

- [[Evidence Graph Data Model]]
- [[Browser Harness Research Workflow]]
- [[Tangie Williams Field Test]]
- [[Contact Candidate Packet Test]]
