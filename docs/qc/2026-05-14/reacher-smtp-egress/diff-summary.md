# Diff Summary

## Added

- `docs/qc/2026-05-14/reacher-smtp-egress/REPORT.md`
- `docs/qc/2026-05-14/reacher-smtp-egress/test-output.txt`
- `docs/qc/2026-05-14/reacher-smtp-egress/diff-summary.md`

## Updated

- `CONTEXT.md`
- `TODO.md`
- `memory.md`

## Finding

Outbound SMTP port `25` to public MX hosts times out while local outbound firewall is open and control ports `443`/`587` connect. This points to provider/network SMTP egress blocking, not Ares/Reacher app logic or local firewall configuration.

## Excluded

- no secrets
- no email sent
- no Reacher config changes
- no HubSpot/Instantly/Vapi/source-provider side effects
