# Agentic Company Operating Cadence Runbook

## Purpose
Run Ares as the deterministic operating spine while Hermes supervises decisions, approvals, and operator communication. Ares remains canonical; HubSpot, Instantly, Vapi, and Mission Control are operator/provider surfaces.

## Daily cadence
1. Morning brief review
   - Open Mission Control and review the latest source-run / morning-brief summary.
   - Confirm warnings, counts, stale fixtures, and any manual-review tasks before approving outreach or calls.
   - Treat the brief as decision support, not proof that providers were mutated.

2. Source runs
   - Start with fixture/manifest-backed source runs for QA.
   - Before live source pulls, verify source lane, county scope, credentials, cost/spend impact, and operator approval.
   - Keep source lanes separate from strategy lanes: probate, tax/title friction, bankruptcy/PACER, and other lanes should not collapse into one undifferentiated list.

3. HubSpot mirror preview / customization state
   - HubSpot portal customization has already been live-applied once for Ares custom properties and stages; evidence: `docs/qc/2026-05-14/hubspot-live-buildout/`.
   - The portal is limited to one deal pipeline, so Ares stages live in the existing HubSpot `Sales Pipeline` rather than a separate `Ares Acquisitions` pipeline.
   - Use HubSpot preview endpoints first to inspect any future customization or CRM record payloads.
   - Confirm Ares canonical fields, provider links, idempotency/sync hashes, and expected create/update decisions.
   - Only consider HubSpot record sync after explicit operator approval and provider live gates are enabled.

4. Instantly enrollment preview/apply approval flow
   - Run enrollment preview against explicit record IDs and campaign/list targets.
   - Check verification/status eligibility, existing provider links, duplicate/idempotent rows, and summary counts.
   - Do not enroll leads or send email until the operator approves the exact target set and the Instantly live gate/API key/workspace billing state are verified.

5. Vapi call dry-run/dispatch approval flow
   - Use dry-run outbound call preview first; verify recipient, assistant ID, phone number ID, and expected metadata.
   - Live dispatch requires operator approval, global provider live gate, Vapi live gate, credentials, assistant, phone number, and approved recipient scope.
   - Never treat a dry-run as a completed provider call.

6. Hermes tool catalog usage
   - Prefer safe `read`/`preview` tools for autonomous inspection.
   - Treat `apply`, `enroll`, `send`, `dispatch`, and other live-provider tools as approval-required.
   - Hermes is the control shell; Ares typed APIs enforce policy and state.

7. QC evidence cadence
   - Capture command, exact output, scope, and no-live posture in `docs/qc/<date>/<slice>/`.
   - Add `REPORT.md`, `test-output.txt`, and `diff-summary.md` for meaningful slices.
   - Keep evidence free of secrets, raw provider tokens, and unnecessary PII.

## Weekly cadence
- Review QC index and living docs for drift.
- Re-run full verification before PR/merge/deploy decisions.
- Review provider link health, sync run failures, and stale cursors.
- Audit pending approvals and abort stale/ambiguous live actions.
- Confirm environment gates are still disabled unless a live rollout is intentionally scheduled.
- Update runbooks when an operator action changes from preview-only to live-approved.

## Operator approval checklist
- What exact records, campaigns, calls, or provider objects are in scope?
- Is Ares canonical state current and backed by provider links/idempotency keys?
- Is the action previewed and reviewed?
- Are all live gates and credentials intentionally configured?
- Is rollback/abort behavior understood?
- Is evidence captured without secrets?
