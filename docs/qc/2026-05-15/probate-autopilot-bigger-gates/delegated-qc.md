# Delegated QC Summary

## First review

Verdict: FAIL

Blocker found:

- The new Trigger task for property/tax/title enrichment originally used `runWithLifecycle(..., { artifactType: "lead_machine_probate_property_tax_title_enrichment" })`.
- `runWithLifecycle` stores the full runtime response as an artifact payload.
- The enrichment response can include internal record details, so the artifact would have leaked raw identifiers/PII into run-detail surfaces.

Fix applied:

- Removed `artifactType` from `trigger/src/lead-machine/probatePropertyTaxTitleEnrichment.ts`.
- Added contract coverage in `tests/api/test_lead_machine_trigger_contract.py` proving this task does not publish a raw-response artifact.

## Re-review

Verdict: PASS

No blockers.

Confirmed:

- No raw-response artifact publication from the new Trigger enrichment task.
- Adapter preview remains default-off, approval-gated, and no-network/no-browser.
- Property/tax/title enrichment rejects live flags and stays no-send.
- Outbound enqueue requires explicit operator approval and both live gates before Instantly side effects.
- Focused tests, Trigger typecheck, and `git diff --check` passed in delegated review.
