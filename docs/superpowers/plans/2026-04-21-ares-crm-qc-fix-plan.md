# Ares CRM QC Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 21 QC findings from the Ares CRM master-scope build, add regression coverage for every confirmed bug, and verify the fixes do not regress existing `origin/main` Mission Control / control-plane behavior.

**Architecture:** Fixes are grouped by risk boundary instead of by chronology: (1) runtime/planner/execution contract bugs, (2) Mission Control/operator visibility bugs, and (3) shared foundations/persistence/workflow bugs. Every fix starts with a failing regression test, stays lane-separated, and uses `origin/main` as the baseline for pre-existing files (`mission_control`, `db/client`, `main`, package layout, reset behavior) so we do not “fix” the branch by breaking inherited behavior.

**Tech Stack:** FastAPI, Pydantic, Python services, in-memory/file-backed control-plane state, pytest.

---

## QC issue ledger

### Runtime / planner / execution
1. Tax-only leads falsely treated as estate-verified
2. Hard approval bypass with fake approval ID
3. Action budget bypass by reusing `action_id`
4. Whitespace-only planner goal returns 500
5. Tax-only suppression may be globally scoped instead of county-scoped

### Mission Control / operator visibility
6. Mission Control shows stale phase-5 operator state after newer execution run
7. Planner-only flows misclassified as phase 1
8. `reset_control_plane_state()` does not clear file-backed operator/eval state
9. Autonomy visibility freshness metadata may drift from actual artifact freshness
10. Guarded operator initialization may become double-run side-effect trouble

### Shared foundations / workflow / persistence
11. First memory event is dropped
12. Playbook fetch failure overwritten to `completed`
13. Concurrent writers clobber memory history
14. Concurrent writers clobber eval history
15. Eval metrics allow impossible values above `1.0`
16. Workflow retry counts survive restart of same `workflow_id`
17. Agent registry revisions are mutable
18. Output-contract failures are missing from audit trail
19. `supabase` backend path is dead / misleading
20. Policy layer still trusts truthy approval strings too much
21. File persistence is non-atomic and corruption-intolerant

---

## Task 1: Scope freeze + `origin/main` baseline map

**Files:**
- Modify: `docs/superpowers/plans/2026-04-21-ares-crm-qc-fix-plan.md`
- Reference only: `app/api/mission_control.py`
- Reference only: `app/services/mission_control_service.py`
- Reference only: `app/db/client.py`
- Reference only: `app/main.py`
- Reference only: `tests/api/test_mission_control_phase3.py`
- Reference only: `tests/test_package_layout.py`

- [ ] Confirm active repo/worktree is `/root/.hermes/_repos/Hermes-Central-Command` on the QC/fix branch before any edits.
- [ ] Run `git diff --stat origin/main -- app/api/mission_control.py app/services/mission_control_service.py app/db/client.py app/main.py tests/api/test_mission_control_phase3.py tests/test_package_layout.py` and save the output in work notes so every edit to inherited files can be justified against baseline behavior.
- [ ] Classify each issue as either:
  - branch-local Ares bug,
  - inherited file contract regression risk,
  - or “needs explicit fail-fast contract instead of hidden dead path.”
- [ ] Freeze scope: no loop-guardrail work, no new Ralph/QC framework work, no unrelated refactors.
- [ ] Create a working issue checklist in local notes with one checkbox per issue ID 1-21 so nothing silently drops.

**Verification:**
- Run: `git branch --show-current && git rev-parse --show-toplevel`
- Run: `git diff --stat origin/main -- app/api/mission_control.py app/services/mission_control_service.py app/db/client.py app/main.py tests/api/test_mission_control_phase3.py tests/test_package_layout.py`
- Expected: branch/repo confirmed and baseline diff captured.

---

## Task 2: Add regression tests for runtime/planner/execution bugs (issues 1-5)

**Files:**
- Modify: `tests/services/test_ares_service.py`
- Modify: `tests/services/test_ares_policy_service.py`
- Modify: `tests/services/test_ares_execution_service.py`
- Modify: `tests/services/test_ares_planner_service.py`
- Modify: `tests/api/test_ares_plans.py`
- Modify: `tests/api/test_ares_runtime.py`

- [ ] Add a regression test proving a plain tax-delinquent owner like `John Doe` does **not** become `estate_of=True` automatically and does **not** rank as `TAX_ONLY_ESTATE_VERIFIED`.
- [ ] Add a regression test proving hard approval fails when the approval id is fabricated / unregistered / wrong state.
- [ ] Add a regression test proving repeated authorization with the same `action_id` still consumes budget or is rejected after the first allowed call.
- [ ] Add a regression test proving `POST /ares/plans` with whitespace-only goal returns a 4xx contract error, not 500.
- [ ] Add a characterization test for multi-county probate/tax behavior so the intended county-scoped vs global rule is explicit before code changes.
- [ ] Add API-level regressions for any bypass that can currently be reached through `/ares/execution/run` or `/ares/plans`.

**Verification:**
- Run: `uv run pytest tests/services/test_ares_service.py tests/services/test_ares_policy_service.py tests/services/test_ares_execution_service.py tests/services/test_ares_planner_service.py tests/api/test_ares_plans.py tests/api/test_ares_runtime.py -q`
- Expected: newly added regressions fail before implementation changes.

---

## Task 3: Fix runtime/planner/execution behavior (issues 1-5)

**Files:**
- Modify: `app/domains/ares/models.py`
- Modify: `app/services/ares_service.py`
- Modify: `app/services/ares_policy_service.py`
- Modify: `app/services/ares_execution_service.py`
- Modify: `app/services/ares_planner_service.py`
- Modify: `app/api/ares.py`

- [ ] Tighten estate detection so tax-delinquent source alone does not auto-certify `estate_of=True`; require explicit estate evidence.
- [ ] Make tax-only ranking logic enforce the real estate verification rule and document/test whether probate suppression is county-scoped or global.
- [ ] Replace truthy-string hard approval checks with actual approval validation semantics (existence + allowed state + scope).
- [ ] Rework execution budget accounting so repeated use of one `action_id` cannot mint unlimited `ALLOW` decisions.
- [ ] Normalize planner goal validation at the request boundary so whitespace-only goals are rejected deterministically.
- [ ] Keep fixes narrow: do not redesign the runtime; patch the contracts and state transitions only.

**Verification:**
- Run: `uv run pytest tests/services/test_ares_service.py tests/services/test_ares_policy_service.py tests/services/test_ares_execution_service.py tests/services/test_ares_planner_service.py tests/api/test_ares_plans.py tests/api/test_ares_runtime.py -q`
- Run: `uv run python -m compileall app tests`
- Expected: runtime/planner/execution regressions pass and code still compiles.

---

## Task 4: Add Mission Control / operator regressions (issues 6-10)

**Files:**
- Modify: `tests/api/test_mission_control_phase3.py`
- Create or modify if needed: `tests/services/test_mission_control_service.py`
- Modify if needed: `tests/api/test_ares_plans.py`
- Modify if needed: `tests/api/test_ares_runtime.py`

- [ ] Add a regression proving a newer execution run replaces stale operator-driven phase/next-action state for the same `(business_id, environment)`.
- [ ] Add a regression proving planner-only flows are shown as planner review, not phase 1 lead wedge.
- [ ] Add a regression proving `reset_control_plane_state()` also resets any operator/eval state that affects supposedly fresh runs.
- [ ] Add a characterization/regression test for autonomy visibility `updated_at` so it reflects the newest displayed artifact.
- [ ] Add a regression guarding against duplicate guarded-operator initialization side effects.

**Verification:**
- Run: `uv run pytest tests/api/test_mission_control_phase3.py tests/services/test_mission_control_service.py -q`
- Expected: new regressions fail before service changes.

---

## Task 5: Fix Mission Control / operator visibility behavior (issues 6-10)

**Files:**
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `app/models/mission_control.py`
- Modify: `app/services/ares_autonomous_operator_service.py`
- Modify: `app/main.py`
- Modify if needed: `app/services/run_service.py`
- Reference against baseline: `origin/main` versions of the inherited files above

- [ ] Rework autonomy-visibility precedence so the newest relevant artifact wins instead of stale operator snapshots dominating the read model.
- [ ] Correct planner-only phase classification and `next_action` derivation.
- [ ] Make reset semantics clear and deterministic across in-memory + file-backed operator/eval state.
- [ ] Align `updated_at` semantics with the actual artifact displayed in Mission Control.
- [ ] Ensure guarded-operator initialization is idempotent and not repeated in a way that can duplicate stateful side effects.
- [ ] Compare every inherited-file change against `origin/main` before finalizing so existing Mission Control contracts are preserved unless the regression test says otherwise.

**Verification:**
- Run: `uv run pytest tests/api/test_mission_control_phase3.py tests/services/test_mission_control_service.py tests/api/test_ares_plans.py tests/test_package_layout.py -q`
- Run: `git diff --stat origin/main -- app/api/mission_control.py app/services/mission_control_service.py app/models/mission_control.py app/main.py`
- Expected: tests pass and diff against baseline is only the intended Ares visibility/operator changes.

---

## Task 6: Add regressions for shared foundations / workflow / persistence bugs (issues 11-21)

**Files:**
- Modify: `tests/services/test_ares_memory_service.py`
- Modify: `tests/services/test_ares_playbook_service.py`
- Modify: `tests/services/test_ares_eval_loop_service.py`
- Modify: `tests/services/test_ares_eval_service.py`
- Modify: `tests/services/test_ares_state_service.py`
- Modify: `tests/services/test_ares_agent_registry_service.py`
- Modify: `tests/services/test_ares_policy_service.py`
- Modify if needed: `tests/domains/ares_workflows/test_workflow_models.py`

- [ ] Add a regression proving the very first memory event survives in a fresh service instance.
- [ ] Add a regression proving failed playbook fetch steps remain failed/retrying instead of being overwritten to completed.
- [ ] Add concurrent-writer regression coverage for memory and eval history persistence.
- [ ] Add validation regressions preventing impossible eval metrics above `1.0`.
- [ ] Add a regression proving restarting the same `workflow_id` resets retry counters.
- [ ] Add a regression proving agent revisions are immutable once a `(name, revision)` is registered.
- [ ] Add a regression proving output-validation failures are still audited.
- [ ] Add a regression or contract test clarifying what happens when `control_plane_backend='supabase'` is selected.
- [ ] Add at least one corruption-tolerance test for malformed JSON / partial persistence recovery expectations so issue 21 is pinned down.

**Verification:**
- Run: `uv run pytest tests/services/test_ares_memory_service.py tests/services/test_ares_playbook_service.py tests/services/test_ares_eval_loop_service.py tests/services/test_ares_eval_service.py tests/services/test_ares_state_service.py tests/services/test_ares_agent_registry_service.py tests/services/test_ares_policy_service.py tests/domains/ares_workflows/test_workflow_models.py -q`
- Expected: new regressions fail before service changes.

---

## Task 7: Fix shared foundations / workflow / persistence behavior (issues 11-21)

**Files:**
- Modify: `app/services/ares_memory_service.py`
- Modify: `app/services/ares_playbook_service.py`
- Modify: `app/services/ares_eval_loop_service.py`
- Modify: `app/services/ares_eval_service.py`
- Modify: `app/services/ares_state_service.py`
- Modify: `app/services/ares_agent_registry_service.py`
- Modify: `app/services/ares_policy_service.py`
- Modify: `app/db/client.py`
- Modify if needed: `app/domains/ares_workflows/*`

- [ ] Fix memory append semantics so the first event is never lost.
- [ ] Preserve failure/retry/fallback state in playbook execution instead of overwriting it with completed.
- [ ] Add deterministic write semantics (reload/merge/lock/atomic-write strategy) for memory and eval persistence.
- [ ] Enforce cross-field metric validation so impossible ratios are rejected.
- [ ] Reset workflow retry counters when a workflow is restarted.
- [ ] Make agent revisions immutable or reject duplicate conflicting registrations.
- [ ] Ensure output contract validation failures still leave an audit record.
- [ ] Resolve the dead `supabase` backend path one of two ways:
  - implement a real supported adapter if `origin/main` already expects it, or
  - convert it to an explicit fail-fast unsupported contract so the system no longer advertises a fake path.
- [ ] Harden file persistence enough that malformed/corrupted files fail predictably and, where feasible, use atomic writes.

**Verification:**
- Run: `uv run pytest tests/services/test_ares_memory_service.py tests/services/test_ares_playbook_service.py tests/services/test_ares_eval_loop_service.py tests/services/test_ares_eval_service.py tests/services/test_ares_state_service.py tests/services/test_ares_agent_registry_service.py tests/services/test_ares_policy_service.py tests/domains/ares_workflows/test_workflow_models.py -q`
- Run: `uv run python -m compileall app tests`
- Expected: all foundation/workflow regressions pass and the persistence contract is explicit.

---

## Task 8: Whole-slice verification + issue closeout

**Files:**
- Modify: `docs/superpowers/plans/2026-04-21-ares-crm-qc-fix-plan.md`
- Modify if needed: `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-progress.txt` (only if the user wants issue-tracking notes there; otherwise leave untouched)

- [ ] Run the full targeted Ares + Mission Control verification slice after all fixes land.
- [ ] Re-run manual repros for the critical bugs (issues 1, 2, 3, 6, 11, 12).
- [ ] Check `git diff --check` and `git status --short`.
- [ ] Mark each issue 1-21 as closed, converted to design decision, or intentionally deferred (there should be no silent “maybe”).
- [ ] Record any remaining suspicious-but-unproven concerns separately so they do not get mixed in with closed bugs.

**Verification:**
- Run: `uv run pytest tests/api/test_ares_runtime.py tests/api/test_ares_plans.py tests/api/test_mission_control_phase3.py tests/services/test_ares_service.py tests/services/test_ares_copy_service.py tests/services/test_ares_planner_service.py tests/services/test_ares_execution_service.py tests/services/test_ares_memory_service.py tests/services/test_ares_playbook_service.py tests/services/test_ares_eval_loop_service.py tests/services/test_ares_eval_service.py tests/services/test_ares_state_service.py tests/services/test_ares_agent_registry_service.py tests/services/test_ares_policy_service.py tests/domains/ares/test_models.py tests/domains/ares/test_agent_registry_models.py tests/domains/ares_planning/test_planner_models.py tests/domains/ares_workflows/test_workflow_models.py tests/test_package_layout.py -q`
- Run: `uv run python -m compileall app tests`
- Run: `git diff --check && git status --short`
- Expected: targeted regression slice passes, compile passes, working tree contains only the intended fix-set.

---

## Issue-to-task mapping

- Issues 1-5 → Tasks 2-3
- Issues 6-10 → Tasks 4-5
- Issues 11-21 → Tasks 6-7
- `origin/main` safety / inherited-file comparison → Tasks 1, 5, 8

---

## Notes / guardrails for the fix pass

- Prefer service-layer fixes and route-boundary validation over wide refactors.
- For inherited files (`mission_control`, `db/client`, `main`, package layout), compare against `origin/main` before and after each patch cluster.
- Do **not** implement the future Ralph/loop internal QC system in this pass.
- If issue 19 (`supabase` backend) cannot be safely implemented without backend wiring, fix the lie instead: explicit unsupported contract + tests beats a hidden dead path.
- When in doubt, choose deterministic fail-fast behavior over magical fallback.
