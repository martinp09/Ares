# Diff Summary

## `scripts/activation_readiness.py`

- Added dotenv-style `--env-file` loading for one or more external env files.
- Added `--runtime-url` and `--derive-local-defaults` to fill safe derived activation values:
  - TextGrid status callback URL
  - landing marketing/site-event URLs
  - landing API key from `RUNTIME_API_KEY`
  - default business id/environment
  - Trigger task defaults
  - `CAL_BOOKING_URL` from existing local scheduling env names when present
- Keeps raw secret values out of output by continuing to use fingerprints and sanitized URLs.

## `tests/scripts/test_activation_readiness.py`

- Added regression coverage proving the CLI can load an env file, derive defaults, avoid raw-secret output, and still report unresolved blockers.

## Docs / Living State

- `README.md`: documents the env-file activation command.
- `docs/activation-readiness-handoff.md`: adds the exact env-file readiness command and updated blocker interpretation.
- `CONTEXT.md`: updates current branch/scope and latest remaining gates.
- `TODO.md`: records this readiness pass, local dark smoke result, and remaining external gates.
- `memory.md`: records a concise durable changelog entry.

## QC Artifacts

- `REPORT.md`
- `activation-readiness-envfile-output.json`
- `local-dark-intake-smoke-output.json`
- `hosted-authenticated-dark-smoke-output.json`
- `provider-shape-output.json`
- `vercel-auth-check.txt`
- `trigger-auth-check.txt`
- `test-output.txt`
- `full-test-output.txt`
