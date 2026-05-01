# Diff Summary — Copywriting Brain Offer Engine

## Added

- `app/models/copy_offers.py` — typed `OfferAsset`, `CopySegment`, `CopyAssetStatus`, review-gated offer model.
- `app/models/copy_assets.py` — typed `CopyAsset` with channel, framework, awareness, truth/risk notes, no-auto-send gate.
- `app/services/copy_offer_service.py` — Harris probate `Inherited Property Exit Option` builder using value-equation fields.
- `app/services/copy_asset_service.py` — channel-specific email/direct-mail/SMS copy asset generation.
- `tests/services/test_copy_offer_service.py` — offer model/service tests.
- `tests/services/test_copy_asset_service.py` — copy asset model/service tests.
- `docs/copywriting-wiki/` — repo-local LLM Wiki with schema, index, log, raw notes, entity/concept/example pages.
- `docs/qc/2026-05-01/copywriting-brain-offer-engine/` — QC evidence.

## Modified

- `app/services/ares_copy_service.py` — now builds briefs/drafts from offer and copy asset services instead of generic text.
- `tests/services/test_ares_copy_service.py` — asserts the stronger offer-first, pain-first copy and approval gate.
- `CONTEXT.md`, `TODO.md`, `memory.md` — living-doc updates for this slice.

## Not touched

- No Instantly/TextGrid/direct-mail provider enrollment.
- No Mission Control frontend.
- No Supabase migrations.
- No Obsidian installation/sync configuration.
