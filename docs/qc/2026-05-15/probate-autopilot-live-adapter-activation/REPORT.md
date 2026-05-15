# QC Report — Probate Autopilot Live Adapter Activation

- Date: 2026-05-15
- Branch: `feature/probate-autopilot-source-foundation`
- Repo: `martinp09/Ares`
- Worktree: `/opt/ares/worktrees/probate-autopilot-source-foundation`
- Status: PASS — fresh local QC passed; safe to merge; not deployed

## Scope

Implemented the no-send activation layer for the Harris + Montgomery probate autopilot PRD:

1. Real public probate source adapters for Harris Clerk WebSearch and Montgomery Odyssey.
2. Live source-provider bridge mode behind explicit source approval and disabled-by-default env gates.
3. Optional Trigger schedule live-source activation behind a separate schedule env flag.
4. Injectable live CAD/tax/land-record enrichment gates.
5. Operator runbook and living-doc updates.

## Non-goals / side-effect guardrails

No live county pull was executed. This slice did not run or add any automatic outbound path:

- No Instantly enrollment
- No email/SMS send
- No Vapi call
- No paid skiptrace
- No HubSpot batch mirror/write
- No Slack/provider notification
- No direct mail
- No deploy

## Gate decisions

### Source adapters

Live public source acquisition now requires all of:

- `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true`
- `live_source_calls=true`
- `source_provider_bridge.mode=live_source_adapters`
- `source_provider_approval.approved=true`
- `source_provider_approval.no_send=true`
- `source_provider_approval.provider_sends_enabled=false`

After live source rows are hydrated, the request is converted back to `live_source_calls=false` for the existing manifest/source-run path.

### Scheduled runs

Trigger schedules remain no-send by default. Scheduled live-source activation also requires:

- `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=true`
- backend `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true`

The schedule helper only emits no-send approval metadata when the schedule gate is enabled.

### Enrichment

Live enrichment lanes are injectable and disabled by default. They require:

- Per-lane env gate (`LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED`, `LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED`, `LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED`)
- Registered public client for the requested lane
- `enrichment_approval.approved=true`
- `enrichment_approval.no_send=true`
- `enrichment_approval.provider_sends_enabled=false`

Responses preserve `no_send=true`, `provider_sends_enabled=false`, and `outbound_allowed=false`.

## Verification commands

### Backend full suite

Command:

```bash
uv run pytest -q
```

Result:

```text
819 passed in 15.28s
```

Output: `full-backend-test-output.txt`

### Mission Control tests

Command:

```bash
npm --prefix apps/mission-control test -- --run
```

Result:

```text
24 test files passed / 79 tests passed
```

Output: `mission-control-test-output.txt`

### Mission Control typecheck

Command:

```bash
npm --prefix apps/mission-control run typecheck
```

Result: PASS

Output: `mission-control-typecheck-output.txt`

### Mission Control build

Command:

```bash
npm --prefix apps/mission-control run build
```

Result: PASS

Output: `mission-control-build-output.txt`

### Trigger typecheck

Command:

```bash
npm --prefix trigger run typecheck
```

Result: PASS

Output: `trigger-typecheck-output.txt`

### Diff whitespace check

Command:

```bash
git diff --check
```

Result: PASS

Output: `git-diff-check-output.txt`

## QC review

Delegated final QC result: PASS.

Reviewer confirmed:

- Source-provider live path requires explicit no-send/provider-disabled approval.
- Enrichment live path requires explicit no-send/provider-disabled approval.
- Parser fixtures use synthetic identifiers/names.
- Mission Control health remains aggregate-only.
- No obvious HubSpot/Instantly/SMS/Vapi/skiptrace side-effect path was introduced.

Output: `delegated-qc-summary.md`

## Notable fix during QC

An initial full backend run failed because `tests/api/test_trigger_contract_files.py` still expected the Trigger schedule source to contain literal `live_source_calls: false`. The test was updated to assert the new disabled-by-default schedule env gate and no-send approval contract. The rerun passed: `819 passed`.

A delegated pre-final review also found that live approvals accepted missing no-send/provider-send fields and that parser fixtures used real-looking IDs/names. The code/tests were hardened before final verification.

## Remaining live-activation gates

- No live county pilot should run until durable source-run state and artifact paths are configured.
- Keep schedule live activation off until one manual no-send source pull is reviewed.
- HubSpot mirror writes and outbound remain separate approval gates.
- Deploy remains a separate explicit approval gate; this slice only ships disabled-by-default code, docs, and tests.
