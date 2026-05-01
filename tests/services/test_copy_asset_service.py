import pytest

from app.models.copy_assets import CopyAsset, CopyAssetType, CopyChannel
from app.models.copy_offers import CopySegment
from app.services.copy_asset_service import CopyAssetService
from app.services.copy_offer_service import CopyOfferService


def test_copy_asset_service_builds_channel_specific_review_required_assets() -> None:
    offer = CopyOfferService().build_harris_probate_offer(segment=CopySegment.HOT)
    assets = CopyAssetService().build_harris_probate_assets(offer)

    assert {asset.asset_type for asset in assets} == {CopyAssetType.EMAIL, CopyAssetType.SMS, CopyAssetType.DIRECT_MAIL}
    assert {asset.channel for asset in assets} == {CopyChannel.INSTANTLY, CopyChannel.TEXTGRID, CopyChannel.DIRECT_MAIL}
    assert all(asset.offer_id == offer.id for asset in assets)
    assert all(asset.auto_send is False for asset in assets)
    assert all(asset.truth_risk_notes for asset in assets)
    email = next(asset for asset in assets if asset.asset_type == CopyAssetType.EMAIL)
    assert "Inherited property decisions can get messy" in email.body
    assert "simple buyer option" in email.body
    assert "first_name" in email.template_variables


def test_copy_assets_require_truth_notes_and_no_auto_send() -> None:
    with pytest.raises(ValueError):
        CopyAsset(
            id="bad",
            offer_id="offer",
            asset_type=CopyAssetType.EMAIL,
            channel=CopyChannel.INSTANTLY,
            source_lane="probate",
            segment=CopySegment.HOT,
            body="hi",
            truth_risk_notes=[],
        )
