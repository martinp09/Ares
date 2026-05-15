# HubSpot Record Sync Canary QC

## Scope

Operator approved moving past the HubSpot portal buildout into the first controlled live record-sync canary.

This slice performed:

- commit/push of the operating-spine bundle
- local non-secret HubSpot default env configuration
- remote Supabase migration apply for provider links/sync cursors/sync runs
- one HubSpot record-sync canary through the gated Ares service path
- HubSpot readback and provider-link verification

## Commit / push

- Commit: `8c19c26b63545f4bdb58487710e2994ff5e4fa49`
- Message: `feat: add Ares provider operating spine`
- Branch: `feature/copywriting-brain-offer-engine`
- Remote: `origin/feature/copywriting-brain-offer-engine`
- Push verification: local and remote heads matched `8c19c26b63545f4bdb58487710e2994ff5e4fa49`.

## Local env defaults

Updated local ignored `.env` only; no tracked secret file changed.

- `HUBSPOT_DEFAULT_PIPELINE_ID=default`
- `HUBSPOT_DEFAULT_DEAL_STAGE_ID=3668226794`
- `PROVIDER_LIVE_SENDS_ENABLED=false`
- `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`

Backup created locally:

- `/opt/ares/Ares/.env.bak.hubspot-defaults-20260514T113913Z`

## Remote Supabase migration

Applied migration:

- `20260514090000_provider_object_links.sql`

Post-apply migration list shows local and remote both have:

- `20260514090000 | 20260514090000 | 2026-05-14 09:00:00`

## Canary record

A single synthetic canary record was synced:

- Ares record ID: `hubspot_canary_20260514`
- Ares opportunity ID: `opp_hubspot_canary_20260514`
- HubSpot contact ID: `486079925950`
- HubSpot deal ID: `325110558439`
- Pipeline: `default`
- Deal stage: `3668226794`
- Sync hash: `hubspot-canary-20260514-v1`

## Result

Live apply result:

- created: `2`
- updated: `0`
- skipped: `0`
- failed: `0`
- warnings: `0`

HubSpot readback verified:

- contact exists and has `ares_record_id=hubspot_canary_20260514`
- deal exists and has `ares_primary_record_id=hubspot_canary_20260514`
- deal has `ares_opportunity_id=opp_hubspot_canary_20260514`
- deal has `pipeline=default`
- deal has `dealstage=3668226794`

Provider-link verification:

- contact provider link present
- deal provider link present
- both links have `sync_hash=hubspot-canary-20260514-v1`

## Live-side-effect posture

Live effects executed:

- one HubSpot contact create
- one HubSpot deal create
- two provider-link rows in Supabase
- provider-links migration applied to remote Supabase

Live effects **not** executed:

- no HubSpot batch record sync
- no Instantly enrollment/send
- no Vapi call
- no county/source-provider pull
- no Slack/provider send
- no deploy

## Follow-up gates

Before syncing real records:

1. Inspect the canary manually in HubSpot if desired.
2. Keep live gates off by default.
3. Use preview first for any real record set.
4. Start with a narrow hand-selected keep-now/probate/tax lead, not a batch.
5. Confirm provider-link readback after the first real record.
