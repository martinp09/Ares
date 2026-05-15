# Probate Autopilot Bigger Gates QC Report

Date: 2026-05-15
Branch: `feature/probate-autopilot-source-foundation`
Commit status at report time: pre-commit verification green; final commit/push recorded in Git history.

## Scope

Executed the next safe PRD gates after the source-provider bridge/health-panel work:

1. Source adapter dry-run preview gate for Harris/Montgomery.
2. Property/CAD + tax + land-record/title-friction enrichment execution gate using supplied local artifacts only.
3. Legacy/probate outbound enqueue hard-block before Instantly side effects.
4. Trigger/runtime contracts for the new no-send enrichment step.

## Changes made

- Added `LEAD_MACHINE_SOURCE_ADAPTER_PREVIEW_ENABLED=false` as a default-off preview gate.
- Extended the probate source-provider bridge with `mode=adapter_preview`, which:
  - requires the preview env gate;
  - requires `source_provider_approval.approved=true`;
  - stays dry-run only;
  - records `network_calls_attempted=false` and `browser_calls_attempted=false`;
  - creates placeholder source manifests for Harris/Montgomery without county network/browser calls.
- Added `ProbatePropertyTaxTitleEnrichmentService` and internal API endpoint:
  - `POST /lead-machine/internal/probate-property-tax-title-enrichment`
  - consumes only supplied keep-now rows, HCAD/CAD candidates, tax overlay snapshots, and land-record rows;
  - rejects live CAD/tax/land-record flags before work;
  - returns aggregate block counts for HubSpot/outbound approval gates;
  - keeps `no_send=true`, `provider_sends_enabled=false`, `outbound_allowed=false`.
- Added Trigger endpoint/type/task contract for property/tax/title enrichment.
- Hardened outbound enqueue:
  - `operator_approval` now exists in API/service/Trigger payloads;
  - `LeadOutboundService` and `ProbateWritePathService` require explicit operator approval plus `PROVIDER_LIVE_SENDS_ENABLED=true` and `INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=true` before provider calls;
  - write path checks approval/gates before Instantly client/API-key construction.

## Safety / side-effect posture

No live side effects were introduced or run:

- No live county scraping/browser/API calls.
- No HubSpot record batch writes.
- No Instantly enrollment/send/provider call.
- No SMS.
- No Vapi call.
- No paid skiptrace.
- No Slack/provider sends.
- No deploy.

## Redaction / public-surface review

- Source adapter preview metadata is aggregate/safe only.
- Mission Control source-run health remains aggregate-only.
- A delegated QC review initially found that the new Trigger enrichment task would have emitted full enrichment responses as lifecycle artifacts. Fixed by removing `artifactType` from `probatePropertyTaxTitleEnrichment.ts`; a contract test now asserts no raw-response artifact is published for that task.

## Verification

Captured in `test-output.txt`.

- Focused relevant backend tests: `48 passed`, then post-fix `49 passed`.
- Full backend: `807 passed`, then post-fix/final `808 passed`.
- Mission Control tests: `24 files / 79 tests passed`.
- Mission Control typecheck: pass.
- Mission Control build: pass.
- Trigger typecheck: pass.
- `git diff --check`: clean.
- Delegated QC after artifact fix: PASS / no blockers.
- Final pre-push verification repeated all core gates and stayed green; see appended output in `test-output.txt`.

## Remaining gates

Still not implemented in this slice:

- Actual Harris county live source adapter/network/browser execution.
- Actual Montgomery county live source adapter/network/browser execution.
- Live CAD/property portal calls.
- Live HCTax/Montgomery ACT calls.
- Live land-record portal/browser calls.
- HubSpot batch mirror apply for enriched records.
- Instantly enrollment/send beyond the already-gated approval path.

Those remain separate explicit approval + env-gate + QC slices.
