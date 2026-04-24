# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Local test checkout: `/tmp/ares-production-readiness`
- Branch: `test/production-readiness-handoff`
- Base commit: `0c14769` (`origin/main`)
- Production-readiness handoff: `docs/production-readiness-handoff.md`
- Curative-title data pipeline doctrine: `docs/curative-title-data-pipeline.md`
- Curative-title workflow wiki: `docs/curative-title-wiki/index.md`
- Production-readiness plan: `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`

## Current Scope
- This branch is a test/handoff branch for the remaining live-production wiring gates.
- Ares is code-wired, but not production-ready until live Supabase, Ares runtime, Trigger.dev, Mission Control, providers, smoke evidence, and rollback evidence are proven.
- No production migrations, production deploys, Trigger deploys, or live provider sends are performed by this branch.
- Mission Control must point at Ares runtime APIs; it must not call Supabase directly.

## Current TODO
1. Use `docs/production-readiness-handoff.md` as the operator checklist.
2. Execute the plan phases in `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`.
3. Create rollout evidence files under `docs/rollout-evidence/` as each hosted gate is proven.
4. Do not call Ares fully production-ready until the final acceptance gate and production evidence are complete.

## Recent Change
- 2026-04-24: Implemented first tax-overlay adapter slice: Harris parser hardened and live-smoked on Tangie/McMahan accounts, Travis quick-search adapter/parser implemented and live-smoked, Dallas/Montgomery ACT detail parser scaffolded with fixture coverage, Tarrant deferred.
- 2026-04-24: Discovered official tax overlay portals for all five Phase-1 counties and saved adapter matrix under `docs/rollout-evidence/tax-overlay-discovery-2026-04-24/`; Harris and Travis are directly probeable, Dallas/Montgomery are ACT Web portals timing out here, and Tarrant is Cloudflare-blocked in this environment.
- 2026-04-24: Ran HCAD/property match test for top contact packets; Tangie (`543678`) matched HCAD acct `1091100001181` / `1407 GREEN TRAIL DR` / `FALLBROOK SEC 3`, McMahan (`543652`) matched acct `1172610010016`, and Montoya (`525833-401`) remains ambiguous pending partition/property document extraction.
- 2026-04-24: Generated contact-candidate packets for the 12 enriched Harris probate keep-now leads under `docs/rollout-evidence/contact-candidate-packets-2026-04-24/`; top ready-for-paid-skiptrace packets are Tangie Williams (`543678`), Daniel R. Montoya (`525833-401`), and Janet Marie Mcmahan (`543652`).
- 2026-04-24: Consolidated curative-title process docs into `docs/curative-title-wiki/index.md` with separate linked pages for operating model, browser-harness workflow, county land records, evidence graph, skiptrace, contact-candidate packets, and the Tangie Williams field test.
- 2026-04-24: Ran first browser-harness curative-title land-record recon field test on Tangie Renee Williams / Harris probate case `543678`; saved Fallbrook and Perkins/Otis Williams estate document-thread evidence under `docs/rollout-evidence/land-records-recon-2026-04-24/`.
- 2026-04-24: Added `docs/curative-title-data-pipeline.md` to make land-record document/deed review and browser-harness research foundational for curative-title heir/descendant discovery.
- 2026-04-24: Added Harris probate rollout evidence: 202 last-week rows, 113 keep-now rows, 12 priority heirship/title-friction case-detail enrichments, and an Ares memory-backed intake simulation that bridged all 12 priority cases into canonical leads while leaving HCAD/tax overlay as the next backend gap.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
