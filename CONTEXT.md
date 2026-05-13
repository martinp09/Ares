# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/opt/ares/worktrees/ares-hubspot-crm-customization`
- Active branch: `feature/hubspot-crm-customization`
- Base: `origin/main` at `397f37e`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- HubSpot CRM customization scaffold for Ares operator workflows.
- Adds dry-run-first endpoints:
  - `POST /crm/hubspot/customization`
  - `POST /crm/hubspot/records/sync`
- HubSpot live writes require both `PROVIDER_LIVE_SENDS_ENABLED=true` and `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true`.
- HubSpot credentials are env-only; do not commit raw keys.

## Current TODO
1. Finish ship gate for `feature/hubspot-crm-customization`: QC artifacts, diff checks, commit/push.
2. Before live HubSpot writes, move credentials to deployment env, rotate any token pasted in chat, dry-run inspect the customization payload, then enable live-write gates intentionally.
3. After live HubSpot customization, set `HUBSPOT_DEFAULT_PIPELINE_ID` and `HUBSPOT_DEFAULT_DEAL_STAGE_ID` from the created portal pipeline before syncing records.
4. Keep Vapi setup deferred until a separate voice-agent activation date.

## Recent Change
- 2026-05-13: Added HubSpot provider client, Ares CRM customization service, HubSpot routes, tests, env placeholders, and docs. Verification: focused HubSpot tests `13 passed`, full backend suite `690 passed`, `compileall` passed, and `git diff --check` passed.
- 2026-05-10: Vapi voice-agent scaffold landed on `origin/main` and remains dry-run until Vapi env/live gates are set.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
