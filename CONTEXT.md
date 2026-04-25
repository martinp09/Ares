# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Active checkout: `/Users/solomartin/Projects/Ares`
- Branch: `feature/ares-crm-control-plane-planning`
- Baseline before production patch: `902570240f777e9be0c16db59927042d16a48755`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Planning branch for the Ares CRM/control-plane product slice.
- Production wiring is live and must remain untouched while planning.
- CRM control-plane draft spec: `docs/superpowers/specs/2026-04-25-ares-crm-control-plane-design.md`
- CRM roadmap: `docs/superpowers/plans/2026-04-25-ares-crm-control-plane-roadmap.md`
- Source research: `docs/mission-control-wiki/raw/articles/2026-04-25-ghl-datasift-crm-research.md`
- Vault wiki concept: `wiki/Concepts/Ares CRM Control Plane.md`

## Current TODO
1. Review and approve or revise the CRM control-plane spec.
2. Start implementation with CRM shell over current state, then Records workspace/registry.
3. Add configurable pipelines/stage history after Records are modeled.
4. Defer owner/property graph, research cockpit, and map UI until the CRM shell, Records, and stage model are stable.

## Recent Change
- 2026-04-25: Added Records as a first-class top-level workspace and canonical Supabase-backed inventory layer in the CRM spec/roadmap.
- 2026-04-25: Created and pushed `feature/ares-crm-control-plane-planning`.
- 2026-04-25: Researched Go High Level and DataSift/REISift patterns for Ares CRM/control-plane planning.
- 2026-04-25: Added repo and vault wiki notes plus CRM control-plane draft spec/roadmap.
- 2026-04-25: Production Ares deployed to public Vercel URL with provider-compatible callback auth/parsing.
- 2026-04-25: Instantly webhook `019dc29e-bd0f-7ceb-a8f6-1dd9af1a7645` configured to production Ares and provider test returned 200.
- 2026-04-25: TextGrid live SMS to `+13467725914` was received; signed form-encoded TextGrid callback returned 200.
- 2026-04-25: Cal.com webhook `3d941b34-6943-44ed-b9b0-8904ebab0978` is active and synthetic booking webhook returned 200.
- 2026-04-25: Resend live email smoke to `dejesusperales16@gmail.com` queued with provider id `4a9172b4-dd9d-403e-9b59-2cb2304cb7e1`.
- 2026-04-25: Supabase rollback bundle saved at `/Users/solomartin/Projects/Ares-backups/2026-04-25-awmsrjeawcxndfnggoxw`.
- 2026-04-25: Trigger prod env targets production Ares and worker version `20260425.6` is deployed; `run_4` callback smoke completed.
- 2026-04-25: Verification passed: backend pytest, Mission Control test/typecheck/build, Trigger typecheck, lock/diff checks, no-live full-stack smoke.
- 2026-04-25: Saved approved polished ARES dashboard theme mockup under `docs/design/`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
