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
- Martin approved **Ares Chief of Staff** as the first AI employee/lead desk operator; it must stay separate from Telegram and report through Slack/operator artifacts.
- This branch now has Chief of Staff v3 runtime scheduling: the v2 read-only lead desk report still scores/buckets leads into hot/contact-ready/research/skiptrace/blocked queues, writes Markdown/JSON/CSV artifacts, and renders a PII-redacted Slack digest; the new protected endpoint `POST /ares-chief-of-staff/internal/check-in` returns a Trigger-safe `ares_chief_of_staff_check_in_v1` summary with queue counts, safety flags, and artifact path map when artifacts are written; Trigger includes a gated `chief-of-staff-check-in-0815-ct` daily 08:15 CT employee check-in.
- Slack reports are intentionally PII-redacted: no lead names, contact details, property addresses, raw case numbers, or raw lead IDs in Slack text/blocks/payload or Trigger check-in responses. Exact details remain in local operator artifacts.
- Safety boundary: Chief of Staff v3 never sends seller outreach, spends paid skiptrace, enrolls Instantly, writes HubSpot/provider records, calls SMS/email/Vapi, runs live county/source pulls, executes manager approvals, posts live Slack without explicit Slack gates, or posts to Telegram.
- Slack route/config is code-ready but not live-activated in this slice. Configure `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_CHIEF_OF_STAFF`, and `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=true` after deploy before the scheduled employee check-in can post to Slack.
- Supabase migration file `20260518130327_chief_of_staff_slack_route.sql` is added but not remotely applied in this slice.

## Current TODO
1. Review and merge `feature/ares-chief-of-staff-v0` after the Chief of Staff trigger check-in slice is accepted.
2. After merge/deploy, apply the new Slack route migration and configure/create/invite the `#ares-chief-of-staff` Slack channel.
3. Run `uv run python scripts/slack_notification_readiness.py --json --render-sample --route chief_of_staff_digest` before any live Chief of Staff Slack post.
4. Keep `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=false` until the Slack channel/bot readiness smoke is green; then enable it only for the scheduled employee check-in.
5. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
6. Later: add a Slack reply inbox / decision journal for `approve/deny cos_action_...` that records manager intent only, without calling the generic approval executor.
7. For email marketing launch: review the Herrington/Browne draft campaign and verification QC, then approve exact contacts/copy/enrollment before any Instantly upload, activation, or seller send.
8. For SMS: use the temporary owned-number smoke transcript only for Martin's approved number; do not enable global SMS auto-replies until a scoped production approval/receiver exists.

## Recent Change
- 2026-05-18: Prepared the first Herrington/Browne email-marketing packet and verification gate. Added draft-only curative-title/ambiguous-heirship soft-finder campaign docs/backups, ran local syntax/MX/disposable/role checks plus Instantly email verification and duplicate probes for five candidate emails, and stored raw PII evidence outside repo docs under `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/`. No Instantly lead upload, campaign activation, or seller email send occurred. Also created an owned-number SMS smoke lead for Martin, sent one TextGrid test SMS to his approved number, confirmed provider status `delivered`, and started a temporary allowlisted qualification watcher for that number only. QC: `docs/qc/2026-05-18/email-marketing-herrington-browne-prep/`.
- 2026-05-18: Added Chief of Staff trigger check-in/schedule. New protected endpoint `POST /ares-chief-of-staff/internal/check-in` returns a Trigger-safe `ares_chief_of_staff_check_in_v1` summary, Trigger has `chief-of-staff-check-in` plus daily `chief-of-staff-check-in-0815-ct`, Slack delivery is separately gated by `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=false` by default, and no live Slack/provider/source/outreach side effects occurred. Verification: focused suite `61 passed`, Trigger typecheck passed, API smoke returned `200` with Slack blocked by gate, full backend `1148 passed`. QC: `docs/qc/2026-05-18/ares-chief-of-staff-trigger-check-in/`.
- 2026-05-18: Expanded Mission Control record/navigation segmentation after browser QA: richer real-estate left rail, `Operator scope` replacement for `Organization scope`, visible Records / Property Cards / Owner Cards / Skip Trace / Tax-Title pages, and property-owner detail cards. Verification: Mission Control typecheck passed, `25` test files / `85` tests passed, Vite build passed, browser-harness click sweep covered `15` nav clicks with `0` failed clicks, browser smoke had `0` console/JS errors, and `git diff --check` passed. QC: `docs/qc/2026-05-18/ares-mission-control-record-segmentation/`.
- 2026-05-18: Refreshed Mission Control overview into a segmented analytics dashboard inspired by `builderz-labs/marketing-dashboard`: KPI strip, graph-style lane performance, contact-mix donut, acquisition funnel, blocker chart, and segmented operating cards. Verification: Mission Control typecheck passed, `25` test files / `83` tests passed, Vite build passed, browser smoke had zero console/JS errors, and backstage/admin words were hidden from the visible overview. QC: `docs/qc/2026-05-18/ares-dashboard-analytics-segmentation/`.
- 2026-05-18: Added Chief of Staff v2 manager-action packet. Verification: focused/regression tests `52 passed`, full backend `1144 passed`, configured artifact-root/source-run-state dry-run side-effect check `dry_run_artifacts_created=0` and `dry_run_source_state_created=0`, and `git diff --check` passed. QC: `docs/qc/2026-05-18/ares-chief-of-staff-v2-manager-actions/`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
