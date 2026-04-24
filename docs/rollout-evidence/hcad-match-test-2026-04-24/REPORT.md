# HCAD Property Match Test — 2026-04-24

## Result

Tested the top three contact-candidate packets against the local HCAD DuckDB.

- Cases tested: `543678`, `525833-401`, `543652`
- Matched/property-confirmed: **2**
- Ambiguous/no confirmed property: **1**

## Findings

### 543678 — Tangie Renee Williams

- Status: `matched_property_thread`
- Confidence: **high**
- HCAD account: `1091100001181`
- Owner: `WILLIAMS TANGIE`
- Site address: `1407 GREEN TRAIL DR`, Houston
- Legal: `LT 1181 BLK 24` / `FALLBROOK SEC 3`
- Market value: `$245,311`
- Why it matters: this exactly ties the Harris Clerk Fallbrook thread to an HCAD taxable property.
- Caveat: Brittany Edwards’s 1614 Royal Grantham property is applicant/contact context, **not** the target property.

### 525833-401 — Daniel R. Montoya

- Status: `ambiguous_hcad_candidates`
- Confidence: **low until the partition document or case detail exposes the property**
- HCAD found multiple Daniel Montoya owner candidates and one Larence/Lawrence Montoya respondent-name candidate.
- No HCAD account is confirmed for this probate packet yet.
- Still a strong contact packet because the filing says `Original Application for Partition and Distribution of Heirs Property`.

### 543652 — Janet Marie Mcmahan

- Status: `matched_applicant_decedent_address_property`
- Confidence: **high for person/address match; medium until land records prove title-friction opportunity**
- HCAD account: `1172610010016`
- Owner: `MCMAHAN PATRICK K and JANET`
- Site/mailing address: `5073 N NELSON AVE`, Katy
- Legal: `LT 16 BLK 1` / `MORRISON BOULEVARD PLACE R/P`
- Market value: `$323,264`

## Tax overlay note

A live hctax check was attempted for the two confirmed accounts. It returned no delinquency signal, but the existing parser misread owner/value fields on the tax statement pages, so this should be treated as a **soft no-delinquency signal**, not final stored tax evidence. Parser hardening is now a real follow-up if we want automated tax overlay inside Ares.

## Next states

- Tangie: `needs_paid_skiptrace_or_document_image_review`
- Montoya: `needs_partition_document_image_or_case_property_extraction`
- McMahan: `needs_land_record_search_then_paid_skiptrace`

## Output files

- `docs/rollout-evidence/hcad-match-test-2026-04-24/hcad_match_results.json`
- `docs/rollout-evidence/hcad-match-test-2026-04-24/REPORT.md`
