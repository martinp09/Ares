from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domains.ares import AresCounty, AresSourceLane
from app.services.ares_service import AresLeadTier, RankedAresLead


@dataclass(frozen=True)
class AresLeadBrief:
    rank: int
    county: AresCounty
    source_lane: AresSourceLane
    rationale: str
    brief: str


@dataclass(frozen=True)
class AresOutreachDraft:
    rank: int
    county: AresCounty
    source_lane: AresSourceLane
    rationale: str
    approval_status: str
    auto_send: bool
    subject: str
    body: str


class AresCopyService:
    def generate_lead_briefs(self, ranked_opportunities: Iterable[RankedAresLead]) -> list[AresLeadBrief]:
        return [self._build_brief(opportunity) for opportunity in ranked_opportunities]

    def generate_outreach_drafts(self, ranked_opportunities: Iterable[RankedAresLead]) -> list[AresOutreachDraft]:
        return [self._build_draft(opportunity) for opportunity in ranked_opportunities]

    def _build_brief(self, opportunity: RankedAresLead) -> AresLeadBrief:
        rationale = self._rationale_for(opportunity)
        lead = opportunity.lead
        return AresLeadBrief(
            rank=opportunity.rank,
            county=lead.county,
            source_lane=lead.source_lane,
            rationale=rationale,
            brief=(
                f"Rank #{opportunity.rank} in {lead.county.value}: {lead.property_address}. "
                f"Primary lane {lead.source_lane.value}. {rationale}"
            ),
        )

    def _build_draft(self, opportunity: RankedAresLead) -> AresOutreachDraft:
        rationale = self._rationale_for(opportunity)
        lead = opportunity.lead
        return AresOutreachDraft(
            rank=opportunity.rank,
            county=lead.county,
            source_lane=lead.source_lane,
            rationale=rationale,
            approval_status="pending_human_approval",
            auto_send=False,
            subject=f"Ares outreach draft for {lead.property_address}",
            body=(
                f"Rank #{opportunity.rank} opportunity in {lead.county.value} county.\n"
                f"Source lane: {lead.source_lane.value}\n"
                f"Rationale: {rationale}\n\n"
                "Draft message:\n"
                f"Hello, I am reaching out about {lead.property_address}. "
                "If you are the right contact, I would like to discuss options."
            ),
        )

    def _rationale_for(self, opportunity: RankedAresLead) -> str:
        if opportunity.tier == AresLeadTier.PROBATE_WITH_VERIFIED_TAX:
            return "Probate lead with verified tax delinquency overlay."
        if opportunity.tier == AresLeadTier.PROBATE_ONLY:
            return "Probate lead ranked without verified tax overlay."
        return "Tax-delinquent estate lead verified without probate match."
