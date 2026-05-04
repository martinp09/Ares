# Diff Summary

## Provider-side effects
- Created two Instantly campaign subsequences:
  - `7db2176c-2ce5-4633-a2e9-346fdc8fff43` — `Long Nurture | Probate | 2026-05`
  - `494fd6b6-6456-46ea-a79d-0547a172ca95` — `Long Nurture | Tax + Title Friction | 2026-05`
- Both attach to the previously created draft parent campaigns.
- Both trigger on `lead_activity: [91]` / campaign completed without reply.
- No leads uploaded, no activation, no sends triggered.

## Code changes
- `app/providers/instantly.py`
  - Added subsequence methods: `create_subsequence`, `list_subsequences`, `get_subsequence`, `pause_subsequence`, `resume_subsequence`.
- `tests/providers/test_instantly.py`
  - Added subsequence request-construction coverage.

## Repo artifacts added
- `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-nurture-subsequence-create-payloads-2026-05-02.json`
- `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-nurture-subsequence-upload-results-2026-05-02.json`
- `docs/marketing/exports/instantly-campaign-backups-2026-05-02/instantly-nurture-subsequence-readback-2026-05-02.json`
- `docs/qc/2026-05-02/instantly-campaign-nurture-upload/`

## Living docs
- `CONTEXT.md`, `TODO.md`, and `memory.md` updated to reflect the nurture upload.
