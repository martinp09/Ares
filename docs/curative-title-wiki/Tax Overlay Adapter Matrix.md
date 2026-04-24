---
title: Tax Overlay Adapter Matrix
status: active
updated_at: 2026-04-24
---

# Tax Overlay Adapter Matrix

Tax delinquency is an overlay signal, not the lead source center.

For curative title, the order stays:

1. identify property/person/title thread
2. match to CAD/appraisal/tax account
3. run tax overlay
4. only then adjust priority, pain stack, and outreach routing

## Five-county portal matrix

| County | Official portal | Adapter tier | Status |
|---|---|---|---|
| Harris | `https://www.hctax.net/Property/DelinquentTax` | direct JSON/API | Parser hardened and live-smoked on Tangie/McMahan accounts |
| Tarrant | `https://www.tax.tarrantcountytx.gov/search` | browser/manual-session discovery | Ignored for now; Cloudflare blocks current cloud/browser environment |
| Montgomery | `https://actweb.acttax.com/act_webdev/montgomery/index.jsp` | ACT JSP HTML scraper | ACT detail parser scaffolded; current environment timed out connecting |
| Dallas | `https://www.dallasact.com/act_webdev/dallas/index.jsp` | ACT JSP HTML scraper | ACT detail parser scaffolded; current environment timed out connecting |
| Travis | `https://tax-office.traviscountytx.gov/properties/taxes/account-search` + `https://travis.go2gov.net/cart/responsive/search.do` | HTML form scraper | Quick search adapter/parser implemented and live-smoked |

Source evidence:

- `docs/rollout-evidence/tax-overlay-discovery-2026-04-24/REPORT.md`
- `docs/rollout-evidence/tax-overlay-discovery-2026-04-24/tax_overlay_portal_matrix.json`
- `docs/rollout-evidence/tax-overlay-adapters-2026-04-24/REPORT.md`
- `docs/rollout-evidence/tax-overlay-adapters-2026-04-24/tax_overlay_adapter_smoke.json`

## Adapter tiers

### Tier 1 — direct JSON/API

Best case. No browser if endpoint behaves.

Current county:

- Harris

Harris endpoint:

```text
POST https://www.hctax.net/Property/Actions/DelAccountsList
```

Fields:

```text
colSearch = name | account | address
searchText = query
```

Detail flow:

```text
GET /Property/AccountEncrypt?account=<account>
GET /Property/TaxStatement?account=<encrypted>
```

### Tier 2 — HTML form scraper

Submit public search forms and parse result/detail HTML.

Current counties:

- Travis
- Dallas
- Montgomery

Travis working POST path:

```text
POST https://travis.go2gov.net/cart/responsive/quickSearch.do
```

Fields:

```text
formViewMode=responsive
criteria.searchStatus=1
pager.pageSize=10
pager.pageNumber=1
criteria.heuristicSearch=<name/address/account>
```

Dallas/Montgomery likely share the ACT Web JSP family:

```text
showdetail2.jsp?can=<account>&ownerno=0
```

### Tier 3 — browser/manual-session discovery

Use only when official site blocks direct requests or requires browser challenge handling.

Current county:

- Tarrant

Tarrant official portal supports account/owner/address/property-location search, but Cloudflare blocked the current environment. Do not bypass protections. Use a human/residential/manual session or endpoint discovery if available.

## Ares overlay contract

Input priority:

1. owner name
2. property address
3. CAD/tax account number
4. candidate names as fallback/disambiguation

Lookup order:

1. owner-name search first
2. property-address search
3. exact account-number lookup
4. manual/browser fallback

Output fields:

- county
- account
- `is_delinquent`
- amount owed
- current-year owed
- prior-years owed
- estimated years delinquent
- suit / attorney / collection clues
- homestead/exemption clues
- search method
- confidence
- raw source URL
- checked timestamp
- parser warnings

## Hard rule

Do **not** set `tax_delinquent=true` from soft/partial parser output.

Use explicit states:

- `tax_overlay_not_checked`
- `tax_overlay_soft_no_signal`
- `tax_overlay_soft_signal`
- `tax_overlay_verified_current`
- `tax_overlay_verified_delinquent`
- `tax_overlay_ambiguous`
- `tax_overlay_blocked`

## Build status

1. Harris parser hardened and live-smoked against confirmed Tangie/McMahan accounts.
2. Travis quick-search adapter/parser implemented and live-smoked.
3. Dallas/Montgomery ACT detail parser scaffolded and fixture-tested; live sites still need reachable samples.
4. Tarrant intentionally deferred.

## Build order

1. Harden Harris parser first.
2. Build Travis adapter second.
3. Build one ACT adapter family for Dallas/Montgomery.
4. Treat Tarrant as browser/manual-session discovery until Cloudflare is resolved.

## Cross-links

- [[HCAD Property Match Test]]
- [[Contact Candidate Packet Test]]
- [[Evidence Graph Data Model]]
