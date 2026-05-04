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
1. Apply current buy-box filters in future scoring/import slices: no mobile homes; SFR/1–4 preferred; commercial review only; $150k–county median core tax/title band; $500k+ creative-finance lane. Canonical note: `docs/lead-scoring/buy-box-filters.md`.
2. Capture stronger primary Alen Sultanic source material (authenticated transcript/source upload) and update `docs/copywriting-wiki/`.
3. Add Mission Control read/approval endpoints for Ares offer/copy assets.
4. Add dedicated Mission Control frontend campaign-launch review page for `GET/POST /mission-control/campaign-launches/harris-probate-hot-warm-cold`.
5. Enrich Harris probate exports with email/phone via Tracerfy before any Instantly/TextGrid enrollment; single-record CRM skiptrace endpoint is wired, batch export enrichment is next. Current artifact is direct-mail-ready only.
6. Consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary; current Records bulk UI fans out through real single-record command callbacks.
7. Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.

## Recent Change
- 2026-05-04: Added Tracerfy as the current Ares skiptrace provider: `TRACERFY_API_KEY`, `app/providers/tracerfy.py`, CRM enrichment service, and `POST /mission-control/records/{record_id}/skiptrace`. Docs/QC: `docs/integrations/tracerfy-skiptrace.md`, `docs/qc/2026-05-04/tracerfy-skiptrace-provider/`. Focused suite: 46 passed; full backend suite: 620 passed after test-environment isolation hardening.
- 2026-05-03: Updated local `.env` to the newly supplied Instantly real-account API key, then safe read preflight hit `HTTP 402 Payment Required` / `Workspace does not have an active paid plan`; no campaigns, subsequences, leads, activations, or sends happened. QC: `docs/qc/2026-05-03/instantly-real-account-sync/`.
- 2026-05-02: Created two Instantly long-nurture subsequences: Probate `7db2176c-2ce5-4633-a2e9-346fdc8fff43` and Tax/Title `494fd6b6-6456-46ea-a79d-0547a172ca95`; trigger is campaign completed without reply, 6 steps through Day 300; no leads, sends, or activation. QC: `docs/qc/2026-05-02/instantly-campaign-nurture-upload/`.
- 2026-05-02: Uploaded two Instantly draft campaigns from local backups: Probate `9b306264-b8d6-4ca3-8628-8d0e10f84d9c` and Tax/Title `70c5b447-2a72-431c-a63d-1fe8fb67c1fe`. Active 4-step sequences only; no leads, sends, or activation. QC: `docs/qc/2026-05-02/instantly-campaign-draft-upload/`.
- 2026-05-02: Patched Ares Instantly client request headers with `Accept: application/json` and a normal `User-Agent`; focused tests passed and live `list_campaigns(limit=1)` preflight now returns 200 with no provider mutation. QC: `docs/qc/2026-05-02/instantly-client-fingerprint-patch/`.
- 2026-05-02: Created full cold-email campaign packets for probate and tax/title-friction sellers under `docs/marketing/campaigns/`, plus local Instantly backups under `docs/marketing/exports/instantly-campaign-backups-2026-05-02/`. Initial Instantly API preflight from default Python urllib fingerprint was blocked with HTTP 403 / error 1010; no live sends or uploads.
- 2026-05-02: Drafted stronger Hormozi/Sultanic probate grand-slam offer at `docs/marketing/copy/2026-05-02-probate-grand-slam-offer-v1.md`: **The Inherited Property Relief Plan**. Added REI multichannel playbook doctrine: cold email speed/testing, direct mail trust/persistence, SMS consent/inbound only.
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
