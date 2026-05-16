# Trigger Auth Recovery And Schedule Gate QC

## Scope

Recover Trigger.dev CLI auth inside the Hermes execution environment, inspect current Ares `main`, deploy Trigger safely, and avoid duplicate/broken production scheduling while the Trigger prod runtime target is still stale.

## What happened

- Fast-forwarded `/opt/ares/worktrees/ares-main` from `f6add17` to `origin/main`/`b74d495`.
- Found Trigger CLI auth existed at `/root/.config/trigger/config.json`, but Hermes-run CLI commands use HOME `/root/.hermes/home` and therefore looked for `/root/.hermes/home/.config/trigger/config.json`.
- Copied the existing Trigger config into Hermes HOME with `0600` permissions.
- Verified `trigger.dev whoami --profile default` works for project `proj_puouljyhwiraonjkpiki`.
- Ran Trigger typecheck and dry-run deploy successfully.
- Deployed Trigger prod `20260516.1` from current main.
- Verified Trigger prod env still points at stale Vercel runtime `https://production-readiness-afternoon.vercel.app`; public `/health` is 200 but protected probate health is 404.
- Verified live VPS tailnet runtime protected probate health is 200 with `status=healthy`, `no_send_ok=true`, and `outbound_allowed=false`.
- Resumed Hermes cron `815e1261ab2e` so no-send probate scraping/enrichment remains authoritative.
- Added `ARES_TRIGGER_SCHEDULES_ENABLED` guard so Trigger cloud schedules no-op unless explicitly enabled.
- Deployed guarded Trigger prod `20260516.2`.

## Safety posture

- Hermes no-agent cron `815e1261ab2e` remains active.
- Trigger prod `20260516.2` is deployed but scheduled runs return skipped/no-op while `ARES_TRIGGER_SCHEDULES_ENABLED` is absent/false.
- No provider sends, SMS auto-replies, Slack posts, Instantly actions, HubSpot writes, Supabase schema changes, or Ares API deploys were performed.

## Current blocker

Trigger prod cannot become authoritative until its runtime env points at an accessible, current Ares backend. Current Trigger env points at Vercel, but that deployment does not expose the protected probate health route. The live VPS runtime is current/healthy over tailnet, but Trigger cloud is not on that private network.

## Next gate

1. Make a current Ares runtime accessible to Trigger cloud, either by deploying current backend to the public runtime or exposing an approved HTTPS edge.
2. Verify protected runtime health from the same env values Trigger will use.
3. Set `ARES_TRIGGER_SCHEDULES_ENABLED=true` in Trigger prod.
4. Pause Hermes cron `815e1261ab2e` only after Trigger's first successful no-send run evidence.
