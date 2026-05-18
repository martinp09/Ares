# Ares Mission Control Record Segmentation QC

Date: 2026-05-18
Branch: `feature/ares-chief-of-staff-v0`
Worktree: `/opt/ares/worktrees/ares-chief-of-staff-v0`

## Scope

Martin asked for Mission Control to feel more segmented and operator-useful:

- More left-rail tabs/sections instead of a thin dashboard.
- Visible `Records`, `Property Cards`, and `Owner Cards` surfaces.
- Deeper property/owner record detail cards.
- Remove the generic `Organization scope` wording.
- Use browser-harness/browser QA to click around and find broken or weak flows.

This slice keeps seller/outbound/provider behavior unchanged. It adds no new live sends or provider mutations; the pre-existing record command buttons remain gated through existing CRM command callbacks and disabled states.

## Changes

- Reworked the left rail into real-estate operator sections:
  - `Work today`: Today Desk, Hot Leads, Replies, To-Do, Approvals, Blocked / Dead.
  - `Records`: Records, Property Cards, Owner Cards, Skip Trace, Tax / Title.
  - Pipeline workspace includes Deal Board, Fire List, Records, Property Cards, Owner Cards, Title / Curative, Skip Trace.
- Replaced `Organization scope` with `Operator scope` / operating-lane filters:
  - portfolio switcher
  - deal lane filter
  - runtime lane filter
- Added richer Records modes in `RecordsPage`:
  - inventory
  - hot leads
  - property cards
  - owner cards
  - skip trace
  - tax/title
- Added an always-visible record detail card for the selected row:
  - property/address/mailing detail
  - owner/assignment detail
  - contact readiness
  - pipeline movement
  - record/source/lifecycle metadata
  - missing-before-contact checklist
  - explicit no-send safety gate copy
- Added responsive styles for the record workbench and detail card.
- Added frontend API request timeout support so unavailable local runtime routes fall back to fixture mode instead of leaving the browser stuck in a refresh state during local QA. The timeout is configurable with `VITE_RUNTIME_REQUEST_TIMEOUT_MS` and defaults to `8000` ms.
- Expanded tests for:
  - visible left-rail segmentation
  - absence of `Organization scope`
  - `Operator scope` replacement
  - record detail cards
  - segmented record modes
  - no out-of-view detail card when a saved view has zero matching rows

## Browser QA findings

Browser-harness and the built-in browser were used against the local Vite app at `http://127.0.0.1:5178`.

Captured artifact:

- `browser-harness-click-sweep.json`
- `browser-harness-validate.txt`

Sweep summary:

- States captured: `16`
- Clicks attempted: `15`
- Failed clicks: `0`
- `Organization scope` seen: `false`
- `Operator scope` seen: `true` in all captured states
- Console exceptions: `0`
- Local fixture-fallback network errors: `4`, limited to expected dev-server `/deals` and `/deals/fire-list` 404s also noted under remaining gates.
- Record-card/detail states appeared on:
  - Hot Leads
  - Records
  - Property Cards
  - Owner Cards
  - Skip Trace
  - Tax / Title
  - Pipeline Property Cards
  - Pipeline Owner Cards
  - Pipeline Title / Curative
  - Pipeline Skip Trace

The click sweep covered:

- Lead Machine Today Desk / Hot Leads / Records / Property Cards / Owner Cards / Skip Trace / Tax / Title / Source Health
- Pipeline / Deal Board / Property Cards / Owner Cards / Title / Curative / Skip Trace / Fire List
- Marketing / Submissions

Built-in browser visual smoke captured:

- `records-page-smoke.png`

Visual smoke verified:

- richer segmented left rail
- `Operator scope` in the header
- no visible `Organization scope`
- Records page with record cards and a right-side detail panel
- no CAPTCHA or verification challenge

Console smoke:

- `browser-console.txt`
- Result: `0` console messages, `0` JavaScript errors after the record page smoke.

## Verification commands

```bash
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control test -- --run
npm --prefix apps/mission-control run build
git diff --check
```

Results:

- Typecheck: passed.
- Mission Control test suite: `25` files passed / `85` tests passed.
- Vite production build: passed.
- `git diff --check`: passed.

Captured artifacts:

- `typecheck-output.txt`
- `test-output.txt`
- `build-output.txt`
- `git-diff-check.txt`
- `diff-summary.md`

## Safety / side effects

No live operational side effects were performed:

- No seller outreach.
- No paid skiptrace.
- No Instantly enrollment/send.
- No HubSpot/provider writes.
- No SMS/email/Vapi sends.
- No live county/source-provider pulls.
- No manager approval execution.
- No live Slack post.
- No Telegram workflow delivery.
- No Supabase remote migration.
- No VPS deploy.

## Remaining gates

- This branch still needs review/merge/deploy before any hosted Mission Control UI sees the new segmentation.
- Runtime API 404s for `/deals` and `/deals/fire-list` during local fixture-backed dev remain expected fixture fallback behavior for this local UI smoke, not proof of production deal-readiness.
- Live Chief of Staff Slack posting still requires the already-documented Slack route migration/configuration and explicit `--send-slack` use after deployment.
