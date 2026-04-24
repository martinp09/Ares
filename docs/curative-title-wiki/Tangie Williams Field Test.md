---
title: Tangie Williams Field Test
status: active
updated_at: 2026-04-24
---

# Tangie Williams Field Test

Seed:

- Harris probate case: `543678`
- decedent: Tangie Renee Williams
- filing: Application for Independent Administration with Heirship
- applicant: Brittany C Edwards
- applicant address: 1614 Royal Grantham Ct, Houston TX 77073
- respondent/heir candidates:
  - Frederick L Phillips
  - Christopher Dewanye Mcfadden
  - Jordan Anthony Brown
  - Laporchea Michelle Mcfadden

## Why this case

This case is messy enough to test the real workflow:

- open heirship case;
- proof by publication;
- attorney ad litem;
- multiple heir/respondent candidates;
- land-record aliases.

## Harris land-record search

Source:

`https://www.cclerk.hctx.net/Applications/WebSearch/RP.aspx`

Search:

- field: Grantor
- query: `Williams Tangie`

## Property thread A: Fallbrook

Legal:

`FALLBROOK Sec 3 Lot 1181 Block 24`

Aliases/people observed:

- Tangie Williams;
- Tangie W McFadden;
- Tangie Williams Brown;
- Tangie B Williams;
- Bobby Brown.

High-value records:

- `RP-2022-274022` — 2022 modification to MidFirst Bank;
- `RP-2017-563067` — 2017 modification to Chase/JPMorgan chain;
- `RP-2017-563055` — 2017 deed of trust to HUD;
- `X177166` — 2003 deed of trust with Bobby Brown / Tangie;
- `V302389` — 2001 contract connecting Tangie W McFadden / Williams to Bobby Brown;
- `V302388` — 2001 deed of trust to SBA;
- `U130254`, `U130253`, `U130252` — 1999 origin/finance records.

Assessment: strongest current property candidate.

## Property/family thread B: Perkins / Otis Williams Estate

Legal:

`PERKINS W; 4.673 acres; Abstract 621`

Associated names:

- Tangie Williams;
- Otis Ladell Williams;
- Williams Otis Estate;
- Joanne/Joan Greene;
- Sandra/Sandra Harris Williams.

High-value records:

- `W397757` — 2003 affidavit tied to Williams Otis Estate;
- `W383936` — 2003 affidavit tied to same estate;
- `W397760` — 2003 warranty deed;
- `W501407` — 2003 warranty deed.

Assessment: likely useful for family/heir mapping even if not the current target property.

## Document image boundary

Tested exact file-number lookups:

- `RP-2022-274022`
- `W397757`

Both document links route through `EComm/ViewEdocs.aspx?...` and redirect to Harris Clerk `Registration/Login.aspx`.

Related-docs postback for `RP-2022-274022` exposed:

- `X177166` — Related Harris County Real Property File Number

Conclusion:

- index metadata is publicly collectable;
- related-doc metadata is browser-collectable;
- document images require authorized Harris Clerk login;
- do not bypass login/CAPTCHA.

## Free skiptrace boundary

Tried:

- TruePeopleSearch;
- CyberBackgroundChecks;
- Bing.

Result: blocked by Cloudflare/challenge in this environment.

Conclusion: free-source skiptrace likely needs a different browser environment, manual/residential session, or approved provider path.

## Evidence files

- `docs/rollout-evidence/land-records-recon-2026-04-24/REPORT.md`
- `docs/rollout-evidence/land-records-recon-2026-04-24/tangie-williams-field-test.json`

## Next actions

1. Authorized Harris Clerk login for document images.
2. Pull/view `RP-2022-274022`, `X177166`, `W397757`, `W383936`.
3. OCR/extract vesting language, affiants, heirs, spouse/co-borrower, addresses.
4. Resolve Fallbrook legal description to HCAD account/property address.
5. Build Ares evidence graph from the extracted facts.

## Cross-links

- [[County Land Records Playbook]]
- [[Evidence Graph Data Model]]
- [[Skiptrace Workflow]]
