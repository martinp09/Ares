# HubSpot Contact Visibility Correction Diff Summary

## Code changes

- `app/services/hubspot_mirror_service.py`
  - Added standard HubSpot contact address mapping from Ares best-contact/mailing/applicant address data.
  - Added `_contact_standard_address` helper.
  - Added `_parse_us_address` helper for current probate address strings such as `Street, Houston TX 77073`.
  - Contact sync now writes standard `address`, `city`, `state`, `zip`, and `country` when the source record has a parsable address.

## Test changes

- `tests/services/test_hubspot_mirror_service.py`
  - Added assertions that contact preview/sync payloads include standard HubSpot address fields in addition to Ares custom fields.

## QC/doc changes

- Added `docs/qc/2026-05-14/hubspot-contact-visibility-correction/` with root-cause readback, live correction evidence, HubSpot UI record-card guidance, and focused test output.
- Updated dated QC index and living docs to record that the standard contact address fields were corrected after the rich-field sync.

## Live side effects

- Updated existing HubSpot contact `485815102172` and deal `325123310274` for `lead_341`.
- Updated provider-link sync hashes to `hubspot-real-lead-lead_341-visible-v4`.
- Did not create any new HubSpot record.
- Did not touch Instantly, Reacher, Vapi, source providers, Slack, or deployment.

## Remaining limitation

Ares can write HubSpot data, but HubSpot record-card visibility is controlled by HubSpot UI record customization. The Ares Service Key path does not automatically pin every custom Ares property onto Martin's visible contact/deal cards; Super Admin / record-layout customization in HubSpot is still needed for the ideal CRM view.
