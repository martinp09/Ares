# Bankruptcy Records as Distressed-Title Deal Sources

## Thesis

Bankruptcy records are an additional source lane to keep in mind — **not a pivot away from the existing lead-machine strategy**. They can surface distressed-title opportunities that do **not** show up on the common tax-sale list path. When a borrower files Chapter 7 or Chapter 13, the automatic stay under `11 U.S.C. § 362` can stop foreclosure and freeze the situation in place. Many operators treat that as a dead deal; for curative-title work it can be a paper-problem lane.

The opportunity is not “bankruptcy = buy.” The opportunity is where bankruptcy records reveal a compressed timeline, stacked liens, discharged personal liability, unreleased instruments, avoidable judgments, foreclosure timing, or title-insurance blockers that leave the owner/heirs stuck.

## High-Value Signals

Look for filings tied to real property with:

- Chapter 7 or Chapter 13 case context.
- Multiple liens stacked on title.
- Old mortgages where personal liability may have been discharged but the lien/release problem remains unresolved.
- Judgments that may be avoidable under `11 U.S.C. § 522(f)`.
- Title companies likely to say they cannot insure without curative work.
- Foreclosure timeline pressure, especially where a lender has requested or obtained relief from stay.
- Heir/estate ownership plus bankruptcy/foreclosure/lien friction.

## Why This Lane Matters

Bankruptcy does not clean title by itself. It can freeze or expose the title problem:

- Owners may believe they have no options.
- Ordinary buyers cannot get financing.
- Wholesalers often do not know how to structure the situation.
- Title companies may refuse to insure until paper defects are resolved.
- Competition is lower than tax-sale lists because fewer investors understand the records.

The compressed timeline is often the pain point. The clouded title is often the competition moat.

## Research Workflow

1. Pull bankruptcy records from PACER or other authorized bankruptcy-record access.
2. Identify debtor names, property addresses, schedules, secured creditors, exemptions, lien/judgment entries, and case chapter/status.
3. Cross-reference property identity in land records and appraisal/tax records.
4. Check foreclosure timeline and whether any lender filed for relief from stay.
5. Build a lien/title thesis:
   - what liens exist;
   - what may have been discharged personally;
   - what instruments still cloud title;
   - what judgments may need legal review;
   - what title insurer objections are likely.
6. Route to curative-title review before outreach or acquisition strategy.

## Evidence Fields to Capture in Ares

- `bankruptcy_case_number`
- `court`
- `chapter`: Chapter 7 / Chapter 13
- `filing_date`
- `case_status`
- `debtor_names`
- `property_address`
- `scheduled_property_value`
- `secured_creditors`
- `lien_claims`
- `judgment_claims`
- `exemptions_claimed`
- `automatic_stay_status`
- `relief_from_stay_motion_status`
- `foreclosure_timeline_clues`
- `land_record_instruments`
- `title_cloud_thesis`
- `needs_attorney_review`
- `source_documents`

## Guardrails

- Do not give legal advice or claim a lien/judgment is avoidable without attorney review.
- Do not imply bankruptcy eliminated a lien unless the record and legal review support it.
- Treat bankruptcy as an evidence source and timeline signal, not automatic outreach eligibility.
- Respect automatic-stay constraints and route any live negotiation/legal timing questions through qualified counsel.
- Preserve source lineage: PACER docket/schedules, foreclosure records, land-record instruments, tax/appraisal records.

## Operational Positioning

This lane fits the curative-title strategy because it favors situations where:

- the seller/owner/heirs are stuck by paperwork;
- conventional buyers and lenders are blocked;
- the cure path requires understanding title, liens, foreclosure timing, and bankruptcy posture;
- competition is lower than obvious tax-sale lists.
