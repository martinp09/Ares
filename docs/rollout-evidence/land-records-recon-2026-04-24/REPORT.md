# Curative Title Land-Records Recon Field Test — Tangie Renee Williams

Status: browser-harness field test  
Seed: Harris County probate case `543678`  
Source evidence: `docs/rollout-evidence/probate-smoke-2026-04-24/priority_keep_now_enriched.json`

## Why this seed

Picked `543678` because it is messy in the useful way:

- decedent: **Tangie Renee Williams**
- filing type: **Application for Independent Administration with Heirship**
- applicant: **Brittany C Edwards**
- applicant address: **1614 Royal Grantham Ct, Houston TX 77073**
- probate events include:
  - Proof of Heirship by Publication
  - attorney ad litem appointment/deposit
  - DOD clue: `2/9/26`
- respondent/heir candidates:
  - Frederick L Phillips
  - Christopher Dewanye Mcfadden
  - Jordan Anthony Brown
  - Laporchea Michelle Mcfadden

This gave multiple names to test against land records and free skiptrace surfaces.

## Browser-harness searches performed

### Harris County Clerk Real Property

Official source:

`https://www.cclerk.hctx.net/Applications/WebSearch/RP.aspx`

Search performed:

- field: `Grantor`
- query: `Williams Tangie`

Result: **hits found**.

### Harris County Tax Office delinquent search

Official source:

`https://www.hctax.net/Property/DelinquentTax`

Search performed:

- field: `Name`
- query: `Williams Tangie`

Result: no result from this name search. This does **not** prove no tax delinquency; it only proves this exact name query did not resolve the account. Need HCAD/account/property address first.

### Free-source skiptrace checks

Sources tried:

- TruePeopleSearch query for `Brittany C Edwards Houston TX`
- CyberBackgroundChecks query for `Brittany Edwards Houston TX`
- Bing query for `"Brittany C Edwards" "Houston"`

Result: all blocked by Cloudflare/challenge in this browser environment.

Interpretation: free skiptrace is still a valid workflow target, but this current browser environment is not enough for those sites. Need manual/residential browser session, another free source, or an approved API/provider path.

## Land-record hits that matter

The Harris real-property search exposed two property/title threads.

### Thread 1 — Fallbrook property candidate

Legal description:

`FALLBROOK Sec 3 Lot 1181 Block 24`

Associated names / aliases observed:

- Tangie Williams
- Tangie W McFadden
- Tangie Williams Brown
- Bobby Brown

High-value records:

| File | Date | Type | Key names | Why it matters |
|---|---:|---|---|---|
| `RP-2022-274022` | 05/25/2022 | MODIF | Brown Tangie / Brown Tangie W / Brown Tangie Williams / Williams Tangie → MidFirst Bank | Recent mortgage modification; property chain active close to death |
| `RP-2017-563067` | 12/22/2017 | MODIF | Brown Tangie Williams / Williams Tangie / Williams Tangie B → Chase/JPMorgan | Confirms alias/name variants and active mortgage chain |
| `RP-2017-563055` | 12/22/2017 | D/T | Brown Tangie Williams / Williams Tangie / Williams Tangie B → HUD | Likely reverse/HUD-related lien/deed-of-trust clue; image needed |
| `X177166` | 11/10/2003 | D/T | Bobby Brown / Brown Tangie Williams / Williams Tangie → Chase Manhattan Mtg | Bobby Brown relationship/property co-interest clue |
| `V302389` | 09/14/2001 | CONT | McFadden Tangie W / Williams Tangie → Bobby Brown | Connects McFadden alias to Brown/property thread |
| `V302388` | 09/14/2001 | D/T | McFadden Tangie W / Williams Tangie → SBA | Identity/property thread; potential business/debt clue |
| `U130254` | 12/16/1999 | NOTICE | Larkstone Bldg Co / Williams Tangie | Initial property/building notice clue |
| `U130253` | 12/16/1999 | D/T | Williams Tangie → Harris County | Early deed-of-trust/tax/public finance clue |
| `U130252` | 12/16/1999 | D/T | Williams Tangie → First Guaranty Financial Corp | Early finance chain |

Field-test assessment:

- This is the strongest property candidate.
- The 2022 modification makes it likely relevant to current title/contact work.
- Need document images for the 2022, 2017, 2003, and 2001 documents to identify marital/co-borrower/vesting language and possible current lien state.

### Thread 2 — Perkins W / Otis Williams estate chain

Legal description:

`PERKINS W; 4.673 acres; Abstract 621`

Associated names:

- Tangie Williams
- Otis Ladell Williams
- Williams Otis Estate
- Joanne/Joan Greene
- Sandra/Sandra Harris Williams

High-value records:

| File | Date | Type | Key names | Why it matters |
|---|---:|---|---|---|
| `W397757` | 01/31/2003 | AFFT | Greene Joanne / Williams Sandra Harris / Williams Tangie → Williams Otis Estate | Affidavit tied to estate; document image likely contains heir/family facts |
| `W383936` | 01/27/2003 | AFFT | Green Joanne / Williams Sandra / Williams Tangie → Williams Otis Estate | Another affidavit tied to same estate chain |
| `W397760` | 01/31/2003 | W/D | Otis Ladell Williams / Tangie Williams → H K Construction | Deed after estate affidavits; likely title transfer evidence |
| `W501407` | 03/14/2003 | W/D | Otis Ladell Williams / Tangie Williams → Huffsmith Kohrville Inc | Subsequent sale/transfer evidence |

Field-test assessment:

- This may not be the current target property, but it is highly valuable for family/heir mapping.
- The affidavit images are likely to name heirs/relationships around the Otis Williams estate.
- Those names can help prove Tangie’s family network and descendant chain.

## Provisional evidence graph

```text
Tangie Renee Williams, deceased
  aliases observed in land records:
    - Tangie Williams
    - Tangie W McFadden
    - Tangie Williams Brown
    - Tangie B Williams

  property thread A:
    FALLBROOK Sec 3 Lot 1181 Block 24
      connected parties:
        - Bobby Brown
        - Chase/JPMorgan/MidFirst/HUD/SBA/lenders
      key active clue:
        - 2022 mortgage modification

  property/family thread B:
    PERKINS W, 4.673 acres, Abstract 621
      connected estate:
        - Williams Otis Estate
      connected people:
        - Otis Ladell Williams
        - Joanne/Joan Greene
        - Sandra/Sandra Harris Williams
      key active clue:
        - 2003 affidavits + deeds

  probate case 543678:
    applicant:
      - Brittany C Edwards
    respondent/heir candidates:
      - Frederick L Phillips
      - Christopher Dewanye Mcfadden
      - Jordan Anthony Brown
      - Laporchea Michelle Mcfadden
```

## What this proves

This validates the corrected curative-title workflow:

1. Probate gives a decedent and candidate heirs.
2. Land records reveal property threads, aliases, and historical estate/family chains.
3. The real contact targets come from combining probate parties + land-record parties + document-image facts.
4. A flat probate lead row is not enough. Ares needs an evidence graph.

## Document image access check

I tested the image/document boundary instead of assuming it.

### `RP-2022-274022`

- Searched by exact file number.
- Result resolved to the same Fallbrook record.
- Film-code/document link points to `EComm/ViewEdocs.aspx?...`.
- Opening the document URL redirected to Harris Clerk `Registration/Login.aspx`.
- Related-docs postback worked and exposed one related document: `X177166`, labeled `Related Harris County Real Property File Number`.

### `W397757`

- Searched by exact file number.
- Result resolved to the Perkins W / Williams Otis Estate affidavit record.
- Film-code/document link also points to `EComm/ViewEdocs.aspx?...`.
- Opening the document URL redirected to Harris Clerk `Registration/Login.aspx`.

Conclusion: Harris index and related-document metadata are public enough for browser-harness collection, but document images require authorized Harris Clerk portal login. Do not bypass login/CAPTCHA; treat image pulls as an operator-authenticated workflow step.

## Workflow ownership: Hermes vs Ares

This should be a split workflow, not “all in Ares” and not “all in Hermes.”

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

Scripts/adapters are optional later. The promotion rule is: browser harness proves the workflow first; only stable, repetitive pieces become Ares adapters or scripts.

## Gaps / blockers

- Harris Clerk document images are login-gated. Do not bypass CAPTCHA/login.
- HCAD account/property address for `FALLBROOK Sec 3 Lot 1181 Block 24` is still unresolved in this smoke.
- HCTax name search for `Williams Tangie` returned no result; need account/address search after HCAD match.
- TruePeopleSearch, CyberBackgroundChecks, and Bing were blocked by Cloudflare/challenge from this browser environment.

## Next actions

1. Pull authorized Harris Clerk images for:
   - `RP-2022-274022`
   - `RP-2017-563067`
   - `RP-2017-563055`
   - `X177166`
   - `V302389`
   - `W397757`
   - `W383936`
2. Resolve `FALLBROOK Sec 3 Lot 1181 Block 24` to HCAD account/property address.
3. Extract vesting, marital/co-borrower, heirship, and affiant details from document images.
4. Build first-class Ares entities:
   - recorded document
   - document party
   - legal description
   - alias/person identity
   - property thread
   - evidence edge
   - contact candidate
5. Re-run free-source skiptrace in an environment that can access people-search sites, or test an approved provider/mock adapter.

## Evidence file

Structured JSON:

`docs/rollout-evidence/land-records-recon-2026-04-24/tangie-williams-field-test.json`
