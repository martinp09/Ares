# Diff Summary — Ares Chief of Staff v0

## New files

- `app/models/ares_chief_of_staff.py` — Pydantic models for Chief of Staff buckets, lead cards, briefs, and run results.
- `app/services/ares_chief_of_staff_service.py` — read-only lead scoring/bucketing service, artifact writer, Slack digest renderer, and safety boundaries.
- `scripts/ares_chief_of_staff_digest.py` — CLI runner for dry-run, artifact generation, and opt-in Slack delivery.
- `tests/services/test_ares_chief_of_staff_service.py` — service tests for hot/contact-ready/research/skiptrace/blocked queues, artifact output, Slack payload safety, and no contact PII in Slack text.
- `tests/db/test_leads_repository.py` — covers slug business tenant resolution for Supabase lead listing so Chief of Staff reads stay tenant-scoped.
- `tests/scripts/test_ares_chief_of_staff_digest.py` — CLI dry-run JSON contract test, including configured artifact-root no-write behavior.
- `supabase/migrations/20260518130327_chief_of_staff_slack_route.sql` — extends the Slack notification route check constraint to allow `chief_of_staff_digest`.
- `docs/qc/2026-05-18/ares-chief-of-staff-v0/` — QC evidence for this slice.

## Modified files

- `.env.example` — adds `SLACK_CHANNEL_CHIEF_OF_STAFF` and `ARES_CHIEF_OF_STAFF_ARTIFACT_ROOT`.
- `README.md` — documents Chief of Staff usage, safety boundaries, artifact output, and Slack readiness.
- `app/core/config.py` — adds `slack_channel_chief_of_staff` and `ares_chief_of_staff_artifact_root` settings.
- `app/db/leads.py` — resolves non-numeric business slugs to Supabase tenant PKs before listing leads, preventing environment-wide reads for `limitless/prod` style inputs.
- `app/models/slack_notifications.py` — adds `SlackNotificationRoute.CHIEF_OF_STAFF_DIGEST`.
- `app/services/slack_notification_service.py` — routes `chief_of_staff_digest` to `SLACK_CHANNEL_CHIEF_OF_STAFF`.
- `scripts/slack_notification_readiness.py` — adds readiness/sample rendering for the Chief of Staff route.
- `tests/api/test_runtime_config_contract.py` — covers safe defaults and `.env.example` contract for the new settings.
- `tests/db/test_slack_notifications_repository.py` — verifies the new Slack route migration.
- `tests/scripts/test_slack_notification_readiness.py` — covers Chief of Staff route readiness/sample behavior.
- `tests/services/test_slack_notification_service.py` — covers posting to the dedicated Chief of Staff Slack channel.
