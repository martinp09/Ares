# Instantly Enrollment Phase 5 Diff Summary

## Phase 5 Files Changed In This Slice

- `app/services/instantly_enrollment_service.py`
  - Added summary-only provider batch-result reporting; raw provider responses are never returned.
  - Changed missing per-lead provider IDs to `action="submitted_unlinked"` and prevented `enrolled_count` from overclaiming unlinked submissions.
  - Added `submitted_count` while keeping `enrolled_count` limited to confirmed linked/enrolled records.
  - Hardened Instantly idempotency so any existing Instantly lead provider link for the same Ares `crm_record` skips duplicate enrollment, regardless of missing/changed `sync_hash`.
  - Retained provider-link writes only when a per-lead provider ID is returned.
- `app/models/mission_control.py`
  - Added `submitted_unlinked` result action and `submitted_count` response field.
  - Added model-level provider target validation for Instantly enrollment apply (exactly one of campaign/list) and conflict validation for preview.
  - Added a 500-record request max for Instantly enrollment request payloads.
- `tests/services/test_instantly_enrollment_service.py`
  - Updated confirmed/submitted count expectations.
  - Added missing/changed `sync_hash` idempotency coverage.
  - Added raw provider echo leak coverage for email/phone/payload internals in batch summaries.
- `tests/api/test_mission_control_instantly_enrollment.py`
  - Updated response shape for `submitted_count` and sanitized batch summaries.
  - Added request validation coverage for missing/conflicting provider targets.
- `docs/qc/2026-05-14/instantly-enrollment/`
  - Updated QC report, test output, and this diff summary for the fix lane.

## Broader Active Workspace / Prior Phase 1-4 Files

These files may also appear in `git diff` because they are part of the already-active Phase 1-4 / Phase 5 workspace, but they are not fully described by this Phase 5 fix-lane artifact:

- Provider-link foundations and tests from Phase 2.
- HubSpot preview/customization/record-sync code and tests from Phases 1, 3, and 4.
- Shared Mission Control/config/test fixture updates required by those earlier phases.
- Earlier QC folders under `docs/qc/2026-05-14/`.

Reviewers should use this artifact for the Instantly enrollment fix-lane changes above, not as a complete description of all active workspace changes.

## Not Changed

- No live Instantly provider calls were exercised.
- No provider secrets were added or printed.
- No commits were made.

## Artifact Tracking

The QC directory is untracked in the active checkout; add it intentionally with the Phase 5 changes if committing later.
