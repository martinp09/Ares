# QC Report — Harris Probate Campaign Launch Slice

## Scope

Added a safe campaign-launch slice for the Harris probate hot/warm/cold campaign.

## Changes

- Added `CampaignLaunchService` to build HOT/WARM/COLD preview/export manifests from `hot_warm_ranked_enriched.csv`.
- Added Mission Control API models for campaign launch previews and approval requests.
- Added Mission Control endpoints:
  - `GET /mission-control/campaign-launches/harris-probate-hot-warm-cold`
  - `POST /mission-control/campaign-launches/harris-probate-hot-warm-cold/approval`
- Generated current campaign exports under `docs/marketing/exports/harris-probate-2026-04-30/`.
- Added campaign plan and copywriting domain-expertise plan docs.
- Added focused API tests.

## Safety

No live SMS/email/direct-mail sends are performed by this slice. All exports include `do_not_send_before_approval=true`, and the approval route only creates an approval-gated command snapshot.

## Verification

- `uv run pytest tests/api/test_mission_control_campaign_launch.py -q` — PASS, 2 tests.
- `python3 -m compileall app/services/campaign_launch_service.py app/api/mission_control.py app/models/mission_control.py` — PASS.
- `git diff --check` — PASS.

## Known follow-up

- Existing `tests/api/test_mission_control_lead_machine.py` showed environment data contamination under the current Supabase-backed/default state when run together; not caused by this slice. Focused new tests pass.
- Mission Control frontend dedicated campaign page is still the next UI polish slice; current backend/API exposes the preview and approval contract and existing Approvals view can surface the created approval.
