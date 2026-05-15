# HubSpot Real Lead Sync QC

## Scope

Operator chose the HubSpot-only lane after confirming Instantly inboxes should continue warming up and Reacher should stay out of scope.

This slice performed exactly one real HubSpot record sync from the Ares production lead ledger:

- Business: `limitless`
- Environment: `prod`
- Ares lead: `lead_341`
- Probate case: `543678`
- Lead/source lane: `harris_county_probate`
- Lead score: `95`
- Filing: `APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP`

## Safety posture

Live effects executed:

- one HubSpot contact create
- one HubSpot deal create
- two provider-link rows in Supabase

Live effects not executed:

- no HubSpot batch sync
- no Instantly enrollment
- no Instantly send
- no Reacher/email verification call
- no Vapi call
- no county/source-provider pull
- no Slack/provider send
- no deploy

## Preflight

Dry-run preview was run first with live gates off:

- `preview_dry_run=true`
- `preview_would_call_provider=false`
- `preview_live_write_enabled=false`
- contact payload count: `1`
- deal payload count: `1`
- company payload count: `0`

Existing provider-link check before sync:

- contact link existed: `false`
- deal link existed: `false`

Known warning:

- `Record lead_341 has no email or phone for HubSpot contact matching.`

This was accepted for the HubSpot-only CRM mirror step because the lead is not being enrolled/sent; it remains marked `skiptrace_status=needed` and `outreach_status=not_ready`.

## Live apply result

Live apply was run with the required one-command env gates and explicit operator approval:

- `PROVIDER_LIVE_SENDS_ENABLED=true`
- `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true`
- `operator_approval=True`

Result:

- live applied: `true`
- created: `2`
- updated: `0`
- skipped: `0`
- failed: `0`
- errors: `0`
- warnings: `1`

Created/readback IDs:

- HubSpot contact ID: `485815102172`
- HubSpot deal ID: `325123310274`
- Provider link/contact: `plink_3`
- Provider link/deal: `plink_4`
- Sync hash: `hubspot-real-lead-lead_341-v1`

## HubSpot readback

Contact readback:

- archived: `false`
- `ares_record_id=lead_341`
- `ares_source_lane=harris_county_probate`
- `ares_contact_status=ready`
- `ares_skiptrace_status=needed`
- `ares_next_best_action=Manual review and skiptrace before Instantly enrollment; copy approval required before any send.`

Deal readback:

- archived: `false`
- deal name: `Harris probate 543678 - TANGIE RENEE WILLIAMS`
- pipeline: `default`
- stage: `3668226794`
- `ares_primary_record_id=lead_341`
- `ares_opportunity_id=opp_lead_341`
- `ares_source_lane=harris_county_probate`
- `ares_lead_temperature=hot`
- `ares_lead_score=95`
- `ares_tax_delinquency_status=not_delinquent_in_current_overlay`
- `ares_title_complexity=heirship`
- `ares_skiptrace_status=needed`
- `ares_outreach_status=not_ready`
- `ares_sync_hash=hubspot-real-lead-lead_341-v1`

## Follow-up

Before any Instantly action:

1. Keep inbox warmup untouched until Martin approves an outreach/copy test.
2. Draft/review the exact copy first; no REI jargon, use survival/red-tape framing.
3. If a lead is selected for Instantly later, require verified contact info and the existing operator approval gates before enrollment/send.
4. Reacher remains a separate day because the Hetzner VPS still has outbound port `25` blocked for SMTP mailbox probing.

## Evidence

Verification:

- Focused HubSpot/provider-link suite: `45 passed in 1.57s`
- `git diff --check`: passed

- Command output: `docs/qc/2026-05-14/hubspot-real-lead-sync/test-output.txt`
- Diff summary: `docs/qc/2026-05-14/hubspot-real-lead-sync/diff-summary.md`
