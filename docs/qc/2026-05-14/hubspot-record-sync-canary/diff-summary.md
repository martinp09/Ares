# Diff Summary

## New evidence added

- `docs/qc/2026-05-14/hubspot-record-sync-canary/REPORT.md`
- `docs/qc/2026-05-14/hubspot-record-sync-canary/test-output.txt`
- `docs/qc/2026-05-14/hubspot-record-sync-canary/diff-summary.md`

## Living docs updated

- `CONTEXT.md`
- `TODO.md`
- `README.md`
- `memory.md`
- `docs/qc/2026-05-14/README.md`
- `docs/runbooks/provider-sync-and-recovery.md`
- `docs/superpowers/plans/2026-05-14-hubspot-operating-spine-agentic-company-plan.md`

## Side effects documented

- commit/push of operating-spine bundle
- local ignored `.env` defaults updated with non-secret HubSpot pipeline/stage IDs and live gates off
- remote Supabase migration `20260514090000_provider_object_links.sql` applied
- one synthetic HubSpot contact/deal canary synced
- provider links verified in Supabase

## Excluded

- raw secrets/credentials
- unrelated tracked `docs/integrations/tracerfy-skiptrace.md`
- unrelated older untracked deployment/marketing/QC files
- any batch HubSpot sync, Instantly send/enrollment, Vapi call, source-provider pull, Slack send, or deploy
