# Landing → Ares intake/SMS agent QC report

## Scope

Ares backend side of the lease-options landing-page contact integration. The public form now has a first-class Ares intake contract that preserves full seller context and exposes side-effect statuses while keeping provider sends gated.

## Changes

- Expanded `POST /marketing/leads` request fields and response side-effect shape.
- Persisted seller-fit fields, consent metadata, and attribution through Ares contact records/metadata.
- Required `sms_consent` for confirmation SMS.
- Kept SMS/email/Trigger side effects skipped unless `PROVIDER_LIVE_SENDS_ENABLED=true`.
- Updated living docs: `README.md`, `CONTEXT.md`, `TODO.md`, `memory.md`.

## Verification

- `git diff --check`: passed (`diff-check.txt`).
- Focused backend suite: `51 passed` (`focused-test-output.txt`).
- Full backend suite: `636 passed` (`full-test-output.txt`).

## Remaining deployment gates

- Configure landing runtime envs before deploying the landing branch.
- Keep Ares `PROVIDER_LIVE_SENDS_ENABLED=false` until Martin explicitly approves a live SMS/email smoke with approved recipient(s).
