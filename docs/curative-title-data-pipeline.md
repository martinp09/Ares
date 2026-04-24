# Curative Title Data Pipeline

Status: planning / workflow doctrine  
Branch: `test/production-readiness-handoff`  
Purpose: define the evidence-first workflow for curative-title leads before skiptrace or outreach.

## Core correction

Curative title is **not probate-first**.

Probate filings are one source of party clues, but the central evidence layer is land-record document review: deeds, affidavits, probate-related recordings, liens, releases, powers of attorney, transfer-on-death deeds, life estate instruments, and related recorded documents.

The business question is not merely “who filed probate?”

The business question is:

> Who owns, inherited, controls, claims, or may have partial rights in this property, and how can we prove enough of that chain to contact the right living people?

## Foundational workflow method: browser harness

Browser harness / Hermes browser automation is a foundational method for this pipeline.

Reason:

- county systems are fragmented, old, and inconsistent;
- many portals are ASP.NET WebForms or JavaScript-heavy apps;
- document detail pages, image viewers, postbacks, signed image URLs, and search forms often do not expose clean public APIs;
- the browser gives the most faithful view of what a human title researcher actually sees;
- browser-driven research is faster and more accurate for exploratory county workflows than prematurely building brittle scripts.

Scripts are still useful when:

- a browser workflow has already been proven;
- the extraction pattern is stable;
- the script is integrated into Ares as a repeatable adapter;
- the script preserves raw evidence, source URLs, timestamps, and confidence decisions.

Default posture:

1. use browser harness to discover and verify the workflow;
2. save raw evidence and screenshots/HTML/text where appropriate;
3. only then promote stable pieces into scripts or Ares adapters.

## Lead pipeline

### 1. Lead intake

Potential sources:

- probate cases;
- appraisal records showing `ESTATE OF` / deceased-owner patterns;
- tax delinquency overlays;
- land-record searches for heirship / estate / deceased / probate instruments;
- foreclosure, lien, or distress filings;
- owner name and mailing-address anomalies.

### 2. Property identity

Normalize and preserve:

- county;
- appraisal account / parcel id;
- situs/property address;
- mailing address;
- legal description;
- subdivision, lot, block, section, abstract, tract;
- current record owner;
- prior owners;
- source URLs and timestamps.

### 3. Land-record document review

Search official county land records for:

- decedent name;
- estate name;
- current owner name;
- prior owner name;
- applicant/executor/heir names;
- grantor/grantee variants;
- legal description;
- subdivision / lot / block / abstract;
- instrument numbers from related docs.

High-value instruments:

- Affidavit of Heirship;
- Small Estate Affidavit;
- Probate Proceedings;
- Certified Copy of Probated Will;
- Warranty Deed;
- Special Warranty Deed;
- Quitclaim Deed;
- Executor's Deed;
- Administrator's Deed;
- Trustee's Deed;
- Transfer on Death Deed;
- Life Estate Agreement;
- Power of Attorney;
- Deed of Trust;
- Release;
- Lien;
- Foreclosure / substitute trustee documents.

### 4. Chain and party graph

Build a graph, not just a flat lead row.

Entities:

- property;
- recorded document;
- probate case;
- person;
- estate;
- entity/trust;
- attorney / ad litem;
- contact point;
- source evidence.

Relationships:

- person owns property;
- person previously owned property;
- estate/decedent tied to property;
- person is heir / grantee / grantor / applicant / executor / administrator / trustee / affiant;
- document transfers or clouds interest;
- probate case references decedent or estate;
- contact point belongs to person with confidence.

The target output is a ranked list of living people who may hold, control, or influence partial rights in the property.

### 5. Free skiptrace and open-source contact discovery

Before paid skiptrace, use free/open web sources where appropriate:

- TruePeopleSearch;
- CyberBackgroundChecks;
- county appraisal mailing address;
- recorded document mailing addresses;
- probate applicant addresses;
- secretary of state / registered agent clues where entities are involved;
- obituary / funeral home pages;
- social/profile/public web confirmation;
- USPS/address normalization if available.

Rules:

- do not skiptrace the decedent as a contact target;
- use decedent information only to identify relatives/heirs/estate contacts;
- preserve source and confidence for every contact clue;
- mark uncertain matches for manual review;
- apply suppression/compliance checks before outreach.

### 6. Paid skiptrace later

Paid skiptrace belongs after the party graph exists.

Inputs should be living candidate contacts, not raw property rows:

- full name;
- role in title/probate chain;
- last known address;
- associated property address;
- county/state;
- source document IDs;
- confidence basis.

### 7. Outreach readiness

A lead is outreach-ready only when Ares can explain:

- property identity;
- title/ownership problem;
- candidate contact target;
- why that person may have rights or control;
- best contact address/phone/email;
- confidence score;
- suppression status;
- next recommended action.

Possible statuses:

- `needs_land_record_review`;
- `needs_document_image_review`;
- `needs_hcad_match`;
- `needs_heir_graph`;
- `ready_for_free_skiptrace`;
- `ready_for_paid_skiptrace`;
- `ready_for_manual_review`;
- `ready_for_direct_mail`;
- `blocked_low_confidence`;
- `blocked_suppressed`.

## County-specific starting points

### Harris County

Official land-record index:

`https://www.cclerk.hctx.net/Applications/WebSearch/RP.aspx`

Practical notes:

- index metadata is publicly searchable;
- document images appear login-gated behind the county registration flow;
- browser automation is best for search/postback/result review;
- do not bypass CAPTCHA or gated document access;
- store document references and image availability separately.

### Montgomery County

Official public search:

`https://montgomery.tx.publicsearch.us/`

Practical notes:

- supports quick search, advanced search, party names, full text/OCR, date windows, legal descriptions;
- document details and preview images were visible in browser testing;
- image URLs can be temporary/signed, so store canonical document page URLs and metadata;
- browser automation is the right first-class method.

## Ares implementation implications

Ares should add first-class models or fields for:

- recorded documents;
- document parties;
- legal descriptions;
- document images / image access status;
- evidence snippets;
- person/property/probate/document relationship edges;
- contact clues;
- skiptrace candidates;
- outreach eligibility decisions.

Do not flatten this too early into a single `lead` row. Curative title needs evidence lineage because the deal thesis depends on the details.

## Near-term smoke test

Use the 12 priority probate/heirship cases already captured in rollout evidence as seed inputs, but treat them as only one lead source.

Smoke objective:

1. For each seed person/property clue, use browser harness to search Harris and Montgomery land records.
2. Capture matching recorded-document metadata.
3. Extract grantor/grantee/party/legal-description clues.
4. Build a provisional heir/descendant/partial-rights graph.
5. Run free-source skiptrace reconnaissance for candidate living contacts.
6. Produce an Ares-ready evidence package and recommended next action per lead.

No live outreach. No paid skiptrace. No document-login bypass.
