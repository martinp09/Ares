import pytest

from app.domains.ares import AresSourceLane
from app.models.copy_offers import CopyAssetStatus, CopySegment, OfferAsset
from app.services.copy_offer_service import CopyOfferService


def test_harris_probate_offer_uses_hormozi_value_equation_and_review_gate() -> None:
    offer = CopyOfferService().build_harris_probate_offer(segment=CopySegment.HOT)

    assert offer.id == "harris-probate-inherited-property-exit-hot"
    assert offer.name == "Inherited Property Exit Option"
    assert offer.source_lane == AresSourceLane.PROBATE
    assert offer.segment == CopySegment.HOT
    assert offer.status == CopyAssetStatus.REVIEW_REQUIRED
    assert offer.auto_send is False
    assert "repairs" in " ".join(offer.effort_reducers).lower()
    assert "cleanup" in " ".join(offer.effort_reducers).lower()
    assert "legal" in " ".join(offer.constraints).lower()
    assert offer.offer_code_insights
    assert "without" in " ".join(offer.infusion_directives).lower()
    assert "perfect" in " ".join(offer.offer_code_insights).lower()
    summary = offer.hormozi_value_equation_summary()
    assert summary["dream_outcome"] == offer.dream_outcome
    assert summary["perceived_likelihood"]
    assert summary["time_delay"]
    assert summary["effort_and_sacrifice"]


def test_offer_assets_cannot_auto_send() -> None:
    with pytest.raises(ValueError, match="cannot auto-send"):
        OfferAsset(
            id="bad",
            name="Bad",
            source_lane=AresSourceLane.PROBATE,
            audience="seller",
            pain_points=["pain"],
            dream_outcome="outcome",
            likelihood_boosters=["proof"],
            time_delay_reducers=["fast"],
            effort_reducers=["easy"],
            unique_mechanism="mechanism",
            value_stack=["stack"],
            truth_risk_notes=["risk"],
            auto_send=True,
        )
