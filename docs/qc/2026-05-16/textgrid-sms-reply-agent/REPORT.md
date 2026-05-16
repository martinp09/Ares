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
