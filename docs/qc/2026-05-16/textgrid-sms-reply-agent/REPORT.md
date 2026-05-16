# TextGrid SMS Reply Agent Task 11 QC

## Scope

Task 11 added smoke and provider activation artifacts for the TextGrid SMS reply-agent branch.

Implemented local artifacts:

- `scripts/smoke/textgrid_sms_reply_agent_smoke.py`
- `tests/scripts/test_textgrid_sms_reply_agent_smoke.py`
- `docs/runbooks/textgrid-sms-reply-agent-activation.md`
- `README.md` SMS reply-agent smoke/runbook references
- `docs/qc/2026-05-16/textgrid-sms-reply-agent/REPORT.md`

## Provider Safety

- No live Supabase mutation was performed.
- No live TextGrid send was performed.
- No provider dashboard mutation was performed.
- The smoke script only posts a signed Twilio-compatible form payload to the Ares runtime webhook and optionally calls the protected Ares processor endpoint when `--runtime-api-key` is explicitly supplied.

## Verification

Red evidence from new smoke-script test:

```text
FAILED tests/scripts/test_textgrid_sms_reply_agent_smoke.py::test_smoke_posts_signed_webhook_without_bearer_auth
AssertionError: assert '<redacted>' is False
```

Cause: the sanitizer redacted a boolean safety flag because the key included `authorization`. Fix: redact only string values for sensitive key names, preserving boolean safety evidence.

Final local command results:

```bash
uv run pytest tests/api/test_sms_agent.py tests/services/test_sms_agent_processing.py tests/services/test_sms_reply_agent_service.py tests/scripts/test_textgrid_sms_reply_agent_smoke.py -q
# 27 passed in 0.06s

uv run pytest tests/api/test_sms_agent.py tests/services/test_sms_agent_processing.py tests/services/test_sms_reply_agent_service.py -q
# 25 passed in 0.07s

uv run pytest tests/scripts/test_textgrid_sms_reply_agent_smoke.py -q
# 2 passed in 0.01s

git diff --check
# passed
```

Independent QC finding:

```text
FAIL: phone masking only redacted strings that start with `+`, so valid non-E.164 CLI values could print unredacted.
```

Fix: the smoke sanitizer now masks whole-string phone-like values with 10+ digits, including `15551234567` and `(346) 772-5914`, while preserving non-phone values such as dates and TextGrid/Twilio message SIDs.

Regression check:

```bash
uv run pytest tests/scripts/test_textgrid_sms_reply_agent_smoke.py -q
# 3 passed in 0.01s
```

Branch-tip closeout:

```bash
uv run pytest tests/api/test_sms_agent.py tests/services/test_sms_agent_service.py tests/services/test_sms_agent_processing.py tests/services/test_sms_reply_agent_service.py tests/services/test_sms_reply_agent_repository.py tests/services/test_inbound_sms_service.py tests/scripts/test_sms_agent_archive_export.py tests/scripts/test_textgrid_sms_reply_agent_smoke.py tests/db/test_sms_agent_schema.py -q
# 99 passed in 0.23s

uv run pytest -q
# 1030 passed in 9.58s

npm --prefix apps/mission-control run build
# passed

npm --prefix apps/mission-control run test -- --run
# 25 files passed, 83 tests passed

npm --prefix apps/mission-control run typecheck
# passed

npm --prefix trigger run typecheck
# passed

git diff --check
# passed
```
