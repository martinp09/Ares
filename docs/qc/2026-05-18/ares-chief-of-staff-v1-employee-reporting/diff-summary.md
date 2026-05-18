# Diff Summary — Ares Chief of Staff v1 Employee Reporting

## Modified files

- `app/db/source_runs.py`
  - Prevents read-only calls against missing file-backed source-run state from creating a lock file or parent directory.

- `app/models/ares_chief_of_staff.py`
  - Promotes the brief contract to `ares_chief_of_staff_brief_v1`.
  - Adds employee/reporting identity fields.
  - Adds `worklog`, `priorities`, `blockers`, `approval_requests`, and `operational_context`.

- `app/services/ares_chief_of_staff_service.py`
  - Builds employee-style worklog/priorities/blockers/approval requests from existing queues.
  - Reads existing lead-machine health/latest morning brief through an injected reader; catches read failures and never triggers source pulls.
  - Renders Slack as a human check-in to Martin.
  - Redacts Slack text/blocks/payload to omit lead names, contact details, property addresses, case numbers, raw lead IDs, and lead-machine operator action reasons.
  - Keeps local Markdown/JSON/CSV artifacts as the detailed operator record.

- `scripts/ares_chief_of_staff_digest.py`
  - Attaches `nightly_lead_machine_service` for read-only operational context in CLI runs.

- `tests/db/test_source_runs_repository.py`
  - Verifies read-only missing source-run state does not create lock files or parent directories during dry-run context reads.

- `tests/services/test_ares_chief_of_staff_service.py`
  - Adds a fake lead-machine reader.
  - Verifies employee fields, operational context, worklog/priorities/blockers/approval requests, and no lead-level PII in Slack output/payload.

- `tests/scripts/test_ares_chief_of_staff_digest.py`
  - Updates CLI contract expectation to `ares_chief_of_staff_brief_v1`.

- `README.md`
  - Documents Chief of Staff v1 as a Slack-first read-only employee report.

- `docs/qc/2026-05-18/ares-chief-of-staff-v1-employee-reporting/`
  - Adds QC evidence for this continuation slice.
