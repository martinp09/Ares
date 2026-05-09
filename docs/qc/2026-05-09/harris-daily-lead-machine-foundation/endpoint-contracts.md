# Endpoint Contracts — Harris Daily Lead Machine Foundation

## Runtime endpoint

`POST /lead-machine/harris/daily-import`

### Request

Required:
- `business_id`: non-empty string
- `environment`: non-empty string
- `run_date`: ISO date string
- At least one source payload collection:
  - `probate_records`: array of objects
  - `hcad_estate_of_records`: array of objects

Optional:
- `dry_run`: boolean, defaults to `true`
- `keep_only`: boolean, defaults to `true`

### Response highlights

- `run_key`: `harris-daily-lead-machine:<run_date>`
- `dry_run`: mirrors request/default
- `live_send_policy`: `no_provider_sends_or_slack_posts_from_daily_import`
- `counts.provider_send_count`: always `0`
- `counts.qc_warning_count`: warning count for operator review
- `probate`: probate preview/import summary
- `estate_of`: Estate Of candidate/import summary
- `qc_warnings`: structured operator warnings
- `notifications`: Slack readiness/skip status; no post is sent by this endpoint

## Trigger task

Task file: `trigger/src/lead-machine/harrisDailyImport.ts`

- Task ID: `harris-daily-import`
- Runtime endpoint key: `harrisDailyImport`
- Artifact type: `lead_machine_harris_daily_import`

## No-send guarantee for this slice

- Daily import never calls Instantly/TextGrid/Resend provider send paths.
- Daily import never posts to Slack.
- Slack token/channel config is readiness metadata only until a dedicated Slack delivery adapter is implemented and explicitly tested.
- Vercel deployment was not attempted because authentication was unavailable.
