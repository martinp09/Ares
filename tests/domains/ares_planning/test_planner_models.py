from pydantic import ValidationError

from app.domains.ares import (
    AresPlannerActionType,
    AresPlannerCheck,
    AresPlannerPlan,
    AresPlannerStep,
    AresSourceLane,
)


def test_planner_plan_accepts_goal_source_lanes_checks_steps_and_rationale() -> None:
    plan = AresPlannerPlan(
        goal="Find high-confidence probate plus tax-overlay leads in Harris county",
        source_lanes=[AresSourceLane.PROBATE, AresSourceLane.TAX_DELINQUENT],
        checks=[
            AresPlannerCheck(
                name="county_scope",
                description="Restrict candidate pull to Harris county",
            )
        ],
        steps=[
            AresPlannerStep(
                step_id="collect_probate",
                description="Pull probate leads for Harris county",
                source_lane=AresSourceLane.PROBATE,
            ),
            AresPlannerStep(
                step_id="rank_overlay",
                description="Apply tax-delinquent overlay to probate set",
                source_lane=AresSourceLane.TAX_DELINQUENT,
                action_type=AresPlannerActionType.READ_ONLY,
            ),
        ],
        rationale="Probate-first plus tax overlay preserves phase-1 lead policy while improving pain-stack signal.",
    )

    assert plan.goal.startswith("Find high-confidence")
    assert [lane.value for lane in plan.source_lanes] == ["probate", "tax_delinquent"]
    assert plan.checks[0].name == "county_scope"
    assert [step.step_id for step in plan.steps] == ["collect_probate", "rank_overlay"]
    assert "phase-1 lead policy" in plan.rationale


def test_side_effecting_step_requires_explicit_approval() -> None:
    try:
        AresPlannerStep(
            step_id="enqueue_outreach",
            description="Enqueue outreach draft creation",
            source_lane=AresSourceLane.PROBATE,
            action_type=AresPlannerActionType.SIDE_EFFECTING,
            requires_approval=False,
        )
    except ValidationError as exc:
        assert "requires_approval" in str(exc)
    else:
        raise AssertionError("Expected side-effecting step without approval to fail")


def test_side_effecting_step_allows_explicit_approval() -> None:
    step = AresPlannerStep(
        step_id="enqueue_outreach",
        description="Enqueue outreach draft creation",
        source_lane=AresSourceLane.PROBATE,
        action_type=AresPlannerActionType.SIDE_EFFECTING,
        requires_approval=True,
    )

    assert step.action_type is AresPlannerActionType.SIDE_EFFECTING
    assert step.requires_approval is True
