# Ares Security Audit Patch QC Report

Date: 2026-05-09
Branch: `hardening/ares-security-audit-patches-2026-05-09`
Repo: `martinp09/Ares`

## Scope

Patched the security-audit risk buckets that were actionable without Slack token or Vercel production promotion:

- Secret hygiene / deployment guardrails
- Runtime/API auth hardening
- Provider webhook trust and fail-closed behavior
- Provider live-send safety gates
- Frontend/deploy security posture
- Dependency advisory cleanup
- Static security scan cleanup

Slack delivery and production promotion remain intentionally deferred.

## Fixes Applied

### Secret hygiene / deployment guardrails

- Added `.dockerignore` to keep env files, private keys, `.git`, virtualenvs, `node_modules`, caches, and build outputs out of Docker contexts.
- Expanded `.gitignore` env-file coverage while preserving `.env.example`.
- Replaced reusable dummy runtime keys in `.env.example` with placeholder values.
- Documented safe defaults for runtime docs, actor header overrides, provider webhook signatures, and live provider sends.

### Runtime/API auth

- Removed default `dev-runtime-key` from `Settings`; protected routes now fail closed when `RUNTIME_API_KEY` is missing.
- Removed query-string runtime API key auth.
- Runtime auth now requires `Authorization: Bearer ...` and uses constant-time comparison.
- FastAPI docs/OpenAPI are disabled by default and protected by runtime auth when explicitly enabled.
- Added runtime security headers.
- Redacted validation-error `input`/`ctx` fields to avoid echoing submitted secrets.
- Disabled actor context header overrides by default; caller actor/org headers only apply when explicitly enabled.

### Provider webhook/live-send safety

- Added Instantly webhook HMAC verification and server-derived trust metadata.
- Removed client-supplied `trusted` / `trust_reason` from accepted Instantly webhook payloads.
- Added fail-closed provider webhook defaults via `PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true`.
- Cal.com/TextGrid require configured webhook secrets when signature enforcement is enabled.
- Added global live-send default `PROVIDER_LIVE_SENDS_ENABLED=false`.
- Gated probate outbound enrollment, lease-option sequence dispatch, booking confirmations, and Mission Control SMS/email test sends behind the live-send flag.
- Mission Control provider status now reports `can_send=false` when live sends are globally disabled even if credentials are configured.

### Frontend/deploy posture

- Removed browser-side runtime API key usage from the Mission Control API client.
- Kept local Vite dev runtime auth injection server-side via proxy headers.
- Added Vercel security headers: CSP, Referrer Policy, X-Content-Type-Options, X-Frame-Options, Permissions-Policy, and HSTS.
- Upgraded Mission Control dependencies and repaired app-level tests after the test runtime upgrade.

### Dependency/static scan cleanup

- Root, Trigger, and Mission Control npm audits now report zero vulnerabilities.
- Python dependency audit now reports zero known vulnerabilities after moving pytest to `9.0.3`.
- Bandit reports zero findings. The remaining `urlopen` calls are explicitly reviewed/suppressed as configured runtime/provider/county endpoints, and temporary runtime paths now resolve through `tempfile.gettempdir()`.

## Verification Summary

All commands passed. Captured output lives in this QC directory.

- `git diff --check` — pass
- `python -m py_compile ...` — pass
- `uv run pytest -q` — `633 passed`
- `npm --prefix trigger run typecheck` — pass
- `npm --prefix apps/mission-control run typecheck` — pass
- `npm --prefix apps/mission-control run build` — pass
- `npm --prefix apps/mission-control run test -- --run` — `72 passed`
- `npm audit --audit-level=low` — zero vulnerabilities
- `npm --prefix trigger audit --audit-level=low` — zero vulnerabilities
- `npm --prefix apps/mission-control audit --audit-level=low` — zero vulnerabilities
- `uvx pip-audit -r python-requirements.txt` — zero known vulnerabilities
- `uvx bandit -r app -f json` — zero findings

## Artifact Index

- `verification-summary.txt` — pass/fail summary for all verification commands
- `backend-pytest.txt` — full backend pytest output
- `trigger-typecheck.txt` — Trigger typecheck output
- `mission-control-typecheck.txt` — frontend typecheck output
- `mission-control-build.txt` — frontend build output
- `mission-control-tests.txt` — full Mission Control Vitest output
- `npm-audit-root.txt` — root npm audit
- `npm-audit-trigger.txt` — Trigger npm audit
- `npm-audit-mission-control.txt` — Mission Control npm audit
- `python-requirements.txt` — exported Python dependency set used by pip-audit
- `pip-audit.json` — Python dependency audit JSON
- `bandit.json` — Bandit static scan JSON
- `diff-summary.md` — changed-file summary
- `git-diff-name-status.txt` — changed-file name/status list
- `git-diff-stat.txt` — diffstat captured before commit
- `final-static-qc.md` — final independent static QC PASS summary

## Remaining Risk / Deferred Work

- Slack delivery remains deferred until `SLACK_BOT_TOKEN` and target channels are available.
- Production promotion is not part of this branch; promote only through a separate env-preserving handoff.
- Provider-specific public callback URLs should be rotated/updated externally if any deployed provider configuration still uses old query-string runtime-key callback URLs.
- The `urlopen` static-scan suppressions are reviewed but should eventually be replaced with a small shared HTTP client/allowlist helper if this runtime grows beyond the current deterministic provider endpoints.
