# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Active checkout: `/opt/ares/worktrees/ares-crm-control-plane-planning`
- Branch: `feature/ares-crm-control-plane-planning`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Implementation branch for the Ares CRM/control-plane product slice, rebased onto current `origin/main` including probate title-packet persistence.
- Production wiring is live and must remain untouched unless explicitly requested.
- CRM control-plane draft spec: `docs/superpowers/specs/2026-04-25-ares-crm-control-plane-design.md`
- CRM roadmap: `docs/superpowers/plans/2026-04-25-ares-crm-control-plane-roadmap.md`
- Source research: `docs/mission-control-wiki/raw/articles/2026-04-25-ghl-datasift-crm-research.md`
- CRM concept: `docs/mission-control-wiki/concepts/ares-crm-control-plane.md`

## Current TODO
1. Validate Records action API, saved views, and pipeline/stage config against Supabase.
2. Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.
3. Keep promotion source-lane selection explicit once canonical source-lane metadata is added to records.

## Recent Change
- 2026-04-29: Exposed source lead/contact identity on canonical Records rows and enabled Mission Control promote-from-record actions when identity is present.
- 2026-04-29: Wired Mission Control Records row actions to the real CRM command API for status changes and suppression; promotion remains gated until source identity is present on rows.
- 2026-04-29: Added CRM record saved views plus a Mission Control saved-view rail for stable Records filters.
- 2026-04-29: Replaced deprecated FastAPI `HTTP_422_UNPROCESSABLE_ENTITY` use and installed a request validation handler to eliminate 422 deprecation warnings.
- 2026-04-29: Added configurable opportunity pipeline configs and stage history for pipeline/stage transitions.
- 2026-04-29: Added deterministic Records action API for import, status changes, suppression, and record-to-opportunity promotion.
- 2026-04-29: Polished Records UI with operator tabs, KPI expansion, read-only action messaging, contactability/data-quality/source badges, and filtered record views.
- 2026-04-29: Added canonical CRM Records registry models/repository/migration and wired Mission Control Records to prefer canonical CRM records when present.
- 2026-04-29: Rebased CRM branch onto current `origin/main` to include probate title-packet persistence before continuing CRM work.
- 2026-04-25: Started CRM buildout with `/mission-control/records`, dashboard record inventory stats, and a Records page beside Pipeline.
- 2026-04-25: Added Records as a first-class top-level workspace and canonical Supabase-backed inventory layer in the CRM spec/roadmap.
- 2026-04-25: Created and pushed `feature/ares-crm-control-plane-planning`.
- 2026-04-25: Added title-packet import route, Supabase schema/repository wiring, and review-task creation for probate intake on main.
- 2026-04-25: Production Ares deployed to public Vercel URL with provider-compatible callback auth/parsing.
- 2026-04-25: Verification passed: backend pytest, Mission Control test/typecheck/build, Trigger typecheck, lock/diff checks, no-live full-stack smoke.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
