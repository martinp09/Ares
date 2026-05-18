# Owned-Number Smoke Notes

Local-only run artifacts live outside the repo at:

```text
/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/
```

## Root-cause finding

The initial no-reply symptom was caused by the temporary smoke watcher not seeing inbound replies through the provider-filtered TextGrid list query. A manual recovery SMS sent through Ares/TextGrid reached final provider status `delivered`, and unfiltered recent-message polling showed the inbound replies were present.

## Fix applied outside repo

The temporary watcher now:

- polls TextGrid recent messages unfiltered;
- filters locally to Martin's owned number and the Ares sender number;
- preserves previously processed inbound message IDs across restarts;
- remains bounded by max turns and expiry;
- uses Hermes-assisted natural copy for the smoke only;
- keeps global Ares auto-replies disabled.

## Current boundary

This smoke is not production seller automation. It is only an owned-number test harness while the repo implementation is being prepared behind disabled-by-default runtime gates.
