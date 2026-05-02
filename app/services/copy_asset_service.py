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
        copy_hinge = self._copy_hinge_for(offer)
        return CopyAsset(
            id=f"{offer.id}-{segment.value}-email-1",
            offer_id=offer.id,
            asset_type=CopyAssetType.EMAIL,
            channel=CopyChannel.INSTANTLY,
            source_lane=offer.source_lane,
            segment=segment,
            framework=CopyFramework.HYBRID,
            awareness_level=AwarenessLevel.PROBLEM_AWARE,
            copy_hinge=copy_hinge,
            recency_signal="recent inherited-property/probate context tied to {{property_address}}",
            relevance_signal="find out whether an as-is option is worth discussing before repairs, cleanup, listing, or solving every issue first",
            personalization_signal=f"{segment.value} probate stage and property-specific address",
            offer_code_insights=list(offer.offer_code_insights),
            cta_gives="A low-pressure read on whether an as-is option is even worth discussing.",
            headline_or_subject=self._email_subject(segment),
            body=(
                "Hi {{first_name}},\n\n"
                f"{copy_hinge}\n\n"
                "Inherited property decisions can get messy when repairs, cleanup, taxes, title questions, "
                "or multiple family members are involved. A normal listing is not always the easiest first step.\n\n"
                "The useful shortcut is not a cash-buyer pitch. It is a quick as-is review so you can see whether "
                "there may be a simple path before the family spends time or money getting the house, paperwork, or everyone’s decision perfect.\n\n"
                "If helpful, I can give you a quick read on whether an as-is option is even worth discussing for {{property_address}}.\n\n"
                "Martin"
            ),
            hook_variants=[
                "If {{property_address}} is becoming one more project",
                "Question about the inherited property",
                "Are you handling {{property_address}}?",
            ],
            critique_notes=[
                "Pain-first opener names probate friction before the offer.",
                "High-response email formula is explicit: recency, relevance, and segment/property personalization are stored on the asset.",
                "Mechanism/outcome is a quick as-is review, not a generic cash-buyer product pitch.",
                "CTA gives a useful read on whether the as-is option is worth discussing before asking for seller effort.",
                "Rosetta Stone directives repeat the code: without repairs, cleanup, listing prep, perfect paperwork, or perfect family alignment.",
            ],
            truth_risk_notes=list(offer.truth_risk_notes),
            template_variables=["first_name", "property_address"],
        )

    def build_direct_mail_asset(self, *, offer: OfferAsset, segment: CopySegment) -> CopyAsset:
        copy_hinge = self._copy_hinge_for(offer)
        return CopyAsset(
            id=f"{offer.id}-{segment.value}-direct-mail-1",
            offer_id=offer.id,
            asset_type=CopyAssetType.DIRECT_MAIL,
            channel=CopyChannel.DIRECT_MAIL,
            source_lane=offer.source_lane,
            segment=segment,
            framework=CopyFramework.HYBRID,
            awareness_level=AwarenessLevel.PROBLEM_AWARE,
            copy_hinge=copy_hinge,
            offer_code_insights=list(offer.offer_code_insights),
            cta_gives="A simple as-is option if selling would help, with a clear no-pressure out if keeping it is the plan.",
            headline_or_subject="Re: {{property_address}}",
            body=(
                "Hi {{recipient_name}},\n\n"
                f"{copy_hinge}\n\n"
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
                "Offer-code language repeats what the seller does not need to do first: repair, clean out, prepare for showings, or have a perfect decision.",
            ],
            truth_risk_notes=list(offer.truth_risk_notes),
            template_variables=["recipient_name", "property_address", "martin_phone"],
        )

    def build_sms_asset(self, *, offer: OfferAsset, segment: CopySegment) -> CopyAsset:
        copy_hinge = "I can tell you whether a simple as-is option is worth discussing."
        return CopyAsset(
            id=f"{offer.id}-{segment.value}-sms-1",
            offer_id=offer.id,
            asset_type=CopyAssetType.SMS,
            channel=CopyChannel.TEXTGRID,
            source_lane=offer.source_lane,
            segment=segment,
            framework=CopyFramework.SULTANIC_PAIN_FIRST,
            awareness_level=AwarenessLevel.PROBLEM_AWARE,
            copy_hinge=copy_hinge,
            offer_code_insights=list(offer.offer_code_insights),
            cta_gives="Permission to ask one quick question so Martin can give a useful as-is read.",
            body=(
                "Hi {{first_name}}, this is Martin. I’m reaching out about {{property_address}}. "
                f"{copy_hinge} Is it okay if I ask one quick question?"
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

    @staticmethod
    def _copy_hinge_for(offer: OfferAsset) -> str:
        return (
            "I’m Martin. If {{property_address}} is becoming one more inherited-property project, "
            f"this note is just to show you the {offer.name}: a low-pressure way to find out whether "
            "a simple as-is path is worth discussing without repairing, cleaning out, listing, or getting every document, tax question, and family decision perfect first."
        )
