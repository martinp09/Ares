# Instantly Real Account Sync — QC Report

## Scope
Attempted to move the existing Ares Instantly campaign work onto the newly supplied Instantly API key / real account.

## What was found from prior work
Existing campaign work already exists locally and had previously been uploaded to a different Instantly account/key as draft-only assets:

- Campaign packet docs:
  - `docs/marketing/campaigns/2026-05-02-probate-cold-email-professional-service-campaign.md`
  - `docs/marketing/campaigns/2026-05-02-tax-curative-title-cold-email-professional-service-campaign.md`
- Backup source artifacts:
  - `docs/marketing/exports/instantly-campaign-backups-2026-05-02/cold-email-campaigns.json`
  - `docs/marketing/exports/instantly-campaign-backups-2026-05-02/sequence-import-backup.csv`
  - `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-create-payloads-2026-05-02.json`
  - `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-nurture-subsequence-create-payloads-2026-05-02.json`

Prior draft IDs from the old account/key:

- Probate campaign: `9b306264-b8d6-4ca3-8628-8d0e10f84d9c`
- Tax/title campaign: `70c5b447-2a72-431c-a63d-1fe8fb67c1fe`
- Probate nurture subsequence: `7db2176c-2ce5-4633-a2e9-346fdc8fff43`
- Tax/title nurture subsequence: `494fd6b6-6456-46ea-a79d-0547a172ca95`

## Action taken
- Updated `/opt/ares/Ares/.env` so `INSTANTLY_API_KEY` uses the newly supplied key.
- Created `.env` backup: `.env.before-instantly-real-account-20260503T215318Z`.
- Ran safe read-only Instantly preflight through the Ares `InstantlyClient` before any provider write.

## Result
The new Instantly API key is valid enough to reach Instantly, but the workspace rejected the preflight with:

```text
HTTP 402 Payment Required
Workspace does not have an active paid plan
```

## Safety status
- No campaigns created in the new account.
- No nurture subsequences created in the new account.
- No leads uploaded.
- No campaign activation.
- No sends triggered.
- API token value was not printed into artifacts.

## Blocker
The new Instantly workspace needs an active paid plan before the API can list/create campaigns. Once the plan is active, rerun the real-account sync script to create the two campaigns and two nurture subsequences from the existing local backups.
