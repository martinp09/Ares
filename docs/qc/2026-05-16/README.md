# QC Index — 2026-05-16

## Latest probate source identity / no-send monitor

- `live-source-zero-row-status-fix/` — fixed stale Slack/runtime `live county scraping is deferred` warning for successful zero-row live county adapter runs; deployed API at `619ae77`, manually fired a live no-send source pull, Slack `lead_runs` sent, Harris/Montgomery source runs show `live_source_adapter_status=live_source_adapter`, `network_calls_attempted=true`, and no deferred warning.
- `trigger-promotion-slack-sms-live/` — Trigger prod scheduler authority promotion from Hermes cron to exactly three Central Time probate lead runs per day; controlled Trigger run completed, Hermes cron paused, Slack `lead_runs`/`hot_leads` delivery verified, SMS/TextGrid processor readiness verified, and provider sends/auto-replies remain gated.
- `probate-production-readiness-wrap/` — earlier production-readiness wrap for env/deploy/cron/Trigger status, Harris postback source-row hardening, and no-send boundaries. Superseded for current scheduler authority by `trigger-promotion-slack-sms-live/`; its historical status was pre-promotion.
- `probate-post-adapter-live-no-send-monitor/` — post-adapter live no-send monitor and Harris case-detail postback classification hardening. Two-day monitor passed with `48` source rows, `8` keep-now rows, no provider sends.
- `probate-source-identity-supabase-adapter/` — production Supabase source identity adapter wiring for `public.probate_source_identities`; superseded monitor follow-up is closed by the post-adapter monitor above.
- `probate-source-identity-supabase-migration/` — approved remote Supabase migration and schema/RLS/index verification for `public.probate_source_identities`.
- `probate-dedupe-runtime-isolation/` — hashed source identity dedupe, same-scope duplicate reporting, and autonomous/manual runtime isolation.
- `probate-autopilot-scheduler-runtime-error/` — Saturday 07:10 CT source-window/runtime correction; zero-row county pages are valid non-errors.

## Other Ares slices

- `back-office-spine-v0/` — canonical deal spine v0 implementation and post-merge verification.
- `vps-edge-container-hardening/` — tailnet-only VPS edge/container hardening and post-deploy smoke.

## Safety notes

- No QC folder should include raw probate rows, names, case numbers, addresses, emails, phones, raw detail HTML, provider payloads, or secret values.
- Outbound/provider actions remain separately gated: Instantly enrollment/sends, SMS/Vapi auto dispatch, paid skiptrace, HubSpot writes, and campaign/provider sends. Slack operational notifications are live for configured Ares routes.
