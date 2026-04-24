# Contact Candidate Packet Test — 2026-04-24

## Result

Generated **12** contact-candidate packets from the enriched Harris County probate keep-now set.

This test does **not** contact anyone and does **not** treat a probate party as a confirmed owner. It creates the normalized input packet needed before a paid skiptrace provider gets involved.

## Why this test matters

- Free skiptrace sources were blocked/unreliable in the browser harness.
- Paid skiptrace should not be fed raw court rows like a garbage disposal with a credit card attached.
- Ares needs clean candidate packets with source lineage, candidate roles, addresses, confidence, and requested enrichment outputs.

## Top packets

### 543678 — Tangie Renee Williams

- Status: `ready_for_paid_skiptrace`
- Packet confidence score: **100**
- Filing: APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
- Known applicant address: 1614 Royal Grantham Ct, Houston TX 77073
- Candidate contacts: 6
  - Brittany C Edwards (`applicant_or_executor`) — 1614 Royal Grantham Ct, Houston TX 77073
  - Frederick L Phillips (`respondent_or_heir_candidate`)
  - Christopher Dewanye Mcfadden (`respondent_or_heir_candidate`)
  - Jordan Anthony Brown (`respondent_or_heir_candidate`)
  - Laporchea Michelle Mcfadden (`respondent_or_heir_candidate`) — 2805 S. Park Ave, Apt 117, Tucson AZ 85713
  - Don D. Ford, III (`attorney_ad_litem_or_court_appointee`)
- Land-record threads:
  - `fallbrook_sec3_lot1181_blk24` — FALLBROOK Sec: 3 Lot: 1181 Block: 24 (high)
  - `perkins_w_abstract621_4_673_acres` — PERKINS W; 4.673 acres; Abstract 621 (medium_high)
- Key friction clues:
  - APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
  - 04/21/2026: Order to Appoint Aty or Gdn Ad Ltm - DON D. FORD, III
  - 04/21/2026: Proof of Heirship by Publication
  - 04/20/2026: Notice of Deposit of Funds for Potential Attorney Ad Litem

### 525833-401 — Daniel R. Montoya

- Status: `ready_for_paid_skiptrace`
- Packet confidence score: **85**
- Filing: APP TO DETERMINE HEIRSHIP
- Known applicant address: 4044 Basswood Dr, Dickinson TX 77539
- Candidate contacts: 5
  - Annette Montoya (`applicant_or_executor`) — 4044 Basswood Dr, Dickinson TX 77539
  - Larence Montoya (`respondent_or_heir_candidate`)
  - Adam R Montoya (`respondent_or_heir_candidate`)
  - Maria Silva (`respondent_or_heir_candidate`)
  - Monica Heimlich (`respondent_or_heir_candidate`)
- Key friction clues:
  - APP TO DETERMINE HEIRSHIP
  - 04/22/2026: Case Initiated Application (OCA) - Original Application for Partition and Distribution of Heirs Property

### 543652 — Janet Marie Mcmahan

- Status: `ready_for_paid_skiptrace`
- Packet confidence score: **65**
- Filing: APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
- Known applicant address: 5073 N. Nelson Dr, Katy TX 77493
- Candidate contacts: 1
  - Patrick Kelly McMahan (`applicant_or_executor`) — 5073 N. Nelson Dr, Katy TX 77493
- Key friction clues:
  - APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
  - 04/21/2026: Notice of Deposit of Funds for Potential Attorney Ad Litem
  - 04/21/2026: Attorney Appointee Fee Deposited
  - 04/20/2026: Application to Appoint Aty or Gdn Ad Ltm

### 543650 — David Mark Lemons

- Status: `ready_for_paid_skiptrace`
- Packet confidence score: **65**
- Filing: APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
- Known applicant address: 6750 Shining Sumac Ave, Houston TX 77084
- Candidate contacts: 1
  - James Corwin Lemons (`applicant_or_executor`) — 6750 Shining Sumac Ave, Houston TX 77084
- Key friction clues:
  - APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
  - 04/20/2026: Proof of Heirship by Publication

### 543672 — Cindy Seltzer

- Status: `ready_for_paid_skiptrace`
- Packet confidence score: **65**
- Filing: APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
- Known applicant address: 13018 Scenic Ritter St, Hedwig TX 78152
- Candidate contacts: 1
  - Megan Galindo (`applicant_or_executor`) — 13018 Scenic Ritter St, Hedwig TX 78152
- Key friction clues:
  - APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP
  - 04/22/2026: Notice of Deposit of Funds for Potential Attorney Ad Litem
  - 04/22/2026: Attorney Appointee Fee Deposited
  - 04/21/2026: Application to Appoint Aty or Gdn Ad Ltm

## Paid skiptrace provider input shape

Each packet now provides:

- `names` — living candidate names only; decedent is explicitly excluded
- `addresses` — applicant/respondent addresses extracted from case detail when present
- `county_context` — Harris County, Texas
- `decedent_context` — estate/decedent link for disambiguation
- `property_context` — legal descriptions when land-record threads exist
- `requested_outputs` — phones, mailing addresses, living/deceased status, relatives/associates, address history, property ownership hints

## Gaps exposed

- Most probate-only packets still lack land-record/property confirmation.
- Tangie is the strongest packet because she has probate parties plus Harris Clerk real-property metadata and alias/property threads.
- Harris Clerk document images still require authorized login; document text/images were not pulled or bypassed.
- HCAD matching remains a separate gate and should run before tax overlay or final outreach.

## Output files

- `docs/rollout-evidence/contact-candidate-packets-2026-04-24/contact_candidate_packets.json`
- `docs/rollout-evidence/contact-candidate-packets-2026-04-24/REPORT.md`
