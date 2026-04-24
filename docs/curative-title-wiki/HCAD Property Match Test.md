---
title: HCAD Property Match Test
status: active
updated_at: 2026-04-24
---

# HCAD Property Match Test

This page documents the first property-matching pass after contact-candidate packets.

## Rule

HCAD/property matching is a separate gate from:

- probate intake
- contact-candidate extraction
- paid skiptrace
- tax delinquency overlay
- outreach readiness

A probate party is not a confirmed property owner until HCAD, land records, or document images support the connection.

## Current test output

- Report: `docs/rollout-evidence/hcad-match-test-2026-04-24/REPORT.md`
- JSON: `docs/rollout-evidence/hcad-match-test-2026-04-24/hcad_match_results.json`
- HCAD database used: `/home/workspace/HCAD_Query/hcad.duckdb`

## Cases tested

### `543678` — Tangie Renee Williams

Status: `matched_property_thread`

Confirmed HCAD property:

- Account: `1091100001181`
- Owner: `WILLIAMS TANGIE`
- Site address: `1407 GREEN TRAIL DR`
- Legal: `LT 1181 BLK 24` / `FALLBROOK SEC 3`
- Market value: `$245,311`

Why it matters:

The Harris Clerk land-record thread said `FALLBROOK Sec 3 Lot 1181 Block 24`. HCAD matched the same lot/block/section and owner signal. This is now the best current curative-title field-test lead.

Important caveat:

Brittany Edwards’s `1614 Royal Grantham Ct` property matched HCAD too, but that is applicant/contact context, not the target title-thread property.

### `525833-401` — Daniel R. Montoya

Status: `ambiguous_hcad_candidates`

HCAD found multiple `Daniel Montoya` owner candidates and one `Larence/Lawrence Montoya` respondent-name candidate, but the probate packet does not expose a property address or legal description yet.

Next gate:

Pull partition/application document detail when authorized document access is available, or extract property clues from any accessible case/detail text.

### `543652` — Janet Marie Mcmahan

Status: `matched_applicant_decedent_address_property`

Confirmed HCAD property:

- Account: `1172610010016`
- Owner: `MCMAHAN PATRICK K and JANET`
- Site/mailing address: `5073 N NELSON AVE`
- Legal: `LT 16 BLK 1` / `MORRISON BOULEVARD PLACE R/P`
- Market value: `$323,264`

Why it matters:

The probate applicant/address signal matched HCAD cleanly. This is a strong person/property packet, but still needs land-record review before calling it a curative-title opportunity.

## Tax overlay note

A live hctax check was attempted for the confirmed Tangie and McMahan accounts. It returned no delinquency signal, but the current `hctax_client` parser misread owner/value fields on those tax statement pages. Treat that as a soft no-delinquency signal only.

Before Ares stores final tax overlay fields, harden the parser and save raw parse evidence safely.

## Next states

- Tangie: `needs_paid_skiptrace_or_document_image_review`
- Montoya: `needs_partition_document_image_or_case_property_extraction`
- McMahan: `needs_land_record_search_then_paid_skiptrace`

## Cross-links

- [[Contact Candidate Packet Test]]
- [[Tangie Williams Field Test]]
- [[Evidence Graph Data Model]]
- [[Skiptrace Workflow]]
