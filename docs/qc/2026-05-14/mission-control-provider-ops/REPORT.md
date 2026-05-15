# Mission Control Provider Ops Phase 8 QC

## Scope
- Added no-live Mission Control provider ops API client methods and fixture-backed Dashboard panel.
- Added Hermes tool catalog entries for provider preview/read commands and approval-gated live/apply command names.
- Preserved Phase 8 safety boundary: preview/read/status only; no UI live/apply/dispatch/send/enroll/call controls.

## Fixer pass (2026-05-14)
- Restored App default workspace to Lead Machine / Agents so existing agents-first org/scope behavior remains intact.
- Scoped brittle Dashboard/App test assertions that collided with ProviderOperationsPanel numeric/status text.
- Fixed full-fixture status accounting after the added suppression view.
- Fixed provider ops API test fetch mock typing for frontend typecheck.

## Phase 8 fix lane (2026-05-14)
- Tightened Mission Control frontend provider preview request types to match backend contracts.
- HubSpot customization preview examples now send only `{ dry_run }`.
- HubSpot record sync preview remains scoped to `{ records }` because the backend preview model supports `dry_run` and `records`, not `business_id`/`environment`.
- Instantly enrollment preview examples now send only backend-supported enrollment preview fields (`records`, optional provider/campaign target fields, `allow_unverified`) and no `business_id`/`environment`.
- API tests assert preview example bodies do not include invalid scope fields.
- Vapi outbound preview still forces `dry_run: true`, overriding caller input.

## Dependency note
- Frontend dependencies were installed with `npm --prefix apps/mission-control install --ignore-scripts`; frontend tests/typecheck/build now run against installed deps.
- No `npm audit` or `npm audit fix` was run in this fix lane.

## Commands
- `npm --prefix apps/mission-control test -- --run src/pages/DashboardPage.test.tsx src/App.test.tsx` — passed in prior fixer evidence, `26 passed`.
- `npm --prefix apps/mission-control test -- --run src/lib/api.test.ts src/components/ProviderOperationsPanel.test.tsx src/pages/DashboardPage.test.tsx src/App.test.tsx` — passed, `39 passed`.
- `npm --prefix apps/mission-control run typecheck` — passed.
- `npm --prefix apps/mission-control run build` — passed.
- `python -m pytest tests/api/test_hermes_tools.py tests/api/test_nightly_lead_machine.py tests/api/test_voice.py -q` — passed, `30 passed in 1.31s`.
- `python -m pytest -q` — passed, `756 passed in 26.25s`.
- `git diff --check` — passed with empty stdout; raw result captured in `test-output.txt`.

## No-live assertions
- API client uses only preview/read endpoints for provider ops.
- API client tests assert paths do not include `/apply`, `/apply-sync`, `/enrollments/apply`, or `dry_run=false`.
- API client tests assert HubSpot customization and Instantly enrollment preview example bodies do not include invalid `business_id`/`environment` fields.
- Vapi outbound preview method overwrites caller input with `dry_run: true`.
- ProviderOperationsPanel renders no buttons and no live action affordances.
- Hermes preview/read tool names are advertised as `safe_autonomous`; live/apply names are advertised as `approval_required` and are not auto-executable.
