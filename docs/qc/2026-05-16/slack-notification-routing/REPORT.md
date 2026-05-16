# Slack Notification Routing Current-Main QC

Date: 2026-05-16
Branch: `feature/slack-notification-routing-current-main`
Base: `origin/main` at `0fc3f80`
Original Slack branch: `origin/feature/slack-notification-routing` at `e4ee1b5`

## Result

- Ported Slack notification routing onto current `origin/main` without rewriting the older pushed branch.
- Preserved the current-main probate/VPS hardening commits, including probate source identity dedupe and the `20260516131500_probate_source_identity_dedupe.sql` migration.
- Resolved the only code conflict in `app/services/nightly_lead_machine_service.py` by keeping both the probate source identity repository wiring and Slack source-pull notification wiring.
- Confirmed the VPS read-only state: live `/opt/ares/Ares` is detached at `fc99b75`; `/opt/ares/worktrees/ares-main` is at `0fc3f80`; `ares-api` is healthy; `ares-ui` returns 200; Caddy is active; Slack env vars are not configured.

## Safety

- No live Slack sends.
- No Slack env changes.
- No provider sends.
- No deploys.
- No Supabase mutations.
- No VPS mutations.
- Slack readiness tooling prints token presence/length/fingerprint only, never raw token values.

## Verification

```bash
uv run pytest tests/db/test_slack_notifications_repository.py tests/services/test_slack_notification_service.py tests/scripts/test_slack_notification_readiness.py tests/api/test_runtime_config_contract.py tests/api/test_nightly_lead_machine.py tests/services/test_nightly_lead_machine_service.py tests/api/test_marketing_webhooks.py tests/services/test_marketing_provider_notifications.py tests/api/test_sms_agent.py tests/services/test_inbound_sms_service.py tests/providers/test_vapi.py tests/services/test_vapi_call_service.py tests/api/test_lead_machine.py tests/services/test_lead_webhook_service.py tests/api/test_agent_installs.py tests/scripts/test_activation_readiness.py -q
```

Result: `224 passed in 4.98s`

```bash
uv run pytest -q
```

Result: `1050 passed in 10.52s`

```bash
npm ci && npm run typecheck
```

Run from `trigger/`.

Result: passed.

```bash
git diff --check
```

Result: passed.

## Remaining Activation Prerequisites

1. Create or identify Slack channels for lead runs, hot leads, Instantly replies, lease-option inbound leads, and SMS/calls.
2. Invite the Ares Slack bot to each channel.
3. Configure `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, and route channel IDs in the target runtime env.
4. Apply `supabase/migrations/20260516012000_slack_notifications.sql` before live persistence.
5. Run no-post readiness against the activated env.
6. Run one explicitly approved Slack smoke per route using test payloads.
