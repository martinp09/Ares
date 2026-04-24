---
title: County Land Records Playbook
status: active
updated_at: 2026-04-24
---

# County Land Records Playbook

This page records the first county-specific land-record workflows for curative-title research.

## Harris County Clerk Real Property

Official source:

`https://www.cclerk.hctx.net/Applications/WebSearch/RP.aspx`

Searchable fields observed:

- file number;
- film code;
- date range;
- grantor;
- grantee;
- trustee;
- subdivision / description;
- instrument type;
- volume/page;
- section, lot, block, unit, abstract, outlot, tract, reserve.

Useful search patterns:

- decedent as grantor and grantee;
- estate name as grantor/grantee;
- applicant/executor/heir names as grantor/grantee;
- known aliases and married names;
- legal description pieces;
- exact file numbers from related docs;
- instrument type filters when the result set is too broad.

High-value Harris instrument types:

- `AFFT` — affidavit / affidavit of heirship / small estate style evidence;
- `PROB` — probate proceedings;
- `WILL` — certified copy of probated will;
- `W/D` — warranty deed;
- `QCD` — quitclaim deed;
- `D/T` — deed of trust;
- `MODIF` — modification;
- `REL` — release;
- liens, life estate agreements, powers of attorney, foreclosure/substitute trustee documents.

Access boundary:

- index metadata is publicly searchable;
- document image links point to `EComm/ViewEdocs.aspx?...`;
- opening image/document links redirects to Harris Clerk registration/login;
- do not bypass login/CAPTCHA;
- related-docs postbacks can expose linked file numbers without image access.

## Montgomery County PublicSearch

Official source:

`https://montgomery.tx.publicsearch.us/`

Observed capabilities:

- quick search;
- advanced search;
- party names;
- grantor/grantee;
- notary;
- recorded date range;
- document numbers;
- document type;
- volume/page;
- image code;
- full-text/OCR;
- legal description fields.

Important distinction:

- Montgomery document detail pages and preview images were visible in browser testing.
- Image URLs are signed/temporary, so store canonical document page URLs and extracted metadata, not expiring image links.

## Document review priorities

Prioritize images/details for:

1. recent active property documents;
2. affidavits of heirship;
3. deeds after estate/affidavit activity;
4. documents with related-doc links;
5. documents showing alias changes, spouses, co-borrowers, trustees, or family relationships.

## Cross-links

- [[Browser Harness Research Workflow]]
- [[Evidence Graph Data Model]]
- [[Tangie Williams Field Test]]
