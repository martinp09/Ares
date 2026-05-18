# Email verification prep — Herrington + Browne

## Summary

- Candidate emails checked: 5
- Local syntax/MX pass: 5
- Instantly preflight ok: True (status 200)
- Instantly eligible signals: 2
- Instantly holds: 2
- Instantly blocks: 1
- Existing Instantly lead matches found: 0

## Artifacts

- Campaign packet: `docs/marketing/campaigns/2026-05-18-curative-title-soft-finder-email-campaign.md`
- Instantly/local backup JSON: `docs/marketing/exports/email-marketing-herrington-browne-2026-05-18/cold-email-campaigns.json`
- Instantly/local sequence CSV: `docs/marketing/exports/email-marketing-herrington-browne-2026-05-18/sequence-import-backup.csv`
- Raw PII manifest: `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/email-launch-manifest-raw.csv`
- Raw verification evidence: `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/email-verification-raw.json`

## Safety

- No lead upload.
- No campaign activation.
- No seller email send.
- Raw emails are stored only in the raw lead-data artifact directory, not this repo QC report.

## Sanitized rows

- COS-EMAIL-1 / g***s@gmail.com / local=local_pass / instantly=verified catch_all=False / launch=verified_or_partially_verified_not_enrolled
- COS-EMAIL-1 / g***n@gmail.com / local=local_pass / instantly=verified catch_all=False / launch=verified_or_partially_verified_not_enrolled
- COS-EMAIL-2 / t***3@yahoo.com / local=local_pass / instantly=verified catch_all=True / launch=hold_identity_and_phone_dnc_review_even_if_email_valid
- COS-EMAIL-2 / p***n@yahoo.com / local=local_pass / instantly=pending catch_all=pending / launch=hold_identity_and_phone_dnc_review_even_if_email_valid
- COS-EMAIL-2 / t***e@ibm.net / local=local_pass / instantly=invalid catch_all=False / launch=hold_identity_and_phone_dnc_review_even_if_email_valid
