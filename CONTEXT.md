# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Working checkout: `/Users/solomartin/Projects/Ares/.worktrees/feature-vapi-real-estate-agent`
- Release branch: `main`
- Active branch: `main`
- Runtime API public HTTPS edge: `https://ares.tail485fd9.ts.net` (Tailscale Funnel -> `127.0.0.1:8000`; protected routes require bearer auth)
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Local `main` now contains the TextGrid SMS reply-agent implementation plus latest `origin/main` Slack activation docs.
- TextGrid SMS reply-agent source docs: `docs/superpowers/specs/2026-05-16-textgrid-sms-reply-agent-design.md`, `docs/superpowers/plans/2026-05-16-textgrid-sms-reply-agent-implementation-plan.md`, and `docs/mission-control-wiki/concepts/textgrid-sms-reply-agent.md`.
- TextGrid runtime remains draft-safe: public signed webhook ingest queues jobs, protected processor drafts/blocks replies, Mission Control exposes review/operator actions, Supabase is hot operational truth, and Obsidian/JSONL is redacted cold eval/archive only.
- Auto SMS replies remain disabled until both global provider sends and `SMS_AGENT_AUTO_REPLIES_ENABLED` are explicitly approved.
- Slack notification routing is live in code and on VPS: persisted attempts, readiness checks, and route notifications for lead-run digests, hot leads, Instantly replies, lease-option inbound leads, SMS replies, and Vapi events.
- Slack route channels exist, the Ares Slack bot is installed with `chat:write` and `chat:write.public`, VPS env has `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, and all five route channel IDs, readiness is configured, and Slack `auth.test` passes. No live Slack test posts were sent.
- VPS `100.74.177.6` live Ares is deployed from current `origin/main`/`61f18de` with healthy API/UI, loopback-only Docker ports, durable `/var/lib/ares/lead-machine` mount, `LEAD_MACHINE_BACKEND=supabase`, TextGrid SMS reply-agent code live in draft-only/no-auto-reply mode, Slack notifications configured, and provider/outbound mutation gates false.
- Trigger CLI auth is recovered for Hermes; `trigger.dev whoami` works for project `proj_puouljyhwiraonjkpiki`.
- Trigger prod `20260516.2` is deployed with schedule-level safety gates. Trigger prod env now points at current Ares through `https://ares.tail485fd9.ts.net`, runtime key fingerprint matches the VPS key, and protected probate health returns `200 healthy/no_send_ok=true/outbound_allowed=false`; schedules intentionally remain no-op with `ARES_TRIGGER_SCHEDULES_ENABLED=false` to avoid duplicate runs while Hermes cron is authoritative.
- Hermes no-agent cron `815e1261ab2e` remains active as the authoritative no-send CT scheduler/watchdog until one controlled Trigger no-send run is proven and cron is intentionally paused.

## Current TODO
1. Run one controlled Trigger no-send schedule/test window against `https://ares.tail485fd9.ts.net`; if it produces the expected no-send source/enrichment lifecycle without duplicates, then set `ARES_TRIGGER_SCHEDULES_ENABLED=true` and pause Hermes cron `815e1261ab2e`.
2. Watch the next Hermes no-agent CT scheduler window for the next `limitless/prod` autonomous morning brief while Hermes remains authoritative.
3. Monitor the public Funnel API edge for protected-route `401` without bearer, protected health `200` with Trigger bearer, and no provider/outbound side effects.
4. Add a Harris postback case-detail client if live Harris party/event/document detail completion is required.
5. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
6. Monitor the first automatic Slack notifications from scheduled lead runs/enrichment/reply webhooks; ask before any live manual Slack test post.

## Recent Change
- 2026-05-16: Advanced VPS `/opt/ares/Ares` to current `origin/main`/`61f18de`, rebuilt/recreated `ares-api` and `ares-ui`, made the API reachable to Trigger through Tailscale Funnel at `https://ares.tail485fd9.ts.net`, updated Trigger prod runtime env/key to that edge, kept `ARES_TRIGGER_SCHEDULES_ENABLED=false`, and verified direct API auth, tailnet UI/API, Funnel API, Trigger-env protected probate health, SMS draft processor, Supabase SMS/Slack/probate tables, and Trigger typecheck. QC: `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/`.
- 2026-05-16: Recovered Trigger CLI auth for Hermes by copying the existing VPS Trigger config into Hermes HOME; deployed Trigger prod `20260516.1`, found Trigger prod env was targeting stale Vercel where protected probate health returned `404`, then deployed guarded Trigger prod `20260516.2` so schedules no-op unless `ARES_TRIGGER_SCHEDULES_ENABLED=true`; this stale-runtime finding was superseded by the Funnel runtime alignment above, but Hermes cron `815e1261ab2e` remains active until controlled Trigger no-send promotion.
- 2026-05-16: Merged latest Slack activation docs from `origin/main` into local `main` with the TextGrid SMS reply-agent commits. Code conflicts were not present; router-doc conflicts were resolved to keep both Slack activation and TextGrid SMS agent state.
- 2026-05-16: Created/installed the Ares Slack app in the Ares workspace with bot scopes `chat:write` and `chat:write.public`; stored `SLACK_BOT_TOKEN` in `/opt/ares/Ares/.env` on VPS `100.74.177.6`; recreated only `ares-api`; readiness reports `configured=true`, `missing=[]`, and all five configured routes `would_post=true`; Slack `auth.test` returned `ok=true` for team `Ares`; `/health` returned `{"status":"ok"}`. No live Slack posts were made.
- 2026-05-16: Added TextGrid SMS reply-agent runtime: signed webhook ingest, queued reply jobs, Supabase/in-memory persistence, deterministic classifier, draft-only defaults, protected processor, Trigger schedule, Mission Control review/operator actions, redacted archive export, local smoke script, activation runbook, and QC artifacts.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
