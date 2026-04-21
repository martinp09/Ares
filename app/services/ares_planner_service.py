from __future__ import annotations

from app.domains.ares import (
    AresCounty,
    AresPlannerActionType,
    AresPlannerCheck,
    AresPlannerPlan,
    AresPlannerStep,
    AresSourceLane,
)


class AresPlannerService:
    def build_plan(self, *, goal: str) -> AresPlannerPlan:
        normalized_goal = goal.strip()
        counties = self._counties_for_goal(normalized_goal)
        source_lanes = self._source_lanes_for_goal(normalized_goal)
        checks = self._checks_for_goal(counties=counties, source_lanes=source_lanes)
        steps = self._steps_for_goal(counties=counties, source_lanes=source_lanes)

        return AresPlannerPlan(
            goal=normalized_goal,
            counties=counties,
            source_lanes=source_lanes,
            checks=checks,
            steps=steps,
            rationale=self._rationale_for_goal(counties=counties, source_lanes=source_lanes),
        )

    def explain_plan(self, plan: AresPlannerPlan) -> str:
        lane_summary = ", ".join(lane.value for lane in plan.source_lanes)
        county_summary = ", ".join(county.value for county in plan.counties) or "all configured counties"
        checks = "; ".join(f"{check.name}: {check.description}" for check in plan.checks)
        steps = "\n".join(f"{step.step_id}. {step.description}" for step in plan.steps)

        return (
            f"Goal: {plan.goal}\n"
            f"County scope: {county_summary}\n"
            f"Source lanes: {lane_summary}\n"
            f"Checks: {checks}\n"
            f"Rationale: {plan.rationale}\n"
            f"Steps:\n{steps}\n"
            "Approval required before any side-effecting step is executed."
        )

    def _counties_for_goal(self, goal: str) -> list[AresCounty]:
        goal_lower = goal.lower()
        counties: list[AresCounty] = []
        for county in AresCounty:
            if county.value in goal_lower:
                counties.append(county)
        return counties

    def _source_lanes_for_goal(self, goal: str) -> list[AresSourceLane]:
        goal_lower = goal.lower()

        lanes: list[AresSourceLane] = []
        if "probate" in goal_lower:
            lanes.append(AresSourceLane.PROBATE)

        if "tax" in goal_lower or "delinquent" in goal_lower:
            lanes.append(AresSourceLane.TAX_DELINQUENT)

        if not lanes:
            lanes.append(AresSourceLane.PROBATE)

        return lanes

    def _checks_for_goal(
        self,
        *,
        counties: list[AresCounty],
        source_lanes: list[AresSourceLane],
    ) -> list[AresPlannerCheck]:
        county_check = AresPlannerCheck(
            name="county_scope",
            description=(
                "Restrict record pull to requested county slice."
                if counties
                else "Use configured phase-1 counties when no county slice is specified."
            ),
        )
        checks = [county_check]

        if AresSourceLane.TAX_DELINQUENT in source_lanes:
            checks.append(
                AresPlannerCheck(
                    name="overlay_match_quality",
                    description="Verify county plus normalized address match before overlaying tax-delinquent data.",
                )
            )

        checks.append(
            AresPlannerCheck(
                name="approval_gate",
                description="Require explicit operator approval before any side-effecting action.",
            )
        )

        return checks

    def _steps_for_goal(
        self,
        *,
        counties: list[AresCounty],
        source_lanes: list[AresSourceLane],
    ) -> list[AresPlannerStep]:
        county_summary = ", ".join(county.value for county in counties) or "configured phase-1 counties"
        steps: list[AresPlannerStep] = []

        step_number = 1
        if AresSourceLane.PROBATE in source_lanes:
            steps.append(
                AresPlannerStep(
                    step_id=f"step-{step_number}",
                    description=f"Pull probate leads for {county_summary}.",
                    source_lane=AresSourceLane.PROBATE,
                )
            )
            step_number += 1

        if AresSourceLane.TAX_DELINQUENT in source_lanes:
            steps.append(
                AresPlannerStep(
                    step_id=f"step-{step_number}",
                    description=f"Pull verified tax-delinquent records for {county_summary}.",
                    source_lane=AresSourceLane.TAX_DELINQUENT,
                )
            )
            step_number += 1

        primary_lane = source_lanes[0]
        steps.append(
            AresPlannerStep(
                step_id=f"step-{step_number}",
                description="Run county/address matching and produce ranked opportunities.",
                source_lane=primary_lane,
            )
        )
        step_number += 1

        steps.append(
            AresPlannerStep(
                step_id=f"step-{step_number}",
                description="Generate operator-facing lead briefs and outreach drafts for review.",
                source_lane=primary_lane,
            )
        )
        step_number += 1

        steps.append(
            AresPlannerStep(
                step_id=f"step-{step_number}",
                description="Queue approved side-effecting actions only after explicit operator approval.",
                source_lane=primary_lane,
                action_type=AresPlannerActionType.SIDE_EFFECTING,
                requires_approval=True,
            )
        )

        return steps

    def _rationale_for_goal(
        self,
        *,
        counties: list[AresCounty],
        source_lanes: list[AresSourceLane],
    ) -> str:
        county_scope = ", ".join(county.value for county in counties) if counties else "configured phase-1 counties"
        lane_summary = " + ".join(lane.value for lane in source_lanes)
        return (
            f"This plan scopes work to {county_scope}, uses {lane_summary}, "
            "runs deterministic matching checks first, and keeps all side effects behind operator approval."
        )
