# Diff Summary

This summary covers the tracked modifications and untracked new Phase 1 files because a plain `git diff` only shows tracked-file edits and omits newly added untracked files in this working tree.

## Runtime

- `.env.example`
  - Restored local-safe runtime API key defaults for `HERMES_RUNTIME_API_KEY` and `RUNTIME_API_KEY` to match the runtime config contract (`dev-runtime-key`).
- `app/providers/hubspot.py`
  - Added sanitized transport message construction with bounded provider/method/path/status details.
  - Wrapped non-`ProviderTransportError` exceptions without including `str(exc)`, preventing accidental token/header/body leaks.
  - Sanitizes `ProviderTransportError.headers` before re-raise and before attaching headers from default `HTTPError` handling.
  - Drops sensitive/raw provider or proxy headers (`Authorization`, cookies, content headers, bearer/token-like names or values) while preserving safe retry metadata (`Retry-After`, `X-RateLimit-*`).
  - Re-wraps injected `ProviderTransportError` instances with sanitized message/status/headers instead of trusting caller-provided metadata.
  - Changed default `HTTPError` handling to avoid surfacing raw HubSpot response bodies while preserving status code and safe retry headers.
- `app/services/hubspot_mirror_service.py`
  - Preserves valid `lead_score=0` via explicit `None` fallback logic to `data_quality_score`.
  - Rejects `dry_run=false` after live-write/token preflight with a clear Phase 1 live-apply-not-implemented error.
  - Keeps preview responses at `would_call_provider=false`; no provider call is made.

## Tests

- `tests/providers/test_hubspot.py`
  - Added assertions that access tokens, Authorization headers, bearer values, raw provider bodies, cookies, and unsafe response headers are absent from raised provider error messages/metadata.
  - Covers injected sender exception wrapping, default `HTTPError` handling, injected `ProviderTransportError` sanitization, and retry behavior with sanitized `Retry-After` metadata.
- `tests/services/test_hubspot_mirror_service.py`
  - Added `lead_score=0` preservation coverage.
  - Added `dry_run=false` live-apply rejection coverage after gate/token checks with no provider call.
- `tests/api/test_hubspot_mirror.py`
  - Added API coverage for `dry_run=false` live-apply rejection after gate/token checks.

## Docs/QC

- `docs/qc/2026-05-14/hubspot-mirror-preview/test-output.txt`
  - Updated captured pytest output for the runtime config contract check (`1 passed`), focused final security-pass suite (`19 passed`), and full backend suite (`639 passed`).
- `docs/qc/2026-05-14/hubspot-mirror-preview/REPORT.md`
  - Updated summary, safety notes, results, and follow-up notes for the final provider-header security pass; replaced the stale broader-suite claim with captured current results.
- `docs/qc/2026-05-14/hubspot-mirror-preview/diff-summary.md`
  - This file.
