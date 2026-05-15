# HubSpot Rich Probate Fields Diff Summary

## Code changes

- `app/services/hubspot_mirror_service.py`
  - Expanded HubSpot contact/deal/company custom-property catalogs for probate, heir/contact, mailing, property, court, tax-overlay, and source-run fields.
  - Added typed property payload selection so numeric fields use HubSpot `number` properties and long-form fields use `textarea`.
  - Expanded contact payloads beyond generic name/email/phone to include contact role/address, property/mailing address, probate context, best-contact details, heir summary/status/confidence/next gate, and priority tier.
  - Expanded deal payloads to include property/mailing/HCTax/HCAD/source-run/tax-overlay status/query/count/probate/heir/party/event/priority fields.
  - Converts sequence values to HubSpot-friendly semicolon-delimited strings for list-like payload values such as enrichment/priority flags and now omits empty sequences instead of sending empty strings that could clear existing HubSpot values.

- `app/models/mission_control.py`
  - Expanded `MissionControlHubSpotRecordSyncItem` so Mission Control/Hermes preview/apply payloads can carry the richer probate and heir/contact fields without being rejected by `extra="forbid"`.

## Test changes

- `tests/services/test_hubspot_mirror_service.py`
  - Asserts the customization preview includes the rich new custom properties and correct HubSpot field types.
  - Asserts record-sync preview produces rich contact/deal payloads with mailing address, probate case, best contact, heir summary, counts, and tax overlay fields.
  - Makes the mutation-count expectation derive from the payload catalog instead of a stale hard-coded property count.

- `tests/api/test_hubspot_mirror.py`
  - Asserts Mission Control record-preview API accepts and returns rich HubSpot probate/heir field payloads.

## QC/doc changes

- `docs/qc/2026-05-14/hubspot-rich-probate-fields/REPORT.md`
- `docs/qc/2026-05-14/hubspot-rich-probate-fields/test-output.txt`
- `docs/qc/2026-05-14/hubspot-rich-probate-fields/diff-summary.md`
- living-doc updates in `CONTEXT.md`, `TODO.md`, `README.md`, `memory.md`, and the dated QC index.

## Live side effects

- Created newly-missing HubSpot custom properties only.
- Updated existing HubSpot contact `485815102172` and deal `325123310274` for `lead_341`.
- Updated provider-link sync hash to `hubspot-real-lead-lead_341-rich-v3`.
- No Instantly/Reacher/Vapi/source-provider/Slack/deploy side effects.

## Known data gap

The selected lead still has no property address/HCAD account in the current Ares data (`property_address_present=false`, `hcad_account_present=false`). The new HubSpot fields now exist and will carry those facts once land/tax/property matching supplies them.
