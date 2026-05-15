# Instantly Long-Nurture Subsequence Upload — QC Report

## Scope
Created Instantly long-nurture subsequences for the two previously uploaded draft campaigns.

## Parent campaigns
- Probate parent campaign: `9b306264-b8d6-4ca3-8628-8d0e10f84d9c`
- Tax/title-friction parent campaign: `70c5b447-2a72-431c-a63d-1fe8fb67c1fe`

## Created subsequences
- Probate nurture: `Long Nurture | Probate | 2026-05`
  - Subsequence ID: `7db2176c-2ce5-4633-a2e9-346fdc8fff43`
- Tax/title-friction nurture: `Long Nurture | Tax + Title Friction | 2026-05`
  - Subsequence ID: `494fd6b6-6456-46ea-a79d-0547a172ca95`

## Trigger and timing
- Trigger condition: `lead_activity: [91]` — Instantly's `Campaign Completed Without Reply` event.
- First nurture email pre-delay: `31 days` after campaign completion, which maps from the 14-day active campaign to the local Day 45 nurture timing.
- Nurture step cadence preserved from local docs:
  - Day 45
  - Day 75
  - Day 105
  - Day 150
  - Day 210
  - Day 300

## Uploaded content
- 6 nurture email steps per subsequence.
- Weekday 09:00-17:00 `America/Chicago` schedule.
- Daily limit mode: `inherit`.
- Ignore account daily limit: `false`.

## Safety status
- No leads uploaded.
- No campaign activation.
- No sends triggered.
- Parent campaigns remain draft/no-lead campaigns.
- API token value was not printed or stored.

## Code support added
- Added Ares Instantly client methods for subsequence create/list/get/pause/resume.
- Added provider tests for subsequence request construction.

## Verification
- Focused provider/rate-limit tests passed: `7 passed`.
- Provider payload/response/readback JSON artifacts validate with `python3 -m json.tool`.
- Readback confirmed both subsequence IDs, names, parent campaign IDs, `status: 0`, trigger `lead_activity: [91]`, 6 sequence steps, and first-step `pre_delay: 31 days`.
