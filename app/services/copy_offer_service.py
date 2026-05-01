from __future__ import annotations

from app.domains.ares import AresSourceLane
from app.models.copy_offers import CopyAssetStatus, CopySegment, OfferAsset


class CopyOfferService:
    def build_harris_probate_offer(self, *, segment: CopySegment = CopySegment.ALL) -> OfferAsset:
        segment_label = segment.value if segment is not CopySegment.ALL else "all"
        return OfferAsset(
            id=f"harris-probate-inherited-property-exit-{segment_label}",
            name="Inherited Property Exit Option",
            source_lane=AresSourceLane.PROBATE,
            segment=segment,
            audience=self._audience_for(segment),
            pain_points=self._pain_points_for(segment),
            dream_outcome=(
                "Get clarity on whether an inherited Harris County property has a simple as-is sale path "
                "without starting with repairs, cleanup, listing prep, or perfect paperwork."
            ),
            likelihood_boosters=[
                "Local buyer/investor context for Harris County inherited properties.",
                "As-is review before the family spends time repairing or cleaning out the property.",
                "Comfortable discussing repairs, cleanout, title questions, tax pressure, and multiple-heir friction without making legal promises.",
            ],
            time_delay_reducers=[
                "Start with a short call or text instead of a full listing process.",
                "Review the property before requiring every title, tax, or cleanup issue to be resolved.",
            ],
            effort_reducers=[
                "No repairs before the first conversation.",
                "No cleanup or cleanout before the first conversation.",
                "No open houses, showings, or MLS prep before learning whether a buyer option exists.",
            ],
            risk_reversal=(
                "If keeping the property is the plan or it is not a fit, the seller can say so and Martin closes his notes."
            ),
            unique_mechanism=(
                "Ares-guided inherited-property review: match probate/property/tax context, then frame a practical as-is buyer conversation without presenting legal or tax advice."
            ),
            proof_points=[
                "Ares has segmented the Harris probate batch into HOT/WARM/COLD and separates direct-mail-ready records from email/SMS enrichment gaps.",
            ],
            value_stack=[
                "As-is property review",
                "Repair and cleanout friction acknowledged up front",
                "Title/tax/heirship questions treated as conversation context, not seller homework before the first call",
                "Low-pressure keep/sell/rent clarity conversation",
            ],
            constraints=[
                "No legal, tax, or probate advice claims.",
                "No guaranteed purchase, closing, title cure, tax solution, or timeline.",
                "No fake scarcity or pressure language.",
                "No Instantly/TextGrid/direct-mail send without operator approval.",
            ],
            truth_risk_notes=[
                "Verify any property-specific tax/title/probate claim before using it in copy.",
                "Use 'may be able to help' or 'if it is a fit' when outcome is uncertain.",
                "Do not imply Martin is an attorney, broker, tax advisor, or probate representative.",
            ],
            status=CopyAssetStatus.REVIEW_REQUIRED,
            auto_send=False,
        )

    @staticmethod
    def _audience_for(segment: CopySegment) -> str:
        if segment is CopySegment.HOT:
            return "Harris County probate contacts with stronger property, tax, title, or operator-review urgency signals."
        if segment is CopySegment.WARM:
            return "Harris County probate contacts who may be handling inherited-property decisions but have less verified urgency."
        if segment is CopySegment.COLD:
            return "Lower-confidence Harris County probate/property contacts who need a soft wrong-person-safe opener."
        return "Harris County probate and inherited-property contacts across HOT/WARM/COLD segments."

    @staticmethod
    def _pain_points_for(segment: CopySegment) -> list[str]:
        shared = [
            "Inherited property decisions can be emotionally and logistically heavy.",
            "A normal listing may not fit when the property needs repairs or cleanout.",
            "Title, tax, heirship, or multiple-family-member questions can slow decisions.",
        ]
        if segment is CopySegment.HOT:
            return [
                "The property may already feel like an urgent project.",
                "Taxes, title friction, repairs, or cleanup may be creating pressure.",
                *shared,
            ]
        if segment is CopySegment.WARM:
            return [
                "The family may still be deciding whether to keep, sell, rent, or evaluate the property.",
                *shared,
            ]
        if segment is CopySegment.COLD:
            return [
                "The contact may not know why they are being contacted or may not be the right person.",
                *shared,
            ]
        return shared
