# HubSpot Contact Visibility Correction QC

## Scope

Martin reported that HubSpot showed Brittany as the best contact but did not show the rest of the contact info. This was a visibility/data-placement issue, not a failed rich-field write.

## Root cause

Live HubSpot readback showed:

- Ares custom fields were populated:
  - `ares_best_contact_address=1614 Royal Grantham Ct, Houston TX 77073`
  - `ares_mailing_address=1614 Royal Grantham Ct, Houston TX 77073`
  - `ares_contact_address=1614 Royal Grantham Ct, Houston TX 77073`
  - `ares_heir_candidate_count=5`
  - `ares_probate_case_number=543678`
- Standard HubSpot contact fields were empty:
  - `address=null`
  - `city=null`
  - `state=null`
  - `zip=null`
  - `country=null`
  - `phone=null`
  - `email=null`

HubSpot's normal contact sidebar/card tends to show standard/contact-card fields, while custom Ares fields only appear if the record card/default view is customized or the user opens/searches all properties.

## HubSpot UI/layout constraint

HubSpot's public KB documents record-card property visibility as a HubSpot UI record-customization setting:

- Individual record view: open the contact/deal, on the left sidebar `About this [record]` or `Key information` card, click `Actions`, choose `Customize properties`, then `Add properties`.
- Account default view: `Settings` → `Objects` → select `Contacts` or `Deals` → `Record Customization` → `Default view`, requiring `Super Admin` or `Customize record page layout` permission.

Ares can create properties and write values via the Service Key/CRM API, but that does not automatically add every custom Ares property to Martin's visible HubSpot card.

## Code correction

Updated `app/services/hubspot_mirror_service.py` so contact sync now also maps a best-contact/mailing/applicant address into HubSpot standard contact fields:

- `address`
- `city`
- `state`
- `zip`
- `country`

The parser handles the current Harris probate address shape, e.g.:

```text
1614 Royal Grantham Ct, Houston TX 77073
```

becomes:

```text
address=1614 Royal Grantham Ct
city=Houston
state=TX
zip=77073
country=United States
```

## Live correction applied

Updated the existing provider-linked records only:

- contact: `485815102172`
- deal: `325123310274`
- provider links: `plink_3` / `plink_4`
- sync hash: `hubspot-real-lead-lead_341-visible-v4`

No new HubSpot contact/deal was created.

No Instantly/Reacher/Vapi/source-provider/Slack/deploy side effects occurred.

## Final HubSpot readback

Contact readback now shows standard address fields populated:

- `address=1614 Royal Grantham Ct`
- `city=Houston`
- `state=TX`
- `zip=77073`
- `country=United States`

Ares custom fields remain populated:

- `ares_best_contact_address=1614 Royal Grantham Ct, Houston TX 77073`
- `ares_mailing_address=1614 Royal Grantham Ct, Houston TX 77073`
- `ares_contact_address=1614 Royal Grantham Ct, Houston TX 77073`
- `ares_heir_candidate_count=5`
- `ares_probate_case_number=543678`

## Remaining true data gaps

These are still blank because Ares does not have them for this lead yet:

- contact email
- contact phone/mobile phone
- property address / HCAD account

Do not invent these. The next real layer is skiptrace/contact enrichment plus property/HCAD matching.

## Recommended manual HubSpot view update

To make the rich Ares fields visible without using `View all properties`, add the following to the contact and deal record card/default view in HubSpot:

Contact card:

- Address
- City
- State/Region
- Postal code
- Ares Mailing Address
- Ares Best Contact Role
- Ares Probate Case Number
- Ares Heir Candidate Count
- Ares Heir Candidates Summary
- Ares Heir Status
- Ares Heir Next Gate

Deal card:

- Ares Probate Case Number
- Ares Decedent Name
- Ares Best Contact Name
- Ares Best Contact Role
- Ares Best Contact Address
- Ares Mailing Address
- Ares Heir Candidate Count
- Ares Heir Candidates Summary
- Ares Property Address
- Ares Tax Overlay Status
- Ares Sync Hash

## Verification

Focused tests passed:

```bash
python -m pytest tests/services/test_hubspot_mirror_service.py tests/api/test_hubspot_mirror.py -q
```

Result: `37 passed in 1.47s`.

Full backend verification passed:

```bash
python -m pytest -q && git diff --check
```

Result: `758 passed in 26.41s`; `git diff --check` passed.

## Evidence files

- `docs/qc/2026-05-14/hubspot-contact-visibility-correction/test-output.txt`
- `docs/qc/2026-05-14/hubspot-contact-visibility-correction/diff-summary.md`
