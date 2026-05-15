# Instantly Campaign Draft Upload — QC Report

## Scope
Uploaded the two local Ares cold-email campaign backups into Instantly as draft campaigns only:

1. `Email | Probate | Inherited Property Relief Plan | Texas | 2026-05`
2. `Email | Tax + Title Friction | Property Situation Review | Texas | 2026-05`

## Source artifacts
- Campaign backup JSON: `docs/marketing/exports/instantly-campaign-backups-2026-05-02/cold-email-campaigns.json`
- Sequence CSV backup: `docs/marketing/exports/instantly-campaign-backups-2026-05-02/sequence-import-backup.csv`
- Generated create payloads: `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-create-payloads-2026-05-02.json`
- Upload response backup: `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-upload-results-2026-05-02.json`
- Readback backup: `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-readback-2026-05-02.json`

## Created Instantly campaigns
- Probate campaign ID: `9b306264-b8d6-4ca3-8628-8d0e10f84d9c`
- Tax/title-friction campaign ID: `70c5b447-2a72-431c-a63d-1fe8fb67c1fe`

## Uploaded content
- 4 active email steps per campaign.
- 2 subject variants per step.
- Weekday 09:00-17:00 `America/Chicago` schedule.
- `stop_on_reply: true`.
- `open_tracking: false`.

## Safety status
- No leads uploaded.
- No campaign activation.
- No sends triggered.
- No API token value printed or stored.

## Verification
- Backup JSON validated with `python3 -m json.tool`.
- Sequence CSV parsed with 8 rows across 2 campaign names.
- Instantly preflight listed campaigns successfully before writes.
- Both campaign create calls returned IDs and `status: 0`.
- Readback confirmed both campaign IDs, names, `status: 0`, and 4 sequence steps each.

## Notes
The local campaign docs include long-nurture strategy. This upload created the active 4-step campaign sequences from the import backup; nurture timing remains preserved in the local campaign packets/backups for a later subsequence/nurture implementation if desired.
