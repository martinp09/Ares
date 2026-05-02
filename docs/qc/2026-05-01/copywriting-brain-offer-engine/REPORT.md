# QC Report — Copywriting Brain Offer Engine Slice

## Scope

Started executing the Ares copywriting brain plan with a research-backed, offer-first slice focused on Alex Hormozi offer architecture and Alen Sultanic pain-first copy patterns.

## Changes

- Initialized repo-local LLM Wiki at `docs/copywriting-wiki/`.
- Added raw source/access notes for:
  - Acquisition.com offer/value-equation page.
  - Nothing Held Back homepage.
  - Strategic Profits Alen Sultanic profile.
  - blocked YouTube transcript access for Alen Sultanic masterclass.
  - existing Ares Harris probate campaign copy.
- Added wiki entity/concept/example pages for:
  - Hormozi offer architecture.
  - Sultanic pain-first copy, with source limitations flagged.
  - value equation.
  - inherited-property offer architecture.
  - mechanism-based offer.
  - Harris probate seller psychology.
  - probate email/direct-mail/SMS examples.
- Added typed offer/copy models:
  - `app/models/copy_offers.py`
  - `app/models/copy_assets.py`
- Added services:
  - `app/services/copy_offer_service.py`
  - `app/services/copy_asset_service.py`
- Upgraded `AresCopyService` to use the new `Inherited Property Exit Option` and channel-specific pain-first copy instead of generic outreach text.
- Added focused service tests.

## Research limitations

- Acquisition.com was accessible and confirms the public offer-course topic map and disclaimers.
- Nothing Held Back and Strategic Profits were accessible for NHB/Sultanic positioning.
- The detailed Alen Sultanic masterclass transcript was blocked by YouTube/cloud IP and transcript mirror Cloudflare challenge. Wiki pages explicitly flag detailed Sultanic tactics as interpretation/secondhand until a transcript or stronger primary source is captured.

## Safety

- No live Instantly/TextGrid/direct-mail provider actions were run.
- New offer and copy assets default to `review_required`.
- New models reject `auto_send=True`.
- Truth/risk notes are required.
- Copy explicitly avoids legal/tax/probate advice and guaranteed purchase/closing/title/tax outcomes.

## Verification

- `uv run pytest tests/services/test_copy_offer_service.py tests/services/test_copy_asset_service.py tests/services/test_ares_copy_service.py -q` — PASS, 6 tests.
- `python3 -m compileall app/models/copy_offers.py app/models/copy_assets.py app/services/copy_offer_service.py app/services/copy_asset_service.py app/services/ares_copy_service.py` — PASS.
- `git diff --check` — PASS.
- Wiki presence check — PASS: 20 markdown files, 5 raw files, required pages present.

## 2026-05-02 addendum — Copy Hinge + offer-first correction

Martin supplied an Alen Sultanic NHB post on the Copy Hinge and corrected the workflow: the core offer must be proposed before campaign copy. Added:

- `docs/copywriting-wiki/raw/transcripts/alen-sultanic-copy-hinge-nhb-2026-05-02.md`
- `docs/copywriting-wiki/concepts/copy-hinge.md`
- `docs/marketing/copy/2026-05-02-core-seller-offer-proposal.md`
- `CopyAsset.copy_hinge`
- early copy-hinge insertion in email/direct-mail/SMS asset generation.

Verification after addendum:

- `uv run pytest tests/services/test_copy_offer_service.py tests/services/test_copy_asset_service.py tests/services/test_ares_copy_service.py -q` — PASS, 6 tests.
- `python3 -m compileall app/models/copy_assets.py app/services/copy_asset_service.py app/services/ares_copy_service.py` — PASS.
- `git diff --check` — PASS.

## 2026-05-02 addendum — High-response email formula + offer-code Rosetta Stone

Martin supplied two additional Alen Sultanic excerpts:

1. High-response email formula: `Recency + Relevance + Personalization = Response`.
2. Offer-code / Rosetta Stone method: find the hidden code in the part of the offer that is working, then infuse that code across the full funnel.

Added:

- `docs/copywriting-wiki/raw/transcripts/alen-sultanic-high-response-email-formula-2026-05-02.md`
- `docs/copywriting-wiki/concepts/high-response-email-formula.md`
- `docs/copywriting-wiki/raw/transcripts/alen-sultanic-offer-code-rosetta-stone-2026-05-02.md`
- `docs/copywriting-wiki/concepts/offer-code-rosetta-stone.md`
- `CopyAsset.recency_signal`, `relevance_signal`, and `personalization_signal`.
- `CopyAsset.cta_gives` for the “CTA gives them something” rule.
- `OfferAsset.offer_code_insights` and `OfferAsset.infusion_directives` for Rosetta Stone extraction/propagation.
- Email copy now sells the quick as-is review mechanism/outcome instead of directly pitching a cash-buyer product.
- Copy hinge now repeats the extracted Ares offer code: without repairs, cleaning out, listing, perfect documents, tax answers, or family alignment first.

Verification after addendum:

- `uv run pytest tests/services/test_copy_offer_service.py tests/services/test_copy_asset_service.py tests/services/test_ares_copy_service.py tests/test_package_layout.py -q` — PASS, 15 tests.

## Follow-up

1. Get Martin's decision on the proposed core offer name/promise before writing a full campaign packet.
2. Capture stronger primary Sultanic source material via authenticated browser, alternate transcript source, or manual source upload.
3. Add Mission Control read/approval endpoints for offers and copy assets.
4. Persist offer/copy assets in a repository instead of service-generated constants.
5. Connect performance events back into wiki/copy asset reports after actual approved campaigns run.
