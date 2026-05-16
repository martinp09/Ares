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
- Local `main` now contains the TextGrid SMS reply-agent implementation, Slack activation/routing docs, and the Trigger authority-promotion patch that limits Harris/Montgomery probate schedules to exactly three Central Time runs per day.
- TextGrid SMS reply-agent source docs: `docs/superpowers/specs/2026-05-16-textgrid-sms-reply-agent-design.md`, `docs/superpowers/plans/2026-05-16-textgrid-sms-reply-agent-implementation-plan.md`, and `docs/mission-control-wiki/concepts/textgrid-sms-reply-agent.md`.
- TextGrid runtime remains draft-safe: public signed webhook ingest queues jobs, protected processor drafts/blocks replies, Mission Control exposes review/operator actions, Supabase is hot operational truth, and Obsidian/JSONL is redacted cold eval/archive only.
- SMS/TextGrid is live for inbound/queue/processor readiness, but auto SMS replies and provider sends remain intentionally disabled until both global provider sends and `SMS_AGENT_AUTO_REPLIES_ENABLED` are explicitly approved for exact recipients/campaigns.
- Slack notification routing is live in code and on VPS: persisted attempts, readiness checks, and route notifications for lead-run digests, hot leads, Instantly replies, lease-option inbound leads, SMS replies, and Vapi events.
- Slack route channels exist, the Ares Slack bot is installed with `chat:write` and `chat:write.public`, VPS env has `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, and all five route channel IDs, readiness is configured, Slack `auth.test` passes, the controlled Trigger lead run posted to `lead_runs`, and a controlled route test posted to `hot_leads`.
- VPS `100.74.177.6` live Ares is deployed from `61f18de` (runtime rebuild commit; later docs commits may be newer) with healthy API/UI, loopback-only Docker ports, durable `/var/lib/ares/lead-machine` mount, `LEAD_MACHINE_BACKEND=supabase`, TextGrid SMS reply-agent code live in draft-only/no-auto-reply mode, Slack notifications configured, and provider/outbound mutation gates false.
- Trigger CLI auth is recovered for Hermes; `trigger.dev whoami` works for project `proj_puouljyhwiraonjkpiki`.
- Trigger prod `20260516.4` is deployed and is now authoritative for the no-send probate scheduler. Trigger prod env points at current Ares through `https://ares.tail485fd9.ts.net`, `ARES_TRIGGER_SCHEDULES_ENABLED=true`, live source/case-detail/enrichment gates are true, and deployed probate tasks are exactly `harris-montgomery-probate-0710-ct`, `harris-montgomery-probate-1240-ct`, and `harris-montgomery-probate-1740-ct` in `America/Chicago`.
- Controlled Trigger lead run `run_cmp8tvbii55lq0hmz6qca6n5i` completed and produced latest brief `morning_brief_f27f1679d1884a149cf5f3d53fc09f76`; protected probate health is `healthy`, `no_send_ok=true`, and `outbound_allowed=false`.
- Hermes no-agent cron `815e1261ab2e` is paused after the controlled Trigger no-send run proved the path. Trigger is now the scheduler authority; keep Hermes cron paused unless explicitly rolling back.

## Current TODO
1. Watch the next automatic Trigger CT windows (`07:10`, `12:40`, `17:40` America/Chicago) for `limitless/prod` autonomous morning briefs and Slack lead-run digests.
2. Keep Hermes cron `815e1261ab2e` paused unless Trigger must be rolled back.
3. Monitor the public Funnel API edge for protected-route `401` without bearer, protected health `200` with Trigger bearer, and no provider/outbound side effects.
4. Add a Harris postback case-detail client if live Harris party/event/document detail completion is required.
5. Keep all outbound/provider-send controls blocked until Martin approves exact recipients/campaigns.
6. Prepare the marketing launch manifest next: source-approved contacts, suppression/verification, exact copy, exact recipient limits, and approval before Instantly/SMS/email sends.

## Recent Change
- 2026-05-16: Promoted scheduler authority from Hermes cron to Trigger prod. Removed the retired 02:20 daily and Sunday 03:15 weekly probate reconciliation Trigger schedules, deployed Trigger prod `20260516.4`, set `ARES_TRIGGER_SCHEDULES_ENABLED=true`, verified the deployed worker has exactly three Harris/Montgomery probate CT schedules plus the SMS processor, ran controlled lead-machine Trigger run `run_cmp8tvbii55lq0hmz6qca6n5i`, verified latest brief `morning_brief_f27f1679d1884a149cf5f3d53fc09f76`, Slack `lead_runs` delivery, controlled `hot_leads` delivery, SMS processor readiness, TextGrid configured but `can_send=false`, and paused Hermes cron `815e1261ab2e`. QC: `docs/qc/2026-05-16/trigger-promotion-slack-sms-live/`.
- 2026-05-16: Advanced VPS `/opt/ares/Ares` to runtime rebuild commit `61f18de`, rebuilt/recreated `ares-api` and `ares-ui`, made the API reachable to Trigger through Tailscale Funnel at `https://ares.tail485fd9.ts.net`, updated Trigger prod runtime env/key to that edge, kept `ARES_TRIGGER_SCHEDULES_ENABLED=false` at that stage, and verified direct API auth, tailnet UI/API, Funnel API, Trigger-env protected probate health, SMS draft processor, Supabase SMS/Slack/probate tables, and Trigger typecheck. Superseded for scheduler authority by the promotion entry above. QC: `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/`.
- 2026-05-16: Recovered Trigger CLI auth for Hermes by copying the existing VPS Trigger config into Hermes HOME; deployed Trigger prod `20260516.1`, found Trigger prod env was targeting stale Vercel where protected probate health returned `404`, then deployed guarded Trigger prod `20260516.2` so schedules no-op unless `ARES_TRIGGER_SCHEDULES_ENABLED=true`; this stale-runtime finding was superseded by the Funnel runtime alignment and later by the Trigger promotion entry above.
- 2026-05-16: Merged latest Slack activation docs from `origin/main` into local `main` with the TextGrid SMS reply-agent commits. Code conflicts were not present; router-doc conflicts were resolved to keep both Slack activation and TextGrid SMS agent state.
- 2026-05-16: Created/installed the Ares Slack app in the Ares workspace with bot scopes `chat:write` and `chat:write.public`; stored `SLACK_BOT_TOKEN` in `/opt/ares/Ares/.env` on VPS `100.74.177.6`; recreated only `ares-api`; readiness reports `configured=true`, `missing=[]`, and all five configured routes `would_post=true`; Slack `auth.test` returned `ok=true` for team `Ares`; `/health` returned `{"status":"ok"}`. At that time, no live Slack posts were made; later controlled Slack route posts are documented in the promotion entry above.
- 2026-05-16: Added TextGrid SMS reply-agent runtime: signed webhook ingest, queued reply jobs, Supabase/in-memory persistence, deterministic classifier, draft-only defaults, protected processor, Trigger schedule, Mission Control review/operator actions, redacted archive export, local smoke script, activation runbook, and QC artifacts.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
