# Diff Summary — Ares Chief of Staff v2 Manager Actions

## Modified files

- `app/models/ares_chief_of_staff.py`
  - Promotes the brief contract to `ares_chief_of_staff_brief_v2`.
  - Adds `AresChiefOfStaffActionType` and `AresChiefOfStaffActionItem`.
  - Adds `manager_action_items` to the Chief of Staff brief.

- `app/services/ares_chief_of_staff_service.py`
  - Builds stable sanitized manager action items from queue counts.
  - Adds Slack reply commands: `approve cos_action_...` and `deny cos_action_...`.
  - Renders manager actions in Markdown and Slack blocks.
  - Adds sanitized manager action payload entries.
  - Writes `manager_action_items.json` and `manager_action_items.csv` artifacts.
  - Keeps action commands informational only; no approval execution path is added.

- `tests/services/test_ares_chief_of_staff_service.py`
  - Verifies manager action item generation, approval/deny command format, artifacts, Slack block section, and Slack payload contract.

- `tests/scripts/test_ares_chief_of_staff_digest.py`
  - Updates CLI dry-run contract to v2.

- `README.md`
  - Documents Chief of Staff v2 manager action/reply-command behavior.

- `docs/qc/2026-05-18/ares-chief-of-staff-v2-manager-actions/`
  - Adds QC evidence for this continuation slice.
