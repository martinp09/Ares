# Diff summary — email marketing Herrington/Browne prep

## Added

- `docs/marketing/campaigns/2026-05-18-curative-title-soft-finder-email-campaign.md`
  - Draft-only soft-finder email campaign for curative-title / ambiguous-heirship contacts.
  - Keeps copy right-person/paperwork focused and avoids ownership, authority, title, tax, legal, and offer claims.

- `docs/marketing/exports/email-marketing-herrington-browne-2026-05-18/cold-email-campaigns.json`
  - Local Instantly-style draft backup only; no provider write.

- `docs/marketing/exports/email-marketing-herrington-browne-2026-05-18/sequence-import-backup.csv`
  - Four-step active cadence backup only; no provider upload.

- `docs/qc/2026-05-18/email-marketing-herrington-browne-prep/verification-results-sanitized.json`
  - Sanitized verification summary with masked emails and hashes.

- `docs/qc/2026-05-18/email-marketing-herrington-browne-prep/REPORT.md`
  - Human-readable verification and safety summary.

- `docs/qc/2026-05-18/email-marketing-herrington-browne-prep/test-output.txt`
  - JSON/CSV validation, raw-email leak guard, and whitespace check.

## Raw local-only artifacts

Raw contact emails and provider responses are intentionally outside repo docs:

- `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/email-launch-manifest-raw.csv`
- `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/email-verification-raw.json`

## Side-effect boundary

- Instantly API read preflight and email-verification jobs were run.
- Instantly duplicate/contact-membership read probes were run.
- No Instantly campaign draft was created in provider.
- No lead was uploaded.
- No campaign was activated.
- No seller email was sent.
- No SMS/call was sent by this email-prep slice.
