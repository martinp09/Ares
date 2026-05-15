# 2026-05-14 QC Index — HubSpot Operating Spine / Agentic Company

## Status
- Overall: Phases 1-9 are implemented and the operating-spine bundle is pushed on commit `8c19c26`; QC artifacts are organized for review.
- Source-of-truth posture: Ares/Supabase remains canonical; HubSpot, Instantly, Vapi, and Mission Control are mirrors/execution surfaces behind deterministic Ares policy.
- Live-side-effect posture: Phases 1-9 were implemented without live provider mutations. After operator approval, live HubSpot CRM customization was executed and documented in `hubspot-live-buildout/`; then one synthetic HubSpot record-sync canary plus remote provider-links migration was executed and documented in `hubspot-record-sync-canary/`; then one real hand-selected Harris probate lead was synced to HubSpot and documented in `hubspot-real-lead-sync/`; then HubSpot rich probate/heir fields were added and the same lead was updated with applicant/heir metadata in `hubspot-rich-probate-fields/`; then contact visibility was corrected by writing standard HubSpot address fields and documenting HubSpot record-card customization in `hubspot-contact-visibility-correction/`. No live Instantly enrollments/sends, Reacher calls, Vapi calls, county/source-provider pulls, Slack sends, batch record sync, or deploys were executed.
- Repository posture: feature branch is pushed; local unrelated tracked/untracked files remain outside the pushed operating-spine/canary scope. Do not describe this state as merged, deployed, or promotable until reviewed/merged intentionally.

## Phase / slice map
- Phase 0 supporting setup — HubSpot key/CLI/MCP readiness
  - Folders: `hubspot-service-key-smoke/`, `hubspot-cli-mcp-setup/`, `hubspot-personal-key-setup/`
  - Scope: local HubSpot auth/setup evidence and read-only REST probes.
  - Latest status: supporting evidence only; no write path enabled.
  - Live-side-effect posture: read-only probes/setup, no HubSpot mutation.
  - Remaining gates: if HubSpot push/webhooks/UI extensions are required later, use proper app/private-app auth rather than Service Key alone.

- Phase 1 — HubSpot mirror preview
  - Folder: `hubspot-mirror-preview/`
  - Scope: payload-only customization/record mirror previews and sanitized HubSpot adapter errors.
  - Latest status: complete and approved.
  - Live-side-effect posture: dry-run/payload construction only; no HubSpot calls/writes.
  - Remaining gates: operator approval, global provider live gate, HubSpot live gate, token, final committed build before any real apply.

- Phase 2 — Provider object links
  - Folder: `provider-object-links/`
  - Scope: provider link index, sync cursors/runs, in-memory and Supabase adapters, migration, tests.
  - Latest status: complete and approved.
  - Live-side-effect posture: canonical/index storage only; no provider calls.
  - Remaining gates: migrate intentionally in target environment and verify rollback strategy before production use.

- Phase 3 — HubSpot customization apply
  - Folder: `hubspot-customization-apply/`
  - Scope: gated HubSpot customization apply route/service/client with retry metadata sanitation.
  - Latest status: complete and approved.
  - Live-side-effect posture: fake-client tests only; no live HubSpot customization writes.
  - Remaining gates: explicit operator approval, global provider live gate, HubSpot live gate, token, and final reviewed payload.

- Phase 4 — HubSpot CRM record sync
  - Folder: `hubspot-crm-sync/`
  - Scope: gated record apply-sync, provider-link create/update decisions, idempotent `sync_hash` skips, safe warnings/errors.
  - Latest status: complete and approved.
  - Live-side-effect posture: fake-client tests only; no live CRM writes.
  - Remaining gates: operator approval, global provider live gate, HubSpot live gate, token, production migration/state verification.

- Phase 5 — Instantly enrollment
  - Folder: `instantly-enrollment/`
  - Scope: enrollment preview/apply contracts, eligibility checks, idempotent provider links, provider-ID-only result summaries.
  - Latest status: complete and approved.
  - Live-side-effect posture: fake-client tests only; no lead enrollments/sends.
  - Remaining gates: operator approval, global provider live gate, Instantly live gate, API key, verified campaign/list targets, workspace billing readiness.

- Phase 6 — Vapi call layer
  - Folder: `vapi-call-layer/`
  - Scope: Vapi config/adapter, dry-run list/outbound routes, gated live outbound dispatch, webhook trust metadata, provider-link writes.
  - Latest status: complete and approved.
  - Live-side-effect posture: dry-run/fake-client tests only; no live calls.
  - Remaining gates: operator approval, global provider live gate, Vapi live gate, API/private key, assistant ID, phone number ID, recipient approval.

- Phase 7 — Nightly lead machine / morning brief
  - Folder: `nightly-lead-machine/`
  - Scope: source-run ledger, fixture/manifest-backed source pulls, morning brief shell, Trigger task contracts, metadata sanitation, scoped idempotency.
  - Latest status: complete and approved.
  - Live-side-effect posture: no county/source-provider/Slack/provider calls; fixtures and manifests only.
  - Remaining gates: explicit source-provider credentials/approvals, live source lane selection, Slack/webhook approval if added.

- Phase 8 — Mission Control provider ops / Hermes tool catalog
  - Folder: `mission-control-provider-ops/`
  - Scope: fixture-backed Mission Control provider ops panel, typed preview/read API client methods, Hermes safe preview/read tools and approval-required live tool names.
  - Latest status: complete and approved; frontend targeted provider ops suite passed.
  - Live-side-effect posture: preview/read/status UX only; no UI live action buttons and no live apply/enroll/dispatch path wired.
  - Remaining gates: final review of UX affordances and separate implementation/approval if operator live buttons are ever added.

- Phase 9 — Final QC/readiness/runbooks/living docs
  - Folder: `operating-spine-final-readiness/`
  - Scope: this index, final readiness report, final verification transcript, diff summary, runbooks, and living-doc status updates.
  - Latest status: complete after final verification results are captured in the folder.
  - Live-side-effect posture: docs/QC only; local tests/typechecks/build/diff-check only.
  - Remaining gates: operator commit/PR, code review, deployment decision, and explicit live-provider approvals.

- Post-Phase live HubSpot buildout — HubSpot portal customization
  - Folder: `hubspot-live-buildout/`
  - Scope: live HubSpot CRM property groups, Ares custom properties, and Ares deal-stage buildout inside the existing HubSpot deal pipeline.
  - Latest status: complete; post-apply read-only verification found contacts `12/12`, deals `20/20`, companies `4/4` Ares properties and `12/12` Ares stages present.
  - Live-side-effect posture: live HubSpot customization mutations only; no HubSpot record sync, Instantly, Vapi, source-provider, Slack, or deploy side effects.
  - Remaining gates: record sync still requires operator approval, provider live gates, provider links/idempotency review, and final committed code.

- Post-Phase HubSpot record-sync canary — one synthetic CRM record
  - Folder: `hubspot-record-sync-canary/`
  - Scope: pushed operating-spine bundle, local HubSpot default pipeline/stage env with live gates off, remote provider-links migration apply, one synthetic HubSpot contact/deal canary, HubSpot readback, provider-link verification.
  - Latest status: complete; contact `486079925950` and deal `325110558439` created and provider-linked for `hubspot_canary_20260514`.
  - Live-side-effect posture: one synthetic HubSpot contact create, one synthetic HubSpot deal create, provider-link rows in Supabase, and remote migration apply only; no real batch sync or outreach/call/source-provider/deploy side effects.
  - Remaining gates: inspect canary if desired; use preview and a narrow hand-selected real record before any broader sync.

- Post-Phase HubSpot real-lead sync — one hand-selected Harris probate lead
  - Folder: `hubspot-real-lead-sync/`
  - Scope: one `limitless/prod` Harris probate lead (`lead_341`, case `543678`) synced through the gated HubSpot record-sync service after dry-run preview.
  - Latest status: complete; contact `485815102172` and deal `325123310274` created and provider-linked (`plink_3`/`plink_4`) with sync hash `hubspot-real-lead-lead_341-v1`.
  - Live-side-effect posture: one real HubSpot contact create, one real HubSpot deal create, and two provider-link rows only; no Instantly enrollment/send, Reacher call, Vapi call, source-provider pull, Slack send, batch record sync, or deploy side effect.
  - Remaining gates: lead has no email/phone; keep `skiptrace_status=needed` and `outreach_status=not_ready`; draft/review copy before any future Instantly test using a warmed inbox.

- Post-Phase HubSpot rich probate fields — lead_341 enrichment correction
  - Folder: `hubspot-rich-probate-fields/`
  - Scope: expanded HubSpot/Ares CRM custom fields for probate/heir/contact/mailing/property/tax-overlay data; live-applied missing HubSpot properties; updated existing `lead_341` contact/deal with best applicant/heir metadata.
  - Latest status: complete; contact `485815102172` and deal `325123310274` updated through provider links `plink_3`/`plink_4` with sync hash `hubspot-real-lead-lead_341-rich-v3`.
  - Live-side-effect posture: HubSpot property creates plus two HubSpot record updates only; no new contact/deal creation, no batch sync, no Instantly/Reacher/Vapi/source-provider/Slack/deploy side effect.
  - Remaining gates: selected lead still has no matched property address/HCAD account and no email/phone; property fields now exist and read back `null` until land/tax/property matching supplies those facts.

- Post-Phase HubSpot contact visibility correction — standard address fields + UI guidance
  - Folder: `hubspot-contact-visibility-correction/`
  - Scope: root-caused why the HubSpot contact card still looked empty: Ares custom fields were populated, but standard HubSpot contact `address/city/state/zip/country` fields were null and custom fields are not automatically pinned to the visible record card.
  - Latest status: complete; existing contact/deal updated through provider links `plink_3`/`plink_4` with sync hash `hubspot-real-lead-lead_341-visible-v4`; standard contact address fields now read back as `1614 Royal Grantham Ct`, `Houston`, `TX`, `77073`, `United States`.
  - Live-side-effect posture: two HubSpot record updates only; no new contact/deal creation, no batch sync, no Instantly/Reacher/Vapi/source-provider/Slack/deploy side effect.
  - Remaining gates: email/phone/mobile and property/HCAD remain truly absent; HubSpot card visibility for Ares custom fields still requires HubSpot UI record customization.

## Phase-numbering reconciliation
- The original master plan shifted Mission Control/observability later in the sequence.
- The current chat execution labels the provider-ops/Mission Control/Hermes catalog slice as Phase 8 and the docs/QC readiness slice as Phase 9.
- This index treats artifact folders as the canonical evidence map for this working tree: `mission-control-provider-ops/` is current Phase 8, and `operating-spine-final-readiness/` is current Phase 9.

## Final ship-check gates
- Required local verification: backend pytest, Mission Control tests/typecheck/build, Trigger typecheck, `git diff --check`.
- Required process gates: no secrets in evidence; no audit/fix mutation; no live Instantly/Vapi/Reacher/source-provider/Slack calls; HubSpot portal customization, one synthetic record-sync canary, one real hand-selected HubSpot lead sync, one rich-field correction update, and one standard-address visibility correction are separately documented.
- Required before shipping: review/merge intentionally, then decide deployment and remaining live-provider enablement separately.
