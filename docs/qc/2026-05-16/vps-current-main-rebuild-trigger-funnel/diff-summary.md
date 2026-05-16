# Diff Summary

## Live infrastructure/runtime changes

- Advanced live checkout `/opt/ares/Ares` to current `origin/main` / `61f18de`.
- Backed up live `/opt/ares/Ares/.env` before appending explicit SMS reply-agent no-send defaults.
- Rebuilt/recreated Docker `ares-api` and `ares-ui` from `61f18de`.
- Enabled Tailscale Funnel public HTTPS API edge `https://ares.tail485fd9.ts.net` -> `127.0.0.1:8000`.
- Updated Trigger prod env for project `proj_puouljyhwiraonjkpiki`:
  - `RUNTIME_API_BASE_URL=https://ares.tail485fd9.ts.net`
  - `HERMES_RUNTIME_API_BASE_URL=https://ares.tail485fd9.ts.net`
  - runtime keys refreshed to match the VPS runtime key fingerprint
  - `ARES_TRIGGER_SCHEDULES_ENABLED=false`

## Repo/documentation changes

- `CONTEXT.md`: current runtime URL, VPS deployed commit, Trigger runtime target, schedule gate status, and current TODOs.
- `TODO.md`: handoff status, VPS/Funnel/Trigger state, immediate next actions.
- `memory.md`: current direction, open work, runtime architecture notes, and change log.
- `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/REPORT.md`: summary and safety boundary.
- `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/smoke-output.json`: endpoint and table smoke evidence.
- `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/infrastructure-output.txt`: Docker, Caddy, listeners, Tailscale Funnel, and Trigger env evidence with secrets redacted.
- `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/test-output.txt`: Trigger typecheck output.

## Explicit non-changes

- No Ares application source code changed in this commit.
- No Supabase migration/schema change was applied.
- No provider/outbound send gate was enabled.
- Trigger schedules were not enabled; `ARES_TRIGGER_SCHEDULES_ENABLED=false` remains explicit.
