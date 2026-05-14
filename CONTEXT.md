# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Active checkout: `/opt/ares/Ares`
- Branch: `feature/copywriting-brain-offer-engine` (pushed to origin; dirty/untracked local extras remain)
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- HubSpot operating spine / agentic company Phases 1-9 are complete and pushed on commit `8c19c26`.
- Post-phase HubSpot portal customization was live-applied after operator instruction; HubSpot itself now has the Ares property groups/properties and Ares stages in the existing single `Sales Pipeline`.
- First HubSpot record-sync canary is complete: one synthetic contact/deal pair created and provider-linked; no batch sync.
- First real HubSpot lead sync is complete: one hand-selected Harris probate lead (`lead_341`, case `543678`) created HubSpot contact `485815102172` and deal `325123310274`; a follow-up rich-field correction added probate/heir/contact/mailing/property fields to HubSpot and updated the same records with applicant/heir metadata; a visibility correction now also fills standard HubSpot contact address fields; no Instantly/Reacher/Vapi/batch/deploy side effects.
- Phase 9 added final QC index/readiness artifacts/runbooks/living-doc updates; no Instantly/Vapi/source-provider/Slack/deploy side effects.
- QC index: `docs/qc/2026-05-14/README.md`
- Final readiness: `docs/qc/2026-05-14/operating-spine-final-readiness/`
- HubSpot live buildout: `docs/qc/2026-05-14/hubspot-live-buildout/`
- HubSpot record-sync canary: `docs/qc/2026-05-14/hubspot-record-sync-canary/`
- HubSpot real-lead sync: `docs/qc/2026-05-14/hubspot-real-lead-sync/`
- HubSpot rich probate/heir fields: `docs/qc/2026-05-14/hubspot-rich-probate-fields/`
- HubSpot contact visibility correction: `docs/qc/2026-05-14/hubspot-contact-visibility-correction/`
- Runbooks: `docs/runbooks/agentic-company-operating-cadence.md`, `docs/runbooks/provider-sync-and-recovery.md`
- Master plan status banner: `docs/superpowers/plans/2026-05-14-hubspot-operating-spine-agentic-company-plan.md`

## Current TODO
1. Review/merge the pushed feature branch or open a PR if needed.
2. For Instantly later: let inboxes keep warming, draft/review copy first, then only test with an approved recipient/lead through gated enrollment/send.
3. Keep remaining live provider actions behind separate operator approvals and gates: HubSpot record batches, Instantly enroll/send, Vapi dispatch, source-provider pulls, Slack/provider sends.
4. Reacher SMTP egress is blocked on outbound port 25 from this Hetzner VPS; use DNS/MX-only, request Hetzner unblock, or run SMTP verifier sidecar elsewhere before relying on SMTP mailbox probes.
5. Apply current buy-box filters in future scoring/import slices: no mobile homes; SFR/1–4 preferred; commercial review only; $150k–county median core tax/title band; $500k+ creative-finance lane. Canonical note: `docs/lead-scoring/buy-box-filters.md`.
6. Capture stronger primary Alen Sultanic source material and update `docs/copywriting-wiki/`.
7. Add Mission Control read/approval endpoints/page for Ares offer/copy assets and Harris probate campaign launch review.
8. Enrich Harris probate exports with email/phone via Tracerfy only after Martin explicitly approves skiptrace spend.

## Recent Change
- 2026-05-14: Fixed HubSpot contact visibility for `lead_341` by confirming Ares custom fields were populated but standard HubSpot contact address fields were blank; Ares now maps applicant/mailing address into standard `address/city/state/zip/country`, and the existing contact/deal were updated with sync hash `hubspot-real-lead-lead_341-visible-v4`. Evidence: `docs/qc/2026-05-14/hubspot-contact-visibility-correction/`. Email/phone/mobile and property/HCAD remain true data gaps; custom Ares field card visibility still requires HubSpot UI record customization.
- 2026-05-14: Corrected the generic first real HubSpot lead sync by expanding HubSpot/Ares fields for probate/heir/contact/mailing/property/tax-overlay data, live-applying missing HubSpot properties, and updating existing `lead_341` contact `485815102172` / deal `325123310274` with applicant/heir metadata. Sync hash now `hubspot-real-lead-lead_341-rich-v3`. Property address/HCAD remain blank for this lead because current Ares data has no property match. Evidence: `docs/qc/2026-05-14/hubspot-rich-probate-fields/`. No Instantly/Reacher/Vapi/source-provider/Slack/deploy side effects.
- 2026-05-14: Ran first real HubSpot-only lead sync for hand-selected Harris probate lead `lead_341` / case `543678`; created HubSpot contact `485815102172` and deal `325123310274` with provider links `plink_3`/`plink_4`. Evidence: `docs/qc/2026-05-14/hubspot-real-lead-sync/`. No Instantly enrollment/send, Reacher call, Vapi call, source-provider pull, Slack send, batch sync, or deploy side effect.
- 2026-05-14: Reacher/SMTP egress check found outbound TCP port 25 to Gmail/Google/Outlook/Yahoo MX hosts timing out while local firewall OUTPUT is ACCEPT and control ports 443/587 connect. Evidence: `docs/qc/2026-05-14/reacher-smtp-egress/`.
- 2026-05-14: Committed/pushed operating-spine bundle as `8c19c26`; applied remote Supabase migration `20260514090000_provider_object_links.sql`; set local HubSpot default pipeline/stage env with gates off; ran one synthetic HubSpot record-sync canary creating contact `486079925950` and deal `325110558439` with provider links. Evidence: `docs/qc/2026-05-14/hubspot-record-sync-canary/`.
- 2026-05-14: Live-applied HubSpot portal customization after operator instruction. HubSpot now has Ares property groups/properties and all 12 Ares stages in the existing single `Sales Pipeline`; evidence: `docs/qc/2026-05-14/hubspot-live-buildout/`. No Instantly/Vapi/source-provider/Slack/deploy side effects.
- 2026-05-14: Added Phase 9 final QC index, final readiness artifacts, operating/provider runbooks, and living-doc updates. Final verification captured in `docs/qc/2026-05-14/operating-spine-final-readiness/test-output.txt`.
- Older Phase 1-8 details live in `memory.md` `## Change Log` and the dated QC folders.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
