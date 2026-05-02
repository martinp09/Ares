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
1. Capture stronger primary Alen Sultanic source material (authenticated transcript/source upload) and update `docs/copywriting-wiki/`.
2. Add Mission Control read/approval endpoints for Ares offer/copy assets.
3. Add dedicated Mission Control frontend campaign-launch review page for `GET/POST /mission-control/campaign-launches/harris-probate-hot-warm-cold`.
4. Enrich Harris probate exports with email/phone before any Instantly/TextGrid enrollment; current artifact is direct-mail-ready only.
5. Consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary; current Records bulk UI fans out through real single-record command callbacks.
6. Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.

## Recent Change
- 2026-05-02: Added Alen high-response email formula and offer-code/Rosetta Stone concept to the copywriting wiki and backend copy brain: email assets now store recency/relevance/personalization signals, give-CTA metadata, offer-code insights, and mechanism/outcome-first copy.
- 2026-05-01: Started Ares copywriting brain execution: repo-local `docs/copywriting-wiki/`, Hormozi/Sultanic source notes, Harris probate `Inherited Property Exit Option`, typed offer/copy asset models/services, upgraded `AresCopyService`, and QC at `docs/qc/2026-05-01/copywriting-brain-offer-engine/`.
- 2026-04-30: Added Harris probate campaign launch backend slice: HOT/WARM/COLD export manifests, no-send-before-approval CSVs, approval-gated command endpoint, campaign plan, copywriting expertise plan, and QC at `docs/qc/2026-04-30/harris-probate-campaign-launch/`.
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
