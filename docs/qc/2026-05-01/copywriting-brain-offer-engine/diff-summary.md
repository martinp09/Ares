# Diff Summary — Copywriting Brain Offer Engine

## Backend models

- `app/models/copy_offers.py`
  - Added `offer_code_insights` and `infusion_directives` so the offer can carry Rosetta Stone / hidden-code findings, not only Hormozi value-equation fields.

- `app/models/copy_assets.py`
  - Added `recency_signal`, `relevance_signal`, and `personalization_signal` for Alen Sultanic's high-response email formula.
  - Added `offer_code_insights` and `cta_gives` so copy assets expose which offer-code directives are infused and what the CTA gives the seller.

## Backend services

- `app/services/copy_offer_service.py`
  - Added Harris probate offer-code insights: without repairs/cleanout/listing prep/perfect paperwork, busy-life empathy, imperfect-decision permission, and edge-case repetition.
  - Added infusion directives for using more “without” language, selling the mechanism/outcome, preserving optionality, and making CTAs give clarity.

- `app/services/copy_asset_service.py`
  - Email assets now explicitly carry recency/relevance/personalization signals.
  - Email copy now sells the quick as-is review mechanism/outcome instead of a direct cash-buyer pitch.
  - Email CTA gives a quick read on whether the as-is option is worth discussing.
  - Direct mail and SMS now inherit offer-code insights and CTA-gives metadata.
  - Copy hinge now repeats the Rosetta Stone “without” code: without repairs, cleaning out, listing, perfect documents, tax answers, or family alignment first.

## Wiki / source notes

- Added `docs/copywriting-wiki/concepts/high-response-email-formula.md`.
- Added `docs/copywriting-wiki/raw/transcripts/alen-sultanic-high-response-email-formula-2026-05-02.md`.
- Added `docs/copywriting-wiki/concepts/offer-code-rosetta-stone.md`.
- Added `docs/copywriting-wiki/raw/transcripts/alen-sultanic-offer-code-rosetta-stone-2026-05-02.md`.
- Updated `docs/copywriting-wiki/index.md` and `docs/copywriting-wiki/log.md`.

## Tests

- `tests/services/test_copy_offer_service.py`
  - Asserts offer-code insights and infusion directives are present.

- `tests/services/test_copy_asset_service.py`
  - Asserts email assets include high-response formula fields, give-CTA metadata, offer-code insights, and mechanism/outcome copy.
