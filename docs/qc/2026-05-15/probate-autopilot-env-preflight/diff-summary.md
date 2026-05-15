# Diff Summary — Probate Autopilot Env Preflight

## Added

- `scripts/probate_autopilot_env_contract.py`
  - Read-only JSON preflight for production no-send probate autopilot deployment.
  - Validates durable state/artifact env vars, no-send/provider mutation gates, and live intelligence gate booleans.
  - Checks path parents/root writability without creating files or directories.
- `tests/scripts/test_probate_autopilot_env_contract.py`
  - Covers healthy preflight, missing durable paths, outbound gate blockers, invalid booleans, missing explicit live gates, strict scheduled-live mode, nonexistent path blockers, and secret-value redaction from CLI output.
- `docs/qc/2026-05-15/probate-autopilot-env-preflight/`
  - Captured focused verification and dry-run preflight output.

## Updated

- `.env.example`
  - Added probate autopilot durable runtime env examples: `LEAD_MACHINE_BUSINESS_ID`, `LEAD_MACHINE_ENVIRONMENT`, `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`, `LEAD_MACHINE_ARTIFACT_ROOT`.
- `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
  - Added preflight command and clarified schedule definitions vs deployed registrations.
  - Removed stale “this branch” wording.
- `README.md`
  - Linked the preflight command in the current operating-spine status.
- `CONTEXT.md`, `TODO.md`, `memory.md`
  - Reconciled implementation commit `9c256bf` vs handoff head `9f30d2f`.
  - Replaced stale live-source pilot wording with the production env-preflight/deploy gate.
- `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/REPORT.md`
  - Fixed wording that implied only outbound email was blocked; all provider mutations remain blocked.
- `docs/qc/2026-05-15/probate-autopilot-main-merge/REPORT.md`
  - Added supersession note so historical disabled-by-default gates do not read as current handoff.
- Obsidian PRD `/root/obsidian-vault/03-Experiments/Harris Montgomery Probate Autopilot PRD.md`
  - Marked executed phases and remaining enrichment-depth work, including case-detail/contact-context as the next major PRD gap.

## Side effects

- No production deploy/promotion.
- No live county/CAD/tax/land-record calls.
- No Instantly, email, SMS, Vapi, paid skiptrace, HubSpot, Slack, or provider mutations.
