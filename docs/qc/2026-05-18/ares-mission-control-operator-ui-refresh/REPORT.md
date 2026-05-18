# Ares Mission Control Operator UI Refresh QC

Date: 2026-05-18
Branch: `feature/ares-chief-of-staff-v0`

## Scope

Refresh the Mission Control frontend so Martin sees a real-estate operator cockpit instead of a backend/admin-heavy dashboard.

## Changes verified

- Mission Control shell now uses a dark command-center layout inspired by the reference Mission Control UI:
  - compact left workspace rail
  - command/search bar
  - top status pills
  - large operator desk title
  - right-side manager/context brief
  - card-based action board
- Primary navigation now foregrounds real-estate work:
  - Today Desk
  - Replies / Submissions
  - Approvals
  - To-Do
  - Blocked / Dead
  - Source Health
  - Pipeline deal flow
- Backend/admin surfaces are hidden from the primary dashboard by default and require the deliberate command/search unlock `backstage` before they appear:
  - Agents
  - Catalog
  - Campaign State / Runs
  - Settings
  - They remain available as bounded backstage routes for regression coverage and internal access only.
- Dashboard summary no longer foregrounds backend counters such as active runs, live agents, provider failures, or system status.
- Primary dashboard now reads as a human action desk:
  - Hit list today
  - Replies to review
  - Needs approval
  - Research / skiptrace
  - Deals in motion
  - Blocked / suppressions
  - Probate/tax title lane
  - Lease-option lane
  - Deal desk
- Provider operations panel was removed from the primary dashboard.

## Verification

Commands run from `/opt/ares/worktrees/ares-chief-of-staff-v0` and captured in this QC folder:

```bash
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control test -- --run
npm --prefix apps/mission-control run build
```

Results:

- Typecheck: passed. Artifact: `typecheck-output.txt`.
- Mission Control tests: `25 passed` test files, `83 passed` tests. Artifact: `test-output.txt`.
- Build: passed, Vite production build completed. Artifact: `build-output.txt`.
- Diff whitespace check: passed before commit.
- Diff summary: `diff-summary.md`.

## Browser smoke

Local Vite server was opened at `http://127.0.0.1:5178` and visually inspected.

Observed:

- Dark command-center style is active.
- Primary UI foregrounds real-estate operator queues and action cards.
- Backstage section is hidden by default and only appears after the deliberate command/search unlock `backstage`.
- Accessibility snapshot did not expose `Agents`, `Catalog`, `Campaign State`/`Runs`, or `Settings` before unlock.
- DOM probe confirmed backstage `display: none`, hidden attr true, and hidden backstage buttons at `0x0` rect before unlock. Artifact: `browser-console.txt`.
- No live backend/provider actions were exposed on the primary dashboard.
- Screenshot: `dashboard-smoke.png`.

## Review fixes

Two bounded review passes were run before commit. Follow-up fixes made:

- Hidden backstage controls are now actually hidden/inert by default instead of visually clipped but still focusable.
- App tests now unlock backstage intentionally through the command/search input before exercising internal routes.
- Default operator tests were renamed away from the old agents-first wording.
- Action-card and kanban grids now use responsive `auto-fit` columns to reduce cramped card density.
- Small operator labels and notes were bumped for readability.
- Undefined `--text-muted` usage was replaced with the existing `--muted` token.

## Safety / side effects

No live side effects performed:

- No seller outreach.
- No provider sends.
- No paid skiptrace.
- No HubSpot/Instantly/TextGrid/Vapi writes.
- No Slack live post.
- No Supabase remote migration.
- No VPS deploy.
