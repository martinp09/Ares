# Secret Hygiene Scan — 2026-05-04

## Scope

Repo: `/opt/ares/Ares`
Branch: `feature/copywriting-brain-offer-engine`
Remote: `martinp09/Ares`

Reviewed:
- untracked deployment files: `Dockerfile.api`, `Dockerfile.ui`, `deploy/nginx.conf`
- ignored/local env files: `.env`, `.env.before-*`
- tracked repo files and docs for env-style assignments and high-confidence token patterns
- git history for high-confidence token patterns

## Findings

### Untracked deployment files

No secrets found in:
- `Dockerfile.api`
- `Dockerfile.ui`
- `deploy/nginx.conf`

Notes:
- `Dockerfile.api` copies only `pyproject.toml`, `README.md`, and `app/` into the API image.
- `Dockerfile.ui` copies Mission Control package files/source and `deploy/nginx.conf`; it does not copy `.env` files.
- `deploy/nginx.conf` is a static SPA fallback config only.

### Real local secrets exist outside git

The local `.env` and `.env.before-*` backup files contain live-looking provider/runtime credentials. They are intentionally not committed.

Detected secret categories include:
- Firecrawl
- N8N
- Supabase service/direct/secret keys
- Resend
- Twilio/TextGrid
- OpenAI
- Cloudflare
- Trigger.dev
- Instantly
- Ares/Hermes runtime API keys

### Git ignore/build-context risk

Before this patch, `.gitignore` ignored `.env` and `.env.local`, but not `.env.before-*` backups. Also no `.dockerignore` existed, so a Docker build context could include local env/backup files even if they were not copied into the image.

Patched:
- `.gitignore` now ignores `.env.*` while keeping `!.env.example` trackable.
- Added `.dockerignore` to keep local env files, keys, build outputs, node modules, venvs, and git metadata out of Docker build context.

### Tracked repo scan

Current tracked scan did not find high-confidence GitHub/OpenAI/Anthropic/Supabase JWT-style provider tokens in tracked files.

Found and sanitized tracked sample values:
- `.env.example` runtime API example keys were blanked.
- README/runbook/plan hard-coded `dev-runtime-key` examples were replaced with placeholders.
- One old plan `DATABASE_URL` example was replaced with `<postgres-connection-string>`.

Remaining tracked scanner warnings appear to be evidence/status fields, not raw secret values:
- `docs/rollout-evidence/preview-2026-04-25.json`: `*_key_present` fields
- `docs/rollout-evidence/production-2026-04-25.json`: `*_key_present` fields

### Git history scan

A high-confidence token-pattern scan across reachable git history returned zero matches for:
- GitHub PAT prefixes
- OpenAI/Anthropic key prefixes
- JWT-style Supabase service-role tokens
- obvious env assignment values for common live provider keys

## Recommendations

1. Keep `.env` and `.env.before-*` local/private only.
2. Move env backups out of the repo directory or delete stale backups after confirming the current `.env` is the only needed runtime file.
3. Rotate any credential that may have been copied into chat/tool logs or shared outside this VPS.
4. Commit `.gitignore`, `.dockerignore`, and doc/env-example sanitization as a dedicated secret-hygiene patch.
5. Treat `Dockerfile.api`, `Dockerfile.ui`, and `deploy/nginx.conf` as clean from a secrets perspective, but commit them only as a separate deployment/containerization slice if they are still wanted.
