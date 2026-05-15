# Ares Buy-Box Filters

Last updated: 2026-05-02

## Operator doctrine

Ownership/title friction is useful, but Ares should not score every broken-title property as equally desirable. The property type, value band, and strategy lane matter.

## Hard excludes

- Mobile homes / manufactured-home-only records are **no-go** for the current acquisitions workflow.
- Exclude HCAD classes beginning with `M` unless explicitly overridden for a future mobile-home strategy.
- Also exclude records whose legal description indicates mobile/manufactured/trailer inventory, including clues like `HUD#`, `SERIAL#`, `TRLR`, `TRAILER`, `REDMAN`, `OAKWOOD`, or similar manufactured-home language.

## Primary acquisition buy box

- Single-family residential up to 4 units.
- Prefer HCAD residential classes that map to houses/duplex/triplex/fourplex where available.
- Commercial/non-core classes are not deleted automatically; keep them in a review lane for now.

## Value-band strategy

For curative-title / tax-friction acquisition, high value is not automatically better.

- Core sweet spot: roughly **$150k to local county median home price**.
- Current market anchors from search snippets on 2026-05-02:
  - Harris County: Redfin snippet showed January 2026 median sale price around **$310k**; Zillow snippet showed average home value around **$281k**.
  - Montgomery County: Redfin snippet showed January 2026 median sale price around **$332k**; Zillow snippet showed average home value around **$342k**.
- Working scoring bands until replaced by a live market-data adapter:
  - Harris tax/title core band: **$150k–$310k**.
  - Montgomery tax/title core band: **$150k–$335k**.

## Lower and higher values

- Below $150k can still work, but should require deeper discount, simpler title path, or stronger urgency.
- $500k+ properties are not disqualified, but route more naturally to longer-cycle/creative-finance strategy lanes:
  - seller finance;
  - lease option;
  - subject-to;
  - notes;
  - relationship-first acquisition.

## Routing states

Use these labels in lead artifacts and future scoring:

- `buy_box_core_tax_title`: SFR/1–4 unit, non-mobile, $150k to county median, tax/title friction present.
- `buy_box_lower_value_requires_discount`: non-mobile but below $150k.
- `buy_box_high_value_creative_finance`: non-mobile but $500k+; route to longer-cycle creative acquisition posture.
- `buy_box_commercial_review`: commercial/non-core; keep for manual review, do not purge by default.
- `buy_box_mobile_home_no_go`: manufactured/mobile-home record; purge from active acquisition/call queues.

## 2026-05-02 call-list purge

Source call list:

`/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/today_heir_call_list_2026-05-02.csv`

Active no-mobile list:

`/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/today_heir_call_list_no_mobile_2026-05-02.csv`

Purged mobile-home list:

`/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/purged_mobile_home_leads_2026-05-02.csv`

Purged cases:

- `lead_491` / case `543469` — GUADALUPE G. RODRIGUEZ — HCAD class `M3` — 1972 Redman/New Moon manufactured-home record.
- `lead_492` / case `543577` — DAVID R. SOTO — HCAD class `M3` — 1997 Oakwood manufactured-home record.
- `lead_494` / case `543367` — ANGEL E. LARA — HCAD class `M3` — 1981 Fairway manufactured-home record.

## 2026-05-02 broader 464-row HCAD mobile screen

Artifacts:

- All HCAD owner-name candidates: `/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/hcad_name_match_candidates_all_464_2026-05-02.csv`
- Categorized mobile candidates: `/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/mobile_home_purge_candidates_all_464_categorized_2026-05-02.csv`
- Summary: `/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/mobile_home_purge_categorized_summary_2026-05-02.json`
- Confirmed-mobile-purged active set: `/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/hot_warm_ranked_enriched_confirmed_mobile_purged_2026-05-02.csv`
- Confirmed + high-confidence mobile screened set: `/opt/ares/lead-data/harris_probate_2026-04-28_30d_daily_raw/hot_warm_ranked_enriched_confirmed_plus_high_confidence_mobile_screened_2026-05-02.csv`

Result:

- 464 keep-now leads screened by conservative HCAD owner-name matching.
- 344 cases had at least one owner-name HCAD candidate.
- 32 cases had at least one HCAD `M*` mobile/manufactured-home candidate.
- 3 cases were confirmed mobile from the verified 15-title-packet HCAD layer and should stay purged.
- 5 additional cases had high-confidence mobile owner-name matches, but should be treated as `review_before_destructive_purge` unless property identity is independently confirmed.
- 24 cases were weak/common-name mobile candidate matches and should only be used as review warnings, not automatic purge decisions.
