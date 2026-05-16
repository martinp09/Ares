# QC Index — 2026-05-16

## Latest probate source identity / no-send monitor

- `probate-post-adapter-live-no-send-monitor/` — latest post-adapter live no-send monitor and Harris case-detail postback classification hardening. Two-day monitor passed with `48` source rows, `8` keep-now rows, no provider sends; env preflight remains blocked until durable production source-run/artifact/business/environment vars are configured.
- `probate-source-identity-supabase-adapter/` — production Supabase source identity adapter wiring for `public.probate_source_identities`; superseded monitor follow-up is closed by the post-adapter monitor above.
- `probate-source-identity-supabase-migration/` — approved remote Supabase migration and schema/RLS/index verification for `public.probate_source_identities`.
- `probate-dedupe-runtime-isolation/` — hashed source identity dedupe, same-scope duplicate reporting, and autonomous/manual runtime isolation.
- `probate-autopilot-scheduler-runtime-error/` — Saturday 07:10 CT source-window/runtime correction; zero-row county pages are valid non-errors.

## Other Ares slices

- `back-office-spine-v0/` — canonical deal spine v0 implementation and post-merge verification.
- `vps-edge-container-hardening/` — tailnet-only VPS edge/container hardening and post-deploy smoke.

## Safety notes

- No QC folder should include raw probate rows, names, case numbers, addresses, emails, phones, raw detail HTML, provider payloads, or secret values.
- Outbound/provider actions remain separately gated: Instantly enrollment/sends, SMS/Vapi, paid skiptrace, HubSpot writes, Slack/provider sends.
