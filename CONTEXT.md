# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Working checkout: `/Users/solomartin/Projects/Ares/.worktrees/feature-textgrid-sms-agent`
- Release branch: `main`
- Active branch: `feature/textgrid-sms-agent`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- TextGrid SMS reply-agent branch is active. Spec: `docs/superpowers/specs/2026-05-16-textgrid-sms-reply-agent-design.md`; plan: `docs/superpowers/plans/2026-05-16-textgrid-sms-reply-agent-implementation-plan.md`; concept: `docs/mission-control-wiki/concepts/textgrid-sms-reply-agent.md`.
- This branch extends the existing `/sms-agent` scaffold into signed TextGrid webhook ingest, queued reply jobs, draft-only processor, Supabase/in-memory persistence, Mission Control review, Trigger scheduling, redacted archive export, and local smoke tooling.
- Supabase is the hot operational source of truth. Obsidian/JSONL is a redacted cold eval/archive layer only.
- Auto replies remain disabled until both global provider sends and `SMS_AGENT_AUTO_REPLIES_ENABLED` are explicitly approved.
- Slack notification routing is now merged on `origin/main` and VPS: persisted Slack attempts, readiness checks, and route notifications for lead-run digests, hot leads, Instantly replies, lease-option inbound leads, SMS replies, and Vapi events.
- Slack activation still requires route channels, bot membership, `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, and route channel IDs on the VPS. Readiness blocks without posting while those env vars are missing.
- VPS `100.74.177.6` live Ares is deployed from `ff7dd9b`/image revision `fc99b75` lineage: API/UI healthy, loopback-only Docker ports, durable `/var/lib/ares/lead-machine` mount, `LEAD_MACHINE_BACKEND=supabase`, and provider/outbound mutation gates false.
- Trigger cloud deploy remains blocked by Trigger CLI auth. Hermes no-agent cron `815e1261ab2e` remains the active no-send CT scheduler/watchdog until Trigger auth is recovered.

## Current TODO
1. Finish `feature/textgrid-sms-agent` QC after merging latest `origin/main` Slack routing changes.
2. Watch the next Hermes no-agent CT scheduler window for the first post-deploy `limitless/prod` autonomous morning brief.
3. Recover Trigger.dev CLI auth and deploy `trigger/` from `ff7dd9b` or newer, then pause Hermes autonomous scheduling to avoid duplicate source runs.
4. Add a Harris postback case-detail client if live Harris party/event/document detail completion is required.
5. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
6. Activate Slack only after route channels exist, the bot is invited, and VPS env has the Slack token plus route channel IDs.

## Recent Change
- 2026-05-16: Reconciled `feature/textgrid-sms-agent` with latest `origin/main` after Slack notification routing landed; merged webhook JSON notification behavior with TextGrid reply-job enqueue behavior. Branch still makes no live Supabase/TextGrid/provider mutation and no deploy.
- 2026-05-16: Passworded VPS inspection found `/var/lib/ares/lead-machine/source-runs.json` was `root:root 600` while `ares-api` runs as UID/GID `999`; repaired to `999:999 640`. Authenticated probate health now returns `200 healthy`, `no_send_ok=true`, and `outbound_allowed=false`.
- 2026-05-16: Added TextGrid SMS reply-agent runtime: signed TextGrid webhook ingest, queued reply jobs, Supabase/in-memory persistence, deterministic classifier, draft-only defaults, protected processor, Trigger schedule, Mission Control review/operator actions, redacted archive export, local smoke script, activation runbook, and QC artifacts.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
