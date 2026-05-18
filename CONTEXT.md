# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Release branch: `main`
- Active branch/worktree: `feature/ares-chief-of-staff-v0` at `/opt/ares/worktrees/ares-chief-of-staff-v0`
- Runtime API public HTTPS edge: `https://ares.tail485fd9.ts.net` (Tailscale Funnel -> `127.0.0.1:8000`; protected routes require bearer auth)
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Martin approved **Ares Chief of Staff v0** as the first AI employee/lead desk operator; it must stay separate from Telegram and use Slack/operator artifacts for human-readable lead visibility.
- This branch adds a read-only Chief of Staff digest: lead scoring/bucketing, hot/contact-ready/research/skiptrace/blocked queues, Markdown/JSON/CSV artifacts, and an opt-in Slack digest route `chief_of_staff_digest` using `SLACK_CHANNEL_CHIEF_OF_STAFF`.
- Safety boundary: Chief of Staff v0 never sends seller outreach, spends paid skiptrace, enrolls Instantly, writes HubSpot/provider records, calls SMS/email/Vapi, or posts to Telegram.
- Slack route/config is code-ready but not live-activated in this slice. Configure `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, and `SLACK_CHANNEL_CHIEF_OF_STAFF` after deploy before sending.
- Supabase migration file `20260518130327_chief_of_staff_slack_route.sql` is added but not remotely applied in this slice.

## Current TODO
1. Review, commit, and push `feature/ares-chief-of-staff-v0`.
2. After merge/deploy, apply the new Slack route migration and configure/create/invite the `#ares-chief-of-staff` Slack channel.
3. Run `uv run python scripts/slack_notification_readiness.py --json --render-sample --route chief_of_staff_digest` before any live Chief of Staff Slack post.
4. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
5. Later: wire the same Chief of Staff queues into Mission Control once the CLI/artifact/Slack brief is proven useful.

## Recent Change
- 2026-05-18: Added Ares Chief of Staff v0. Verification: focused/regression tests `51 passed`, full backend `1143 passed`, configured artifact-root dry-run side-effect check `dry_run_artifacts_created=0`, and `git diff --check`/`git diff --cached --check` passed. QC: `docs/qc/2026-05-18/ares-chief-of-staff-v0/`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
