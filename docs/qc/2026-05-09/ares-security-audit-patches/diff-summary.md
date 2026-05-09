# Diff Summary — Ares Security Audit Patches

## Secret hygiene / deployment guardrails

- `.dockerignore` — exclude env files, private keys, VCS metadata, virtualenvs, node_modules, caches, and build outputs from Docker contexts.
- `.gitignore` — broaden env-file ignore rules while keeping `.env.example` trackable.
- `.env.example` — replace reusable dummy runtime keys with placeholders and add safe-default security flags.

## Runtime/API auth

- `app/core/config.py` — remove default runtime key; add flags for docs, actor header overrides, webhook signature enforcement, and live sends.
- `app/core/dependencies.py` — remove query-param auth, fail closed when runtime key is missing, use constant-time bearer comparison, and disable actor header overrides by default.
- `app/main.py` — protect docs/OpenAPI behind runtime auth when enabled, add security headers, redact validation error inputs.
- `tests/api/test_runtime_auth.py`, `tests/api/test_runtime_config_contract.py`, `tests/api/test_security_hardening.py` — regression coverage for the new auth/security contracts.

## Provider webhook/live-send safety

- `app/providers/instantly.py` — add HMAC webhook signature verification.
- `app/api/lead_machine.py` — remove caller-supplied webhook trust fields and derive trust server-side.
- `app/services/booking_service.py` — require Cal.com secrets when signatures are required; honor live-send gate for confirmations; avoid silent exception pass.
- `app/services/inbound_sms_service.py` — require TextGrid secrets when signatures are required; dry-run sequence sends when live sends are disabled.
- `app/services/probate_write_path_service.py` — block outbound enrollment unless live sends are explicitly enabled.
- `app/services/mission_control_service.py`, `app/api/mission_control.py` — block Mission Control SMS/email test sends unless live sends are explicitly enabled; provider status reflects the gate.
- `tests/api/test_lead_machine.py`, `tests/api/test_marketing_webhooks.py`, `tests/api/test_mission_control.py`, `tests/providers/test_instantly.py`, `tests/services/test_booking_service.py`, `tests/services/test_inbound_sms_service.py`, `tests/services/test_probate_write_path_service.py` — regression coverage for fail-closed webhooks and live-send gates.

## Frontend/deploy posture

- `apps/mission-control/src/lib/api.ts` — remove browser runtime token injection.
- `apps/mission-control/vite.config.ts` — keep runtime bearer injection server-side in the dev proxy.
- `apps/mission-control/vercel.json` — add security headers and preserve SPA rewrites.
- `apps/mission-control/src/App.tsx`, `apps/mission-control/src/pages/RecordsPage.tsx`, `apps/mission-control/src/pages/PipelinePage.tsx` — repair app-level test/accessibility behavior after dependency/runtime upgrade without reintroducing browser runtime token use.

## Dependency/static scan posture

- `package.json`, `package-lock.json` — pin/override audited root Trigger SDK/cookie posture.
- `trigger/package.json`, `trigger/package-lock.json`, `trigger/src/shared/runtimeApi.ts`, `tests/api/test_trigger_contract_files.py` — keep Trigger runtime client fail-fast auth behavior and clear audit advisories.
- `apps/mission-control/package.json`, `apps/mission-control/package-lock.json` — update frontend test/build stack to audit-clean versions.
- `pyproject.toml`, `uv.lock` — update pytest to `9.0.3` for CVE-2025-71176.
- `app/db/*_supabase.py`, `app/domains/site_events/service.py`, `app/services/marketing_lead_service.py`, `app/services/booking_service.py`, `app/services/inbound_sms_service.py`, `app/services/tax_overlay_service.py` — explicitly reviewed Bandit B310 `urlopen` uses for deterministic configured endpoints.
- `app/services/run_service.py`, `app/services/ares_autonomous_operator_service.py` — use `tempfile.gettempdir()` for runtime temp roots.
