# Activation Env-File Readiness QC

Date: 2026-05-10
Branch: `chore/activation-readiness-envfile-2026-05-10`
Repo: `martinp09/Ares`

## Scope

Martin asked to proceed with activation. Slack bot token and Vercel/Trigger auth are not available in this environment, so this pass finished the fixable non-secret work:

- Added env-file support to `scripts/activation_readiness.py` so the existing local VPS env can be checked without copying secrets into `/root/Ares-inspect`.
- Added `--runtime-url` + `--derive-local-defaults` to derive safe callback/landing URLs and local booking URL mapping.
- Kept live sends disabled; no live SMS/email/Slack/Trigger provider dispatch was attempted.
- Ran local dark Ares intake smoke with memory backends and `PROVIDER_LIVE_SENDS_ENABLED=false`.

## Commands / Evidence

- `python scripts/activation_readiness.py --json --env-file /opt/ares/Ares/.env --runtime-url https://production-readiness-afternoon.vercel.app --derive-local-defaults`
  - exit: `2` expected while activation is still blocked
  - artifact: `activation-readiness-envfile-output.json`
  - verdict: `blocked`
  - blocker count: `5`
  - safe to deploy dark: `true`
- Local dark TestClient smoke with loaded local env and `PROVIDER_LIVE_SENDS_ENABLED=false`
  - artifact: `local-dark-intake-smoke-output.json`
  - provider status route: `200`
  - `POST /marketing/leads`: `201`
  - side effects: `confirmation_sms`, `confirmation_email`, `operator_slack_notification`, `trigger_non_booker_check` all `skipped`
- Hosted dark smoke against `https://production-readiness-afternoon.vercel.app`
  - artifact: `hosted-authenticated-dark-smoke-output.json`
  - `/health`: `200`
  - protected `/mission-control/providers/status`: `401` with the local runtime key, so production env/Vercel verification remains required
- Vercel auth check
  - artifact: `vercel-auth-check.txt`
  - result: no existing Vercel credentials
- Trigger auth check
  - artifact: `trigger-auth-check.txt`
  - result: Trigger CLI not logged in
- `uv run pytest tests/scripts/test_activation_readiness.py -q`
  - artifact: `test-output.txt`
  - result: `6 passed`
- `uv run pytest -q`
  - artifact: `full-test-output.txt`
  - result: `654 passed`
- `python scripts/smoke_provider_readiness.py`
  - artifact: `provider-shape-output.json`
  - result: request-shape-only smoke, no live send
- `git diff --check`
  - artifact: `diff-check.txt`
  - result: passed

## Remaining Blockers

- `PROVIDER_LIVE_SENDS_ENABLED=false` remains intentionally safe until the final approved live smoke.
- `RESEND_FROM_EMAIL` is present in the local env but invalid; set it to a verified sender identity.
- `SLACK_BOT_TOKEN` is missing.
- `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` is missing.
- `CAL_WEBHOOK_SECRET` is missing and must match the external Cal.com webhook config.
- Hosted protected routes still return `401` with the local runtime key; Vercel/production env access is required to verify/update deployed `RUNTIME_API_KEY` and landing envs.
- TextGrid still needs account funding confirmation before live SMS can be claimed.

## Safety Notes

- No raw secrets were written to tracked artifacts.
- Local env values are represented only through presence, lengths, fingerprints, or sanitized URLs.
- Local dark smoke used fake lead data and provider live sends disabled.
- No Vercel env updates, Trigger deployments, Slack posts, SMS sends, or email sends were performed.
