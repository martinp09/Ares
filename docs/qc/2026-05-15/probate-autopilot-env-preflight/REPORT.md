# QC Report — Probate Autopilot Env Preflight

- Date UTC: 2026-05-15
- Repo: `martinp09/Ares`
- Worktree: `/opt/ares/worktrees/ares-main`
- Branch: `fix/probate-autopilot-env-preflight`
- Scope: no-send production deployment preflight + stale handoff cleanup
- Superseded by: `docs/qc/2026-05-15/probate-case-detail-enrichment/` for case-detail live gate additions

## Scope

After the live no-send PRD execution, the next operational gate was durable runtime configuration before any production no-send deployment. This slice adds a read-only preflight command so the operator can verify the environment without triggering county source calls, provider sends, provider writes, or file creation.

## What changed

- Added `scripts/probate_autopilot_env_contract.py`.
- Added `tests/scripts/test_probate_autopilot_env_contract.py`.
- Added durable probate env examples to `.env.example`.
- Updated the no-send activation runbook with the preflight command.
- Reconciled stale handoff wording in `CONTEXT.md`, `TODO.md`, `memory.md`, `README.md`, and the prior live-operational/main-merge QC reports.
- Updated the Obsidian PRD rollout section to distinguish completed no-send phases from remaining enrichment-depth follow-ups.

## Preflight contract

The command:

```bash
uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live
```

checks:

- required durable runtime vars:
  - `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`
  - `LEAD_MACHINE_ARTIFACT_ROOT`
  - `LEAD_MACHINE_BUSINESS_ID`
  - `LEAD_MACHINE_ENVIRONMENT`
- no-send/provider mutation gates:
  - `PROVIDER_LIVE_SENDS_ENABLED=false`
  - `INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=false`
  - `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`
  - `VAPI_PROVIDER_LIVE_SENDS_ENABLED=false`
- live intelligence gates are explicit booleans, including the later-added case-detail gates:
  - `LEAD_MACHINE_LIVE_CASE_DETAIL_CALLS_ENABLED`
  - `LEAD_MACHINE_SCHEDULED_LIVE_CASE_DETAIL_CALLS_ENABLED`
- scheduled live source/case-detail/enrichment gates are enabled when `--require-scheduled-live` is used.
- state path parent and artifact root exist and are writable.

The script intentionally does not create files/directories and does not call external sources/providers.

## Verification

Captured outputs:

- `test-output.txt`
- `env-contract-output.json`
- `diff-summary.md`
- `git-diff-check-output.txt`
- `git-cached-diff-check-output.txt`

Passed checks:

```bash
python -m py_compile scripts/probate_autopilot_env_contract.py
uv run pytest tests/scripts/test_probate_autopilot_env_contract.py tests/scripts/test_probate_autopilot_doctor.py tests/api/test_trigger_contract_files.py -q
uv run pytest -q
npm --prefix trigger run typecheck
```

Results:

- Focused contracts: `18 passed`.
- Full backend: `910 passed`.
- Trigger typecheck: passed.

Dry-run preflight output reported:

- `status=healthy`
- `no_send_ok=true`
- `live_intelligence_ready=true`
- `blockers=[]`
- `warnings=[]`
- `created_files_or_directories=false`
- `live_source_calls=false`
- `provider_mutations=false`

## Side-effect audit

Executed:

- Local file edits and QC artifact writes.
- Local temp-directory path checks only.

Not executed:

- no production deploy/promotion;
- no live county/CAD/tax/land-record HTTP calls;
- no Instantly enrollment;
- no email sends;
- no SMS sends;
- no Vapi calls;
- no paid skiptrace;
- no HubSpot batch mirror writes;
- no Slack/provider sends.

## Remaining work

- Run the preflight against the real production env file before a deployment/promotion.
- Configure durable state/artifact directories in the deployment target.
- Case-detail party/event/doc/contact-candidate enrichment was implemented in the follow-up QC slice; next data-quality work is measuring property-match lift from that context while provider/send gates stay blocked.
