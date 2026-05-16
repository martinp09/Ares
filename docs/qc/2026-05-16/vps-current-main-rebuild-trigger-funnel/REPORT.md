# VPS Current-Main Rebuild + Trigger Funnel Runtime

Date: 2026-05-16

## Scope

Martin asked for infrastructure work, a current Ares API/UI container rebuild, and whatever was needed to make the system work together cleanly while he slept.

This slice:

- Advanced live VPS checkout `/opt/ares/Ares` to `61f18de` (runtime rebuild commit; later docs commits may be newer).
- Rebuilt and recreated `ares-api` and `ares-ui` from that commit.
- Added explicit SMS reply-agent runtime defaults in the live VPS env: `SMS_AGENT_MODE=draft_only`, `SMS_AGENT_AUTO_REPLIES_ENABLED=false`, and processing/retention defaults.
- Exposed the FastAPI runtime to Trigger/cloud callbacks through Tailscale Funnel: `https://ares.tail485fd9.ts.net` -> `127.0.0.1:8000`.
- Updated Trigger prod runtime env for project `proj_puouljyhwiraonjkpiki` so `RUNTIME_API_BASE_URL` and `HERMES_RUNTIME_API_BASE_URL` point at the Funnel API edge, and Trigger runtime keys match the VPS key fingerprint.
- Set `ARES_TRIGGER_SCHEDULES_ENABLED=false` explicitly in Trigger prod to prevent duplicate scheduled runs while Hermes cron remains authoritative.

## Runtime result

- API container: running/healthy, non-root user `ares`, dropped caps, no-new-privileges, loopback-only `127.0.0.1:8000`.
- UI container: running, non-root user `101`, dropped caps, no-new-privileges, loopback-only `127.0.0.1:8080`.
- Tailnet Caddy: still bound to `100.74.177.6:80`, still injects bearer only on tailnet API routes, still serves UI fallback.
- Public API edge: Tailscale Funnel HTTPS `https://ares.tail485fd9.ts.net` proxies directly to FastAPI without auth injection; protected routes require bearer.
- Trigger prod env: now targets `https://ares.tail485fd9.ts.net`; protected probate health succeeds using the Trigger runtime key.
- Hermes no-agent cron `815e1261ab2e`: left active and authoritative until a controlled Trigger no-send run is proven.

## Verification summary

Captured in:

- `smoke-output.json`
- `infrastructure-output.txt`
- `test-output.txt`

Key checks:

- Direct `/health`: `200`.
- Direct protected `/deals` without bearer: `401`.
- Direct protected `/deals` with bearer: `200`.
- Direct probate health with bearer: `200 healthy`, `no_send_ok=true`, `outbound_allowed=false`.
- SMS pending processor: `processed_count=0`, `sent_count=0`, `blocked_count=0`, `failed_count=0`.
- Tailnet Caddy `/health`, `/deals`, and UI root: `200`.
- Funnel `/health`: `200`.
- Funnel protected `/deals` without bearer: `401`.
- Funnel protected `/deals` with bearer: `200`.
- Funnel protected probate health with bearer: `200 healthy`, `no_send_ok=true`, `outbound_allowed=false`.
- Trigger-env protected probate health: `200 healthy`, `no_send_ok=true`, `outbound_allowed=false`.
- Supabase SMS-agent, Slack notification, and probate identity tables: reachable.
- Trigger typecheck: passed.

## Safety boundary

No Instantly enrollment/sends, email sends, SMS/Vapi dispatch, paid skiptrace, HubSpot batch writes, live Slack posts, county source pulls, or Supabase schema changes were performed.

Outbound/provider gates remain false:

- `PROVIDER_LIVE_SENDS_ENABLED=false`
- `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`
- `INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=false`
- `VAPI_PROVIDER_LIVE_SENDS_ENABLED=false`
- `SMS_AGENT_AUTO_REPLIES_ENABLED=false`

## Remaining promotion step

Trigger is now pointed at a reachable current runtime, but schedules stay disabled on purpose. Next step is one controlled Trigger no-send run. If it proves the expected lifecycle without duplicate source runs, enable `ARES_TRIGGER_SCHEDULES_ENABLED=true` and pause Hermes cron `815e1261ab2e`.
