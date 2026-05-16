# VPS Edge + Container Hardening QC Report

- Date: 2026-05-16
- Branch: `fix/vps-edge-container-hardening`
- Code commit deployed: `32a3f57`
- Scope: tighten the live VPS edge after Docker rebuild, remove public Caddy exposure, block public Supabase/dev ports, harden tracked Docker artifacts, and reduce Deal Desk read latency by avoiding full control-plane hydration for read-only deal endpoints.

## Root cause

- Caddy was listening on public `*:80` and injected the internal runtime bearer for protected API paths. Direct API access still returned `401`, but public Caddy access could reach protected routes because Caddy supplied the bearer.
- Supabase local/dev ports were published by Docker on `0.0.0.0` / `[::]`.
- `/deals` and `/deals/fire-list` were correct but slow because read-only deal endpoints hydrated the entire Supabase control-plane store, not just the deal runtime tables.

## Changes

### Repo/runtime

- `app/db/deals.py`
  - Added targeted Supabase read-model paths for read-only deal operations.
  - `list_deals`, `get_deal`, `get_detail` children, and fire-list child reads now query only `deal_*_runtime` tables instead of hydrating every control-plane table.
  - Write/promotion paths still use the existing transactional store semantics.
- `tests/db/test_deals_repository.py`
  - Added a regression proving Supabase read-only deal paths do not call the full control-plane transaction/hydration path.
- `Dockerfile.api`
  - Adds OCI labels.
  - Creates and runs as non-root `ares` user.
- `Dockerfile.ui`
  - Switches runtime image to `nginxinc/nginx-unprivileged:1.27-alpine`.
  - Adds OCI labels.
  - Exposes `8080` instead of privileged `80`.
- `deploy/nginx.conf`
  - Listens on `8080`.
  - Disables server tokens.
  - Adds basic security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.
- `deploy/Caddyfile.tailnet.example`
  - Adds a tailnet-bound Caddy edge template using environment variables instead of committed secrets.
- `deploy/docker-compose.vps.example.yml`
  - Adds loopback-only API/UI port publishing, build labels, `no-new-privileges`, and dropped caps.

### Live VPS edge

- Backed up Caddy before changes:
  - `/etc/caddy/Caddyfile.bak.20260516T032356Z`
  - `/etc/caddy/Caddyfile.bak.20260516T032420Z`
- Moved Caddy runtime bearer out of `/etc/caddy/Caddyfile` into root-only environment file:
  - `/etc/caddy/ares-runtime.env` mode `600`
  - `/etc/systemd/system/caddy.service.d/ares-runtime-env.conf`
- Updated Caddy to bind only to Tailscale IP `100.74.177.6:80` with `bind {$ARES_TAILNET_IP}`.
- Added persistent edge firewall guardrail:
  - `/usr/local/sbin/ares-edge-firewall.sh`
  - `/etc/systemd/system/ares-edge-firewall.service`
  - Drops public `eth0` TCP access to `80,54321,54322,54323,54324,54327` for IPv4 and IPv6.

## Verification

See:

- `test-output.txt`
- `build-output.txt`
- `live-edge-smoke.txt`
- `post-deploy-live-smoke.txt`
- `diff-summary.md`

Passed:

- Focused backend/deal contracts: `12 passed`
- Full backend: `946 passed`
- Mission Control tests: `25 files / 82 tests passed`
- Mission Control typecheck: passed
- Mission Control build: passed
- Trigger typecheck: passed
- Docker API image build: passed
- Docker UI image build: passed
- API image non-root UID: `999`
- UI image non-root UID: `101`
- UI container smoke on `127.0.0.1:18080/deal-desk`: `200`
- UI security headers present in smoke: `X-Content-Type-Options=nosniff`, `X-Frame-Options=DENY`
- `git diff --check`: passed
- `git diff --cached --check`: passed

Live edge smoke before deploying the new code image:

- `http://100.74.177.6/health`: `200`
- `http://100.74.177.6/`: `200`
- `http://100.74.177.6/deals`: `200` but still ~12s because running container was still the pre-deploy image at smoke time
- `http://127.0.0.1/health`: connection refused, confirming Caddy is no longer bound to localhost/public wildcard
- Listener summary shows Caddy bound to `100.74.177.6:80`
- Edge firewall service active

Post-merge/deploy smoke after rebuilding `/opt/ares/Ares` from `32a3f57`:

- Direct API health: `200`
- Direct API `/deals` without auth: `401`, preserving API bearer protection
- Tailnet Caddy `/health`: `200`
- Tailnet Caddy `/`: `200`
- Tailnet Caddy `/deal-desk`: `200`
- Tailnet Caddy `/deals`: `200` in `327ms` with no data
- Tailnet Caddy `/deals/fire-list`: `200` in `73ms` with no data
- Tailnet Caddy `/mission-control/probate-autopilot/health`: `200`
- Localhost Caddy: connection refused, confirming Caddy is not bound on local/public wildcard
- `ares-api` container UID: `999`; `ares-ui` container UID: `101`
- Docker published API/UI only on loopback: `127.0.0.1:8000` and `127.0.0.1:8080`
- Caddy listener: `100.74.177.6:80`
- Edge firewall service remains active

## Safety / no-send boundary

No Instantly enrollment/sends, email sends, SMS/Vapi calls, paid skiptrace, HubSpot batch writes, Slack/provider sends, county source pulls, or production outbound mutations were executed.

The live mutations were limited to VPS edge/network/service configuration, repo deployment, and container rebuild/recreate: Caddy binding/env-file migration, firewall guardrail installation, `/opt/ares/docker-compose.yml` loopback/non-root hardening, and rebuilding `ares-api`/`ares-ui` from `32a3f57`.

## Remaining deployment step

Deployment is complete for this hardening slice. Continue monitoring only; if Supabase/dev containers are kept running, keep `ares-edge-firewall.service` active or bind those dev ports to loopback in their owning compose stack.
