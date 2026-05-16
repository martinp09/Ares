# Slack Routing VPS Deploy

Date: 2026-05-16
GitHub PR: `#11`
Merged commit: `ff7dd9b6bf24856c838e0b25dfb37db7050b7054`
VPS: `root@100.74.177.6`

## Result

- Merged Slack notification routing into `origin/main`.
- Fast-forwarded `/opt/ares/worktrees/ares-main` to `ff7dd9b`.
- Deployed `/opt/ares/Ares` as detached `ff7dd9b`.
- Applied remote Supabase migration `20260516012000_slack_notifications.sql`.
- Rebuilt and recreated Docker `ares-api` and `ares-ui`.
- Verified API/UI local health after deploy.

## Supabase Migration

Initial dry-run reported that `20260516012000_slack_notifications.sql` needed `--include-all` because its timestamp is earlier than the latest remote probate identity migration.

Applied with:

```bash
supabase db push --include-all --yes
```

Remote migration history now includes:

```text
20260516011000
20260516012000
20260516131500
```

## Runtime Verification

```bash
docker compose -f /opt/ares/docker-compose.yml ps
```

Result:

- `ares-api`: healthy, loopback `127.0.0.1:8000`
- `ares-ui`: running, loopback `127.0.0.1:8080`

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/
```

Result:

```text
{"status":"ok"}
200
```

## Slack Readiness

```bash
uv run python scripts/slack_notification_readiness.py --env-file .env --json
```

Result: exited `2` with `configured=false`, `would_post=false`.

Missing:

- `SLACK_NOTIFICATIONS_ENABLED=true`
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_LEAD_RUNS`
- `SLACK_CHANNEL_HOT_LEADS`
- `SLACK_CHANNEL_INSTANTLY_REPLIES`
- `SLACK_CHANNEL_LEASE_OPTION_INBOUND`
- `SLACK_CHANNEL_SMS_CALLS`

Slack connector channel search found no existing Ares/lead/Instantly/lease/SMS route channels. The connector can search/read/post but cannot create Slack channels.

## Safety

- No live Slack posts.
- No provider sends.
- No outbound SMS/Vapi/Instantly sends.
- No raw secrets printed.
- Slack delivery remains blocked until the route channel env and bot token are explicitly configured.
