# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/root/Ares-inspect`
- Active branch after ship: `main`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Security-audit hardening is complete and ready to operate from `main` after the merge of `hardening/ares-security-audit-patches-2026-05-09`.
- QC evidence: `docs/qc/2026-05-09/ares-security-audit-patches/`.
- Patched: secret/build-context hygiene, runtime auth fail-closed behavior, docs/auth/security headers, server-derived provider webhook trust, Cal/TextGrid/Instantly signature enforcement, global provider live-send gate, Mission Control no-browser-token behavior, Node/Python advisory cleanup, and Bandit static-scan cleanup.
- Verification passed: `git diff --check`, py compile, `uv run pytest -q` (`633 passed`), Trigger typecheck, Mission Control typecheck/build/full tests (`72 passed`), root/Trigger/Mission Control npm audits, pip-audit, and Bandit.
- Harris daily lead-machine foundation remains merged to `main` via PR #5; Slack and production promotion are still separate follow-ups.
- Production wiring is live and must remain untouched unless explicitly requested.

## Current TODO
1. Wire/test real Slack digest delivery only after Slack bot token + target channels are available.
2. Run a dedicated production promotion only when intentionally preserving/updating the production runtime/provider env contract.
3. Update provider callback configurations externally if any deployed provider still references old query-string runtime-key callback URLs.
4. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

## Recent Change
- 2026-05-09: Completed security-audit hardening patch set and QC at `docs/qc/2026-05-09/ares-security-audit-patches/`.
- 2026-05-09: Merged Harris daily probate + HCAD `Estate Of` import foundation to `main` via PR #5; Vercel preview smoke passed and Slack remains intentionally last.
- 2026-04-30: Added Harris probate campaign launch backend slice and QC at `docs/qc/2026-04-30/harris-probate-campaign-launch/`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
