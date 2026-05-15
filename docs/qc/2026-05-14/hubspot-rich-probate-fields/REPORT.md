# HubSpot Rich Probate Fields QC

## Scope

Martin correctly flagged that the first real HubSpot lead sync was too generic: it created the HubSpot contact/deal but did not yet expose the probate/heir/contact/mailing/property fields needed for a useful acquisitions CRM view.

This slice does three things:

1. Expands the Ares HubSpot customization schema beyond generic templates.
2. Expands the Ares record-sync payload contract so HubSpot can store probate, heir/contact, mailing, property, tax-overlay, and court metadata.
3. Applies the new HubSpot fields live, then updates the existing `lead_341` contact/deal in HubSpot with the available rich data.

## Live-side-effect posture

Live effects executed:

- HubSpot property customization apply for newly-added Ares custom properties.
- HubSpot contact update for existing contact `485815102172` / provider link `plink_3`.
- HubSpot deal update for existing deal `325123310274` / provider link `plink_4`.
- Provider-link sync hashes updated to `hubspot-real-lead-lead_341-rich-v3`.

Live effects not executed:

- no new HubSpot contact/deal creation
- no HubSpot batch sync
- no Instantly enrollment
- no Instantly send
- no Reacher/email verification call
- no Vapi call
- no county/source-provider pull
- no Slack/provider send
- no deploy

## New HubSpot field coverage

Contacts now support Ares fields for:

- source/record/contact role
- contact address
- property address
- mailing address
- probate case number
- decedent name
- estate name
- best contact name/role/address
- heir candidate count
- heir candidate summary
- heir status/confidence/next gate
- priority tier
- next action and agent summary

Deals now support Ares fields for:

- property address and mailing address
- HCAD/HCTax references and owner names
- source run ID
- tax overlay status/candidate count
- probate case/court/file/status/filing metadata
- estate/decedent metadata
- best contact name/role/address
- heir candidate count/summary/status/confidence/next gate
- party/event counts
- priority tier/flags
- existing score/status/outreach/sync fields

Companies now support Ares fields for:

- mailing address
- probate case number
- decedent name

## HubSpot live apply result

- customization live applied: `true`
- first pass mutation count: `44`
- fix-lane mutation count: `1` (`ares_tax_overlay_query`)
- final property payload counts:
  - contacts: `27`
  - deals: `47`
  - companies: `7`
- properties created across both live customization passes:
  - contacts: `15`
  - deals: `27`
  - companies: `3`
- final pass properties skipped/present:
  - contacts: `27`
  - deals: `46`
  - companies: `7`
- warning: reused the existing single HubSpot `Sales Pipeline` because the portal is limited to one deal pipeline.

## lead_341 update/readback result

Updated existing HubSpot records only:

- contact: `485815102172`
- deal: `325123310274`
- contact provider link: `plink_3`
- deal provider link: `plink_4`
- sync hash: `hubspot-real-lead-lead_341-rich-v3`

Available rich facts now read back in HubSpot:

- decedent: `TANGIE RENEE WILLIAMS`
- probate case: `543678`
- probate file date: `2026-04-20`
- probate status: `Open`
- filing type: `APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP`
- best contact/applicant: `Brittany C Edwards`
- best contact role: `Applicant`
- best contact/mailing address: `1614 Royal Grantham Ct, Houston TX 77073`
- heir candidate count: `5`
- heir status: `candidate_identified_relationship_pending`
- heir confidence: `medium_high_candidate_contact`
- next gate: `Pull/OCR application/will/heirship PDF to confirm relationship and authority.`
- party count: `7`
- event count: `7`
- tax overlay status: `tax_overlay_soft_no_signal`
- tax overlay query: `TANGIE RENEE WILLIAMS`
- tax overlay candidate hits: `0`

Known missing facts for this specific lead:

- `ares_property_address` is still `null` because the selected lead currently has no HCAD/property match and no next-layer property address in the Ares data.
- `hcad_account` is still absent for the same reason.
- The lead still has no email/phone; it remains `skiptrace_status=needed` and is not outreach-ready.

## Verification

Focused final tests:

```bash
python -m pytest tests/services/test_hubspot_mirror_service.py tests/api/test_hubspot_mirror.py -q
```

Result: `37 passed in 1.44s`.

Final backend verification before commit:

```bash
python -m pytest -q && git diff --check
```

Result: `758 passed in 26.46s`; `git diff --check` passed.

Additional final verification for the focused slice is captured in this folder's `test-output.txt`.

## Evidence files

- Command/readback output: `docs/qc/2026-05-14/hubspot-rich-probate-fields/test-output.txt`
- Diff summary: `docs/qc/2026-05-14/hubspot-rich-probate-fields/diff-summary.md`
