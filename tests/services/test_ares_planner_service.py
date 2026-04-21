from app.domains.ares import (
    AresCounty,
    AresPlannerActionType,
    AresSourceLane,
)
from app.services.ares_planner_service import AresPlannerService


def test_planner_accepts_probate_plus_tax_goal_with_county_slice() -> None:
    service = AresPlannerService()

    plan = service.build_plan(goal="Find probate plus tax-delinquent leads in Harris County")

    assert plan.goal == "Find probate plus tax-delinquent leads in Harris County"
    assert plan.counties == [AresCounty.HARRIS]


def test_planner_chooses_source_lanes_and_checks_for_probate_plus_tax_goal() -> None:
    service = AresPlannerService()

    plan = service.build_plan(goal="Find probate plus tax-delinquent leads in Harris County")

    assert plan.source_lanes == [AresSourceLane.PROBATE, AresSourceLane.TAX_DELINQUENT]
    check_names = {check.name for check in plan.checks}
    assert "county_scope" in check_names
    assert "overlay_match_quality" in check_names


def test_planner_returns_concrete_steps_with_approval_gate_and_rationale() -> None:
    service = AresPlannerService()

    plan = service.build_plan(goal="Find probate plus tax-delinquent leads in Harris County")

    assert len(plan.steps) >= 4
    assert plan.steps[0].step_id == "step-1"
    assert "harris" in plan.steps[0].description.lower()

    final_step = plan.steps[-1]
    assert final_step.action_type is AresPlannerActionType.SIDE_EFFECTING
    assert final_step.requires_approval is True

    assert "probate" in plan.rationale.lower()
    assert "tax" in plan.rationale.lower()


def test_planner_explains_plan_for_operator_review() -> None:
    service = AresPlannerService()

    plan = service.build_plan(goal="Find probate plus tax-delinquent leads in Harris County")
    explanation = service.explain_plan(plan)

    assert "Goal:" in explanation
    assert "Source lanes:" in explanation
    assert "Checks:" in explanation
    assert "Approval required before" in explanation


def test_planner_rejects_whitespace_only_goal() -> None:
    service = AresPlannerService()

    try:
        service.build_plan(goal="   ")
    except Exception as exc:
        assert "at least 1 character" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected whitespace-only goal to be rejected")
