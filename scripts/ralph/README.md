# Ralph loop for `feature/loose-ends`

This directory turns the probate outbound + lease-option inbound MVP blueprint into a Ralph-style fresh-session board.

## What is here
- `prd.json` — the board, one executable story per loop iteration
- `session-prompt.md` — the fresh-session prompt template for each writer run
- `progress.txt` — repo-local progress trail
- `watchdog.sh` — external restart loop that relaunches a fresh Codex writer until the board is done

## Important scope
- Repo root: `/home/workspace/Hermes-Central-Command/.worktrees/loose-ends`
- Branch: `feature/loose-ends`
- This is the probate outbound + lease-option inbound MVP
- Live Supabase wiring stays deferred in this pass
- `feature/ares-enterprise-platform` is out of scope

## Board shape
The executable board stories are:
1. Port the probate lead-machine slice from `origin/main`
2. Build the probate outbound write path
3. Harden the lease-option inbound lane
4. Add Mission Control dual-lane surfaces
5. Add the thin opportunity seam
6. Run verification and fixture smoke gates

Deferred backend-wiring items are kept in `prd.json.deferredStories` so the loop does not execute them during this pass.

## Run it
From the worktree root:

```bash
chmod +x scripts/ralph/watchdog.sh
RALPH_DRY_RUN=1 scripts/ralph/watchdog.sh
scripts/ralph/watchdog.sh
```

Defaults:
- writer: `codex exec`
- model: `gpt-5.3-codex`
- execution mode: `bypass` (`--dangerously-bypass-approvals-and-sandbox`) because this host hits `bwrap` sandbox failures under normal Codex workspace-write mode
- sandbox fallback setting: `workspace-write` when `RALPH_CODEX_EXECUTION_MODE=sandbox`
- max runs: `100`
- sleep between runs: `15s`

You can override them:

```bash
RALPH_MODEL=gpt-5.3-codex \
RALPH_MAX_RUNS=30 \
RALPH_SLEEP_SECONDS=10 \
RALPH_CODEX_EXECUTION_MODE=bypass \
scripts/ralph/watchdog.sh
```

If this host ever stops tripping over `bwrap`, you can opt back into Codex sandbox mode:

```bash
RALPH_CODEX_EXECUTION_MODE=sandbox \
RALPH_SANDBOX_MODE=workspace-write \
scripts/ralph/watchdog.sh
```

## How it works
- The watchdog reads `prd.json`
- It refuses to continue if a story is marked `blocked`
- It picks the first story with `passes: false`
- It builds a fresh prompt from `session-prompt.md` + board state + story details
- It launches a fresh `codex exec` run in this worktree
- After the run exits, it checks the board again and either stops or starts the next fresh invocation
- Each writer run works only one story at a time, but the watchdog keeps relaunching fresh runs until the entire executable board is done
- In this branch, that means the full probate outbound + lease-option inbound implementation plan except the explicitly deferred Supabase wiring stories

## Writer contract
Each fresh writer run must:
- read the required router docs and board files
- work one story only
- update `scripts/ralph/progress.txt`
- update the story status in `scripts/ralph/prd.json`
- stop after that single story

## Notes
- No `ralph` binary was found in this environment, so the watchdog uses `codex exec` as the writer.
- This host currently fails normal Codex workspace sandboxing with `bwrap: loopback: Failed RTM_NEWADDR: No child processes`, so bypass mode is the safe default here.
- The watchdog now stops immediately if the worker's final message says `status: blocked`, instead of relaunching forever and wasting tokens.
- If remote MCP auth or sandbox nonsense gets in the way, fix the local Codex config before blaming the board.
- Do not mark a story passing without real verification output. That would be fake progress wearing makeup.
