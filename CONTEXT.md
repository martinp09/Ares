# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Active checkout: `/Users/solomartin/Projects/Ares`
- Branch: `main`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- CRM/control-plane product slice has been merged to `main`.
- Production wiring is live and must remain untouched unless explicitly requested.
- CRM control-plane draft spec: `docs/superpowers/specs/2026-04-25-ares-crm-control-plane-design.md`
- CRM roadmap: `docs/superpowers/plans/2026-04-25-ares-crm-control-plane-roadmap.md`
- Source research: `docs/mission-control-wiki/raw/articles/2026-04-25-ghl-datasift-crm-research.md`
- CRM concept: `docs/mission-control-wiki/concepts/ares-crm-control-plane.md`

## Current TODO
1. Consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary; current Records bulk UI fans out through real single-record command callbacks.
2. Remote Supabase CRM migrations are applied; restart local backend with `LEAD_MACHINE_BACKEND=supabase` to view live leads.
3. Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.
4. Keep promotion source-lane selection explicit once canonical source-lane metadata is added to records.

## Recent Change
- 2026-04-29: Converted Pipeline into the default full-screen CRM surface by giving Mission Control a CRM shell mode, compact CRM rail, hidden legacy header/context frame, responsive command metrics, and direct Pipeline boot.
- 2026-04-29: Polished Pipeline into the target CRM concept surface with a light enterprise cockpit, source-lane controls, full stage lanes, metrics, and a charcoal opportunity drawer.
- 2026-04-29: Rebuilt Pipeline into an enterprise CRM board with scoped opportunity rows, kanban stages, selected-opportunity detail, and real stage movement controls.
- 2026-04-29: Applied CRM remote Supabase migrations and fixed Mission Control lead-machine projection to read repositories in Supabase mode; local Records now shows 482 live leads.
- 2026-04-29: Added Records bulk selection/actions for marketable, needs-skip-trace, and suppress flows using existing real CRM command callbacks.
- 2026-04-29: Wired Mission Control Pipeline UI controls to the real opportunity stage movement API, with dashboard refresh and focused frontend/API tests.
- 2026-04-29: Added Mission Control opportunity stage movement and stage-history APIs backed by configured-stage service validation.
- 2026-04-29: Completed CRM Records registry, saved views, row actions, promotion, bulk actions, Pipeline config/stage history, and stage movement API/UI.
- 2026-04-25: Production Ares deployed to public Vercel URL with provider-compatible callback auth/parsing; title-packet persistence landed on main.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
