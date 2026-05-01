from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.domains.ares import AresCounty, AresSourceLane
from app.models.copy_offers import CopySegment
from app.services.ares_service import AresLeadTier, RankedAresLead
from app.services.copy_asset_service import CopyAssetService
from app.services.copy_offer_service import CopyOfferService


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
    def __init__(
        self,
        *,
        offer_service: CopyOfferService | None = None,
        asset_service: CopyAssetService | None = None,
    ) -> None:
        self._offer_service = offer_service or CopyOfferService()
        self._asset_service = asset_service or CopyAssetService()

    def generate_lead_briefs(self, ranked_opportunities: Iterable[RankedAresLead]) -> list[AresLeadBrief]:
        return [self._build_brief(opportunity) for opportunity in ranked_opportunities]

    def generate_outreach_drafts(self, ranked_opportunities: Iterable[RankedAresLead]) -> list[AresOutreachDraft]:
        return [self._build_draft(opportunity) for opportunity in ranked_opportunities]

    def _build_brief(self, opportunity: RankedAresLead) -> AresLeadBrief:
        rationale = self._rationale_for(opportunity)
        lead = opportunity.lead
        offer = self._offer_service.build_harris_probate_offer(segment=self._segment_for(opportunity))
        return AresLeadBrief(
            rank=opportunity.rank,
            county=lead.county,
            source_lane=lead.source_lane,
            rationale=rationale,
            brief=(
                f"Rank #{opportunity.rank} in {lead.county.value}: {lead.property_address}. "
                f"Primary lane {lead.source_lane.value}. {rationale} "
                f"Offer: {offer.name} — {offer.dream_outcome}"
            ),
        )

    def _build_draft(self, opportunity: RankedAresLead) -> AresOutreachDraft:
        rationale = self._rationale_for(opportunity)
        lead = opportunity.lead
        segment = self._segment_for(opportunity)
        offer = self._offer_service.build_harris_probate_offer(segment=segment)
        email_asset = self._asset_service.build_email_asset(offer=offer, segment=segment)
        body = email_asset.body.replace("{{property_address}}", lead.property_address)
        if lead.owner_name:
            body = body.replace("{{first_name}}", self._first_name_from_owner(lead.owner_name))
        return AresOutreachDraft(
            rank=opportunity.rank,
            county=lead.county,
            source_lane=lead.source_lane,
            rationale=rationale,
            approval_status="pending_human_approval",
            auto_send=False,
            subject=f"Rank #{opportunity.rank}: {email_asset.headline_or_subject or 'Inherited property question'}".replace(
                "{{property_address}}", lead.property_address
            ),
            body=(
                f"Rank #{opportunity.rank} opportunity in {lead.county.value} county.\n"
                f"Source lane: {lead.source_lane.value}\n"
                f"Rationale: {rationale}\n"
                f"Offer: {offer.name}\n"
                "Approval: required before any provider enrollment.\n\n"
                "Draft message:\n"
                f"{body}"
            ),
        )

    def _rationale_for(self, opportunity: RankedAresLead) -> str:
        if opportunity.tier == AresLeadTier.PROBATE_WITH_VERIFIED_TAX:
            return "Probate lead with verified tax delinquency overlay."
        if opportunity.tier == AresLeadTier.PROBATE_ONLY:
            return "Probate lead ranked without verified tax overlay."
        return "Tax-delinquent estate lead verified without probate match."

    @staticmethod
    def _segment_for(opportunity: RankedAresLead) -> CopySegment:
        if opportunity.tier == AresLeadTier.PROBATE_WITH_VERIFIED_TAX:
            return CopySegment.HOT
        if opportunity.tier == AresLeadTier.PROBATE_ONLY:
            return CopySegment.WARM
        return CopySegment.COLD

    @staticmethod
    def _first_name_from_owner(owner_name: str) -> str:
        cleaned = owner_name.replace("Estate of", "").replace("ESTATE OF", "").strip(" ,")
        return cleaned.split()[0] if cleaned.split() else "there"
