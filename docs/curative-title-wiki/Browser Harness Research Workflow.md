---
title: Browser Harness Research Workflow
status: active
updated_at: 2026-04-24
---

# Browser Harness Research Workflow

Hermes browser harness is a foundational method for curative-title research.

## Why browser-first

County systems are fragmented, old, inconsistent, and often hostile to clean API assumptions.

Common portal traits:

- ASP.NET WebForms;
- `__VIEWSTATE` / `__EVENTVALIDATION` postbacks;
- JavaScript-heavy search interfaces;
- signed/temporary image URLs;
- login-gated document viewers;
- CAPTCHA or email-confirmation registration;
- related-document popups that only exist after browser postbacks.

A browser gives the most faithful view of what a human title researcher sees. That is more accurate than inventing brittle scripts before the workflow is understood.

## Ownership split

```text
Hermes browser harness
  -> county portal research / screenshots / raw extraction
  -> evidence package
  -> Ares API
  -> durable evidence graph + lead state
  -> Mission Control review queue
```

Hermes owns:

- browser-harness navigation through county portals;
- exploratory research on weird WebForms/SPA sites;
- document-image review when a human-authenticated session is required;
- OCR/summarization/extraction from viewed documents;
- operator decisions and manual confirmations.

Ares owns:

- canonical property/person/document/probate/contact models;
- evidence graph and source lineage;
- deterministic confidence scoring;
- skiptrace candidate state;
- suppression/compliance state;
- outreach-readiness status;
- Mission Control queues and audit trail.

## Promotion rule

Scripts/adapters are optional later.

1. Prove the workflow with browser harness.
2. Save raw evidence, URLs, screenshots/HTML/text where appropriate.
3. Identify stable repetitive steps.
4. Promote only stable steps into scripts or Ares adapters.
5. Keep document-image review human-authenticated when the county requires login/CAPTCHA.

## Evidence capture checklist

For every browser-harness research pass, capture:

- source name;
- source URL;
- search criteria;
- timestamp/date;
- result rows;
- document numbers / film codes;
- grantor/grantee/party names;
- legal description;
- image availability and access status;
- login/CAPTCHA/access blockers;
- confidence and next action.

## Red lines

- Do not bypass login/CAPTCHA.
- Do not represent index metadata as final title proof.
- Do not store temporary signed image URLs as canonical evidence.
- Do not call a contact ready until evidence graph + suppression state support it.

## Cross-links

- [[Curative Title Operating Model]]
- [[County Land Records Playbook]]
- [[Evidence Graph Data Model]]
