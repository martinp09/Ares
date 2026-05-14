# Provider Sync and Recovery Runbook

## Core rule
Ares is canonical. Providers execute or mirror state only after Ares policy, idempotency, provider links, and operator approvals are satisfied.

## Provider gates and envs
- Global live-provider gate must be enabled before any provider mutation.
- Provider-specific live gate must also be enabled:
  - HubSpot live writes for customization/CRM sync.
  - Instantly live enrollment/sends.
  - Vapi live outbound dispatch.
- Required credentials must exist in environment variables, but must never be printed into logs, QC files, chat, or reports.
- Operator approval is separate from env configuration; both are required for live side effects.

## Current HubSpot portal state
- HubSpot CRM customization was live-applied on 2026-05-14 after operator instruction; evidence: `docs/qc/2026-05-14/hubspot-live-buildout/`.
- Ares property groups/properties are present on contacts, deals, and companies.
- The portal allows only one deal pipeline, so Ares stages were added to the existing `Sales Pipeline` / `default` pipeline.
- HubSpot CRM record sync is still a separate live action and must use preview, provider-link/idempotency review, and operator approval before any record write.

## Preview before apply
1. Run preview/dry-run endpoint or Hermes safe preview tool.
2. Inspect target records, provider object decisions, warnings, and idempotency keys.
3. Confirm provider links for existing external IDs before any update path.
4. Confirm all live gates and approvals.
5. Apply only the reviewed scope; do not broaden scope during recovery.

## Idempotency and provider links
- Use provider links as the source for external object identity.
- Use sync hashes/idempotency keys to avoid duplicate writes/enrollments/calls.
- Treat missing provider links as create candidates only after preview confirms the target provider/object type.
- Treat existing provider links as update/skip candidates depending on canonical state and sync hash.

## Failure triage
- Classify the failure:
  - Configuration: missing gate, missing credential, wrong provider target.
  - Validation: unsupported fields, invalid record status, unverified contact details.
  - Transport: timeout, rate limit, retry-after, provider outage.
  - Provider response: rejected payload, duplicate external object, billing/workspace restriction.
  - Canonical state: stale record, missing link, conflicting idempotency key.
- Keep provider errors sanitized. Preserve safe status/category/retry metadata, not raw auth headers or secret-bearing messages.
- Use fake-client/local tests for code fixes before retrying any provider action.

## Recovery patterns
- Preview recovery scope first; do not retry a broad batch blindly.
- For partial HubSpot syncs, compare provider links and sync hashes, then retry only failed or stale records.
- For Instantly enrollments, use existing-link and eligibility checks to avoid duplicate lead enrollment.
- For Vapi, never redial by replaying an ambiguous failed request; confirm recipient and call intent before dispatch.
- For source runs, preserve lane/run artifacts and rerun with the same manifest when reproducing.

## Rollback / abort notes
- If a live apply has not started, abort by leaving gates disabled and closing the approval.
- If a provider mutation partially completed, Ares remains canonical; record provider IDs and reconcile forward rather than deleting provider data blindly.
- If a batch is stale or ambiguous, stop further provider actions and create manual-review tasks.
- Deployment rollback is separate from provider-state rollback; do not assume code rollback undoes external provider mutations.

## Never-print-secrets rule
- Never print tokens, API keys, private keys, webhook secrets, auth headers, signed callback secrets, or full env dumps.
- Redact secret-bearing URLs and headers before adding evidence.
- If a secret appears in logs or docs, stop and rotate it before continuing operational use.
