# Diff Summary

- Updated local `.env` `INSTANTLY_API_KEY` to the newly supplied real-account key.
- Created backup `.env.before-instantly-real-account-20260503T215318Z`.
- Added QC evidence under `docs/qc/2026-05-03/instantly-real-account-sync/`.
- Did not create provider export/readback artifacts for the new account because the safe Instantly preflight failed with `HTTP 402 Payment Required`.
- No code changes were made by the sync attempt.
