# Activation Readiness Handoff QC

Date: 2026-05-10
Repo: `martinp09/Ares`
Branch: `chore/activation-readiness-handoff-2026-05-09`

## Scope

After PR #7 merged, this slice did the non-credentialed work that can be finished without Slack/Vercel/provider access:

- Added a non-secret activation readiness script.
- Updated the live launch env contract in `.env.example` and docs.
- Refreshed living docs so PR #7 is no longer described as an active feature branch.
- Captured local readiness output and provider request-shape smoke evidence.

## Files Changed

- `scripts/activation_readiness.py` — checks runtime/provider/landing launch gates without printing raw secrets.
- `tests/scripts/test_activation_readiness.py` — regression tests for ready, blocked, invalid sender, sensitive query, and CLI paths.
- `.env.example` — adds appointment-reminder and Slack intake env names.
- `docs/activation-readiness-handoff.md` — operator handoff for envs, callback cleanup, and smoke sequence.
- `README.md`, `TODO.md`, `CONTEXT.md`, `memory.md` — living-doc refresh.
- `docs/qc/2026-05-10/activation-readiness-handoff/` — evidence artifacts.

## Local Readiness Verdict

`python scripts/activation_readiness.py --json` currently returns `blocked`, as expected, because this checkout/shell does not have the live provider/landing envs set and `PROVIDER_LIVE_SENDS_ENABLED=false` remains the safe default.

Known external gates remain:

- TextGrid account/config/funds.
- Valid verified `RESEND_FROM_EMAIL`.
- Slack token/channel.
- Cal booking/webhook env.
- Trigger secret.
- Landing runtime envs in hosting.
- External provider callback URLs checked for old query-string runtime keys.

## Verification

Commands captured in this folder:

```bash
uv run pytest tests/scripts/test_activation_readiness.py tests/smoke/test_full_stack_contract.py -q
uv run pytest -q
npm --prefix trigger run typecheck
python scripts/activation_readiness.py --json
python scripts/smoke_provider_readiness.py
git diff --check
```

Focused tests passed: `8 passed`.
Full backend tests passed: `653 passed`.
Trigger typecheck passed.
