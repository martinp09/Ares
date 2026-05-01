from __future__ import annotations

from app.models.copy_assets import AwarenessLevel, CopyAsset, CopyAssetType, CopyChannel, CopyFramework
from app.models.copy_offers import CopySegment, OfferAsset


class CopyAssetService:
    def build_harris_probate_assets(self, offer: OfferAsset) -> list[CopyAsset]:
        segment = offer.segment if offer.segment is not CopySegment.ALL else CopySegment.HOT
        return [
            self.build_email_asset(offer=offer, segment=segment),
            self.build_direct_mail_asset(offer=offer, segment=segment),
            self.build_sms_asset(offer=offer, segment=segment),
        ]

    def build_email_asset(self, *, offer: OfferAsset, segment: CopySegment) -> CopyAsset:
        return CopyAsset(
            id=f"{offer.id}-{segment.value}-email-1",
            offer_id=offer.id,
            asset_type=CopyAssetType.EMAIL,
            channel=CopyChannel.INSTANTLY,
            source_lane=offer.source_lane,
            segment=segment,
            framework=CopyFramework.HYBRID,
            awareness_level=AwarenessLevel.PROBLEM_AWARE,
            headline_or_subject=self._email_subject(segment),
            body=(
                "Hi {{first_name}},\n\n"
                "I’m Martin. I’m reaching out about {{property_address}}.\n\n"
                "Inherited property decisions can get messy when repairs, cleanup, taxes, title questions, "
                "or multiple family members are involved. A normal listing is not always the easiest first step.\n\n"
                "I review some Harris County properties as-is and can tell you whether a simple buyer option makes sense "
                "before the family spends time repairing or cleaning it out.\n\n"
                "Are you the right person to ask about this property?\n\n"
                "Martin"
            ),
            hook_variants=[
                "If {{property_address}} is becoming one more project",
                "Question about the inherited property",
                "Are you handling {{property_address}}?",
            ],
            critique_notes=[
                "Pain-first opener names probate friction before the offer.",
                "Mechanism is an as-is review, not a generic cash-buyer pitch.",
                "CTA asks for right-person confirmation before pushing for a call.",
            ],
            truth_risk_notes=list(offer.truth_risk_notes),
            template_variables=["first_name", "property_address"],
        )

    def build_direct_mail_asset(self, *, offer: OfferAsset, segment: CopySegment) -> CopyAsset:
        return CopyAsset(
            id=f"{offer.id}-{segment.value}-direct-mail-1",
            offer_id=offer.id,
            asset_type=CopyAssetType.DIRECT_MAIL,
            channel=CopyChannel.DIRECT_MAIL,
            source_lane=offer.source_lane,
            segment=segment,
            framework=CopyFramework.HYBRID,
            awareness_level=AwarenessLevel.PROBLEM_AWARE,
            headline_or_subject="Re: {{property_address}}",
            body=(
                "Hi {{recipient_name}},\n\n"
                "I’m reaching out because the property above appears connected to an inherited-property situation in Harris County. "
                "If the family is already handling it, you can ignore this.\n\n"
                "But if the house is becoming one more project — repairs, cleanup, taxes, title questions, or deciding what everyone wants to do — "
                "I may be able to give you a simple as-is option. You would not need to repair it, clean it out, or prepare it for showings before we talk.\n\n"
                "If selling as-is would help, call or text me at {{martin_phone}}. If keeping it is the plan, no problem.\n\n"
                "Respectfully,\nMartin Perales\n{{martin_phone}}"
            ),
            hook_variants=[
                "Inherited-property situation in Harris County",
                "If the house is becoming one more project",
            ],
            critique_notes=[
                "Respectful escape hatch lowers defensiveness.",
                "Names the offer after seller pain is acknowledged.",
            ],
            truth_risk_notes=list(offer.truth_risk_notes),
            template_variables=["recipient_name", "property_address", "martin_phone"],
        )

    def build_sms_asset(self, *, offer: OfferAsset, segment: CopySegment) -> CopyAsset:
        return CopyAsset(
            id=f"{offer.id}-{segment.value}-sms-1",
            offer_id=offer.id,
            asset_type=CopyAssetType.SMS,
            channel=CopyChannel.TEXTGRID,
            source_lane=offer.source_lane,
            segment=segment,
            framework=CopyFramework.SULTANIC_PAIN_FIRST,
            awareness_level=AwarenessLevel.PROBLEM_AWARE,
            body=(
                "Hi {{first_name}}, this is Martin. I’m reaching out about {{property_address}}. "
                "If the family is considering selling it as-is, is it okay if I ask one quick question?"
            ),
            hook_variants=[
                "Are you the right person to ask about {{property_address}}?",
                "Quick question about {{property_address}}",
            ],
            critique_notes=[
                "Permission-based first SMS; no link and no hard sell.",
                "Use only after phone confidence and suppression review.",
            ],
            truth_risk_notes=[*offer.truth_risk_notes, "SMS requires suppression/DNC/channel-confidence review before sending."],
            template_variables=["first_name", "property_address"],
        )

    @staticmethod
    def _email_subject(segment: CopySegment) -> str:
        if segment is CopySegment.HOT:
            return "If {{property_address}} is becoming a project"
        if segment is CopySegment.WARM:
            return "Quick question about {{property_address}}"
        return "Are you the right contact?"
