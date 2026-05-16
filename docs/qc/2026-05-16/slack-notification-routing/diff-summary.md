# Diff Summary

## Current-Main Port

- New branch `feature/slack-notification-routing-current-main` starts from `origin/main` at `0fc3f80`.
- Original Slack branch `origin/feature/slack-notification-routing` remains untouched at `e4ee1b5`.
- Merge-base between current `origin/main` and the original Slack branch is `247e8a2`; current `origin/main` is 10 commits ahead of that base.

## Created

- `app/db/slack_notifications.py`
- `app/models/slack_notifications.py`
- `app/services/slack_notification_service.py`
- `scripts/slack_notification_readiness.py`
- `supabase/migrations/20260516012000_slack_notifications.sql`
- `tests/db/test_slack_notifications_repository.py`
- `tests/scripts/test_slack_notification_readiness.py`
- `tests/services/test_slack_notification_service.py`
- `docs/superpowers/specs/2026-05-15-slack-notification-routing-design.md`
- `docs/superpowers/plans/2026-05-15-slack-notification-routing-implementation-plan.md`

## Modified

- Slack route configuration in `app/core/config.py`, `.env.example`, `README.md`, and activation readiness tooling.
- Lead-machine source-pull notifications in `app/services/nightly_lead_machine_service.py`, while preserving current-main probate source identity dedupe.
- Instantly reply notifications in `app/services/lead_webhook_service.py`.
- Lease-option inbound notifications in `app/services/marketing_lead_service.py` and `app/api/marketing.py`.
- SMS reply notifications in `app/services/inbound_sms_service.py` and `app/api/sms_agent.py`.
- Vapi call notifications and recording URL capture in `app/services/vapi_call_service.py` and `app/providers/vapi.py`.
- Router docs and memory files to reflect the current-main port and activation gates.

## Preserved From Current Main

- Probate source identity repository and migration `20260516131500_probate_source_identity_dedupe.sql`.
- VPS edge/container hardening docs and deploy artifacts under `docs/qc/2026-05-16/`.
- Dockerfiles and deploy examples tracked by current `origin/main`.

## Safety Notes

- No live Slack posts were made.
- No provider sends were made.
- No env, VPS, deploy, or Supabase mutations were made.
- Readiness output redacts token values as presence/length/fingerprint.
