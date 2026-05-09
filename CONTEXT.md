# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout for this slice: `/root/Ares-inspect`
- Active branch: `feat/harris-daily-lead-machine-foundation`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Harris daily lead-machine foundation is implemented locally on `feat/harris-daily-lead-machine-foundation`.
- New runtime endpoint: `POST /lead-machine/harris/daily-import`.
- New Trigger task: `harris-daily-import` in `trigger/src/lead-machine/harrisDailyImport.ts`.
- The daily import path supports dry-run probate + HCAD `Estate Of` processing, CRM import when `dry_run=false`, QC warnings, and no provider sends.
- Slack is readiness metadata only; no Slack posts are sent until `SLACK_BOT_TOKEN` and channel config are available and a delivery adapter is explicitly wired.
- Vercel deployment/hosted smoke are blocked until Vercel auth is available.
- Production wiring is live and must remain untouched unless explicitly requested.

## Current TODO
1. Open PR/merge `feat/harris-daily-lead-machine-foundation` after operator review; branch is pushed to origin.
2. Wire/test real Slack digest delivery only after Slack bot token + target channels are available.
3. Deploy/smoke hosted runtime only after Vercel auth is available.
4. Add dedicated Mission Control frontend campaign-launch review page for `GET/POST /mission-control/campaign-launches/harris-probate-hot-warm-cold`.
5. Enrich Harris probate exports with email/phone before any Instantly/TextGrid enrollment; current campaign artifact is direct-mail-ready only.
6. Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.

## Recent Change
- 2026-05-09: Added Harris daily probate + HCAD `Estate Of` import foundation, Slack readiness config, Trigger task contract, focused/full backend tests, and QC at `docs/qc/2026-05-09/harris-daily-lead-machine-foundation/`.
- 2026-04-30: Added Harris probate campaign launch backend slice: HOT/WARM/COLD export manifests, no-send-before-approval CSVs, approval-gated command endpoint, campaign plan, copywriting expertise plan, and QC at `docs/qc/2026-04-30/harris-probate-campaign-launch/`.
- 2026-04-29: Completed CRM Records registry, saved views, row actions, promotion, bulk actions, Pipeline config/stage history, and stage movement API/UI.
- 2026-04-25: Production Ares deployed to public Vercel URL with provider-compatible callback auth/parsing; title-packet persistence landed on main.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
