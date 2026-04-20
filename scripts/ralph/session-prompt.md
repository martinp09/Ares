# Ares loose-ends Ralph session prompt

You are Ralph resuming implementation on the Ares repo in the branch `feature/loose-ends`.

## Hard scope
- Work ONLY in `/home/workspace/Hermes-Central-Command/.worktrees/loose-ends`.
- Branch of record: `feature/loose-ends`.
- Do NOT touch `feature/ares-enterprise-platform` for this task.
- Do NOT reintroduce the Ralph or enterprise master-plan file here.
- This branch is the probate outbound + lease-option inbound MVP.
- Live Supabase backend wiring is DELAYED for this pass.
- Everything else in the blueprint is in scope.

## Architecture rules
- Ares is the deterministic runtime.
- Hermes is the browser/research driver.
- Providers are transport only.
- Keep probate outbound and lease-option inbound separate in state and routing.
- Keep Mission Control lane-separated.
- Keep the opportunity seam thin; no full title, TC, or dispo automation.
- Keep execution memory-backed and fixture-backed in this pass.
- Preserve a later Supabase cutover plan, but do not activate it now.

## Required startup steps for every fresh run
1. Confirm the working tree and branch:
   - `git branch --show-current`
   - `git status --short`
   - `git rev-parse --show-toplevel`
2. Read these files in order:
   - `AGENTS.md`
   - `CONTEXT.md`
   - `TODO.md`
   - `memory.md`
   - `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md`
   - `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
   - `docs/superpowers/plans/2026-04-17-ares-scaffold-completion-plan.md`
   - `scripts/ralph/prd.json`
   - `scripts/ralph/progress.txt`
3. From `scripts/ralph/prd.json`, select the first `userStories[]` item with `passes: false` and a non-blocked status.
4. Work ONLY that one story in this run.
5. Keep changes small, surgical, and test-driven.
6. Do not start the next story in the same run.
7. The watchdog, not this single run, is responsible for finishing the entire executable board by repeatedly relaunching fresh runs until every non-deferred story has `passes: true`.

## Execution rules
- Follow the story’s goal, files, tasks, and acceptance gate exactly.
- Prefer porting or cherry-picking proven logic from `origin/main` when the story calls for existing lead-machine code.
- Do not activate live Supabase persistence, run migrations, or require live Supabase env vars.
- Keep all execution fixture-backed or memory-backed for this pass.
- If you add Trigger tasks, run the required Trigger checks for that slice.
- If you touch Mission Control, keep the UI additive and lane-separated.
- If you hit a blocker, stop, record it in `scripts/ralph/prd.json` and `scripts/ralph/progress.txt`, and exit instead of freelancing.

## Required state updates before exit
1. Update `scripts/ralph/progress.txt` with:
   - timestamp
   - story id
   - summary of work completed
   - files changed
   - tests/checks run and exact outcomes
   - blocker note if any
2. Update the current story in `scripts/ralph/prd.json`:
   - set `status` to `done` only if the acceptance gate is actually verified
   - set `passes` to `true` only after the verification commands for that story pass
   - set `status` to `blocked` with a real blocker note if the story cannot move forward safely
3. If the story changed repo scope or milestone state meaningfully, update `CONTEXT.md`, `TODO.md`, and `memory.md`.

## Final response format
- `story:` `<story-id>`
- `status:` `done | blocked | partial`
- `files:` bullet list
- `checks:` bullet list with command and pass/fail
- `next:` one sentence saying whether the watchdog should continue or stop

Do the work, verify it, update the board state, and then stop after the single story.
