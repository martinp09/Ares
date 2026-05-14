# 2026-05-14 QC Index — HubSpot Operating Spine / Agentic Company

## Status
- Overall: Phases 1-9 are implemented in this working tree and QC artifacts are organized for final review.
- Source-of-truth posture: Ares/Supabase remains canonical; HubSpot, Instantly, Vapi, and Mission Control are mirrors/execution surfaces behind deterministic Ares policy.
- Live-side-effect posture: Phases 1-9 were implemented without live provider mutations. After the operator explicitly asked whether HubSpot itself was built out, a separate live HubSpot CRM customization buildout was executed and documented in `hubspot-live-buildout/`. No live Instantly enrollments/sends, Vapi calls, county/source-provider pulls, Slack sends, or record sync writes were executed.
- Repository posture: working tree is staged for the operating-spine commit but still has unrelated unstaged/untracked files; do not describe this state as committed, merged, deployed, or promotable until an operator commits/reviews and separately approves any remaining live gates.

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

## Phase-numbering reconciliation
- The original master plan shifted Mission Control/observability later in the sequence.
- The current chat execution labels the provider-ops/Mission Control/Hermes catalog slice as Phase 8 and the docs/QC readiness slice as Phase 9.
- This index treats artifact folders as the canonical evidence map for this working tree: `mission-control-provider-ops/` is current Phase 8, and `operating-spine-final-readiness/` is current Phase 9.

## Final ship-check gates
- Required local verification: backend pytest, Mission Control tests/typecheck/build, Trigger typecheck, `git diff --check`.
- Required process gates: no secrets in evidence; no audit/fix mutation; no live Instantly/Vapi/source-provider/Slack calls; HubSpot portal customization live buildout is separately documented in `hubspot-live-buildout/`.
- Required before shipping: stage/commit intentionally, open/review PR or equivalent, then decide deployment and remaining live-provider enablement separately.
