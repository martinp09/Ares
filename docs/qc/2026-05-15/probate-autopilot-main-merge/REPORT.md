# QC Report — Probate Autopilot Main Merge

- Date: 2026-05-15
- Branch: `main`
- Repo: `martinp09/Ares`
- Worktree: `/opt/ares/worktrees/ares-main`
- Status: PASS locally after merge-conflict resolution; not deployed
- Superseded by: live operational no-send execution evidence in `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/` and env preflight evidence in `docs/qc/2026-05-15/probate-autopilot-env-preflight/`

## Scope

Merged `feature/probate-autopilot-source-foundation` into `main` and resolved conflicts between the current HubSpot/provider operating-spine work and the probate-autopilot source-foundation/live-adapter activation slice.

## Key merge decisions

- Kept the newer no-send probate source/provider and enrichment gates.
- Kept HubSpot CRM token aliases/live-write gates from `main` and added Instantly enrollment/Tracerfy/probate live-source settings from the feature branch.
- Preserved safe test defaults with provider live sends off by default; updated tests that intentionally exercise live provider acceptance to opt in explicitly.
- Removed the duplicate mounted `voice_agents` API router so `/voice/*` resolves to the newer `VapiCallService` contract instead of two conflicting route models.
- Kept provider actions gated/off by default: no Instantly, no SMS/email send, no Vapi call, no HubSpot batch write, no paid skiptrace, no live county pull, and no deploy.

## Verification commands

### Python syntax smoke

```bash
python -m py_compile app/api/lead_machine.py app/core/config.py app/main.py app/services/probate_write_path_service.py tests/api/test_trigger_contract_files.py tests/conftest.py tests/providers/test_hubspot.py tests/providers/test_vapi.py
```

Result: PASS

Output: `py-compile-output.txt`

### Backend full suite

```bash
uv run pytest -q
```

Result:

```text
897 passed in 19.83s
```

Output: `full-backend-test-output.txt`

### Mission Control tests

```bash
npm --prefix apps/mission-control test -- --run
```

Result:

```text
24 test files passed / 79 tests passed
```

Output: `mission-control-test-output.txt`

### Mission Control typecheck

```bash
npm --prefix apps/mission-control run typecheck
```

Result: PASS

Output: `mission-control-typecheck-output.txt`

### Mission Control build

```bash
npm --prefix apps/mission-control run build
```

Result: PASS

Output: `mission-control-build-output.txt`

### Trigger typecheck

```bash
npm --prefix trigger run typecheck
```

Result: PASS

Output: `trigger-typecheck-output.txt`

### Diff checks

```bash
git diff --check
git diff --cached --check
```

Result: PASS after normalizing one trailing-whitespace line inherited from a staged copywriting raw note.

Outputs:

- `git-diff-check-output.txt`
- `git-cached-diff-check-output.txt`

## Remaining live gates

These were the gates at the time of this historical main-merge QC. Current handoff is superseded by `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/` and `docs/qc/2026-05-15/probate-autopilot-env-preflight/`.

- Manual live no-send Harris/Montgomery source pull is complete and healthy in the superseding QC evidence.
- Before production deployment, run the env preflight and configure durable source-run/artifact paths.
- Keep HubSpot batches, Instantly enrollment/send, SMS/Vapi, paid skiptrace, Slack/provider notifications, and deploy as separate explicit approval gates.
