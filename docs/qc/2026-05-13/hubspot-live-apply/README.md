# HubSpot Live Apply QC — 2026-05-13

- Executed at: `2026-05-13T04:16:39Z`
- Result: `blocked_before_live_write`
- Secret handling: parsed the prior Hermes transcript in-process only; no raw HubSpot token/key is stored here.
- Live HubSpot mutations performed: `0`

## What was attempted

```bash
python /tmp/hubspot_live_apply.py
git diff --check
```

The live-apply script was prepared to apply the merged Ares HubSpot definitions idempotently:

- Contact properties: `ares_role`, `ares_source_lane`, `ares_record_status`, `ares_skiptrace_status`, `ares_follow_up_permission`, `ares_contact_confidence`
- Deal properties: `ares_external_key`, `ares_source_lane`, `ares_operator_lane`, `ares_property_address`, `ares_mailing_address`, `ares_county`, `ares_hctax_account`, `ares_probate_case_number`, `ares_estimated_value`, `ares_delinquent_tax_amount`, `ares_delinquent_years`, `ares_debt_to_value_pct`, `ares_title_flags`, `ares_document_pull_status`, `ares_next_action`
- Deal pipeline: `Ares Acquisition Pipeline`

## Sanitized auth/readiness evidence

- Recovered transcript candidates:
  - `hubspot_personal_key`: present, length `107`, prefix fingerprint `CiRu`, suffix fingerprint `uYTI`
  - `hubspot-developer_keys`: present, length `36`, prefix fingerprint `na2-`, suffix fingerprint `d711`
- Bearer probe using the recovered personal key:
  - `GET /account-info/v3/details`: HTTP `401`
  - `GET /crm/v3/properties/contacts/firstname`: HTTP `401`
- Legacy query-key probe, read-only:
  - personal key as `hapikey`: HTTP `401`
  - developer key as `hapikey`: HTTP `403`

## Conclusion

The pasted HubSpot personal key did not authenticate as a HubSpot CRM bearer token, and the developer key is not valid for CRM bearer writes. The script stopped before creating/updating any properties or pipelines, per the no-guess/no-delete safety rule.

## Next required action

Provide or configure a valid HubSpot private-app/personal access token with CRM schema/pipeline scopes, preferably via deployment/local secret env as `HUBSPOT_ACCESS_TOKEN`, then rerun the live apply. Rotate the previously pasted token because it was shared in chat.
