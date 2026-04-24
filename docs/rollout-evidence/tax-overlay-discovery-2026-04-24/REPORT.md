# Tax Overlay Discovery — 2026-04-24

## Answer

I found official tax search/payment portals for all five Phase-1 counties. We do **not** need user-provided links yet. The annoying part is not discovery; it is adapter behavior per county. Different portals, different little goblins.

## County portal matrix

| County | Official portal | Automation path | Current status |
|---|---|---|---|
| Harris | `https://www.hctax.net/Property/DelinquentTax` | tier_1_direct_json_api | working_from_python_requests |
| Tarrant | `https://www.tax.tarrantcountytx.gov/search` | tier_3_browser_or_manual_session_until_endpoint_discovered | official_site_found_but_cloudflare_challenge_in_current_cloud_browser_and_requests |
| Montgomery | `https://actweb.acttax.com/act_webdev/montgomery/index.jsp` | tier_2_html_form_scraper_after_connection_or_manual_session | official_site_found_via_duckduckgo; current environment timed out connecting to actweb.acttax.com |
| Dallas | `https://www.dallasact.com/act_webdev/dallas/index.jsp` | tier_2_html_form_scraper_after_connection_or_manual_session | official_site_found_via_duckduckgo; current environment timed out connecting to dallasact.com |
| Travis | `https://tax-office.traviscountytx.gov/properties/taxes/account-search` | tier_2_html_form_scraper | working_from_python_requests; HTML response parse required |

## Details

### Harris

- Portal: `https://www.hctax.net/Property/DelinquentTax`
- Direct endpoint: `POST /Property/Actions/DelAccountsList`
- Detail flow: `/Property/AccountEncrypt?account=...` then `/Property/TaxStatement?account=<encrypted>`
- Status: direct API path already exists in `/home/workspace/HCAD_Query/hctax_client.py`.
- Gap: parser hardening. Recent tax statement pages gave bad owner/value fields, so final overlay must not trust weak parse output.

### Tarrant

- Portal: `https://www.tax.tarrantcountytx.gov/search`
- Also resolves as: `https://www.tax.tarrantcountytx.gov/Search/Index`
- Status: official site found, but current cloud browser/requests hit Cloudflare challenge.
- Likely path: browser/manual session or endpoint discovery from devtools; do not bypass protections.

### Montgomery

- Portal: `https://actweb.acttax.com/act_webdev/montgomery/index.jsp`
- Direct detail shape seen in indexed results: `showdetail2.jsp?can=<account>&ownerno=0`
- Status: official ACT Web portal found; current environment timed out connecting.
- Likely path: ACT JSP HTML form scraper once reachable.

### Dallas

- Portal: `https://www.dallasact.com/act_webdev/dallas/index.jsp`
- Account search: `https://www.dallasact.com/act_webdev/dallas/searchbyaccount.jsp`
- Property search: `https://www.dallasact.com/act_webdev/dallas/searchbyproperty.jsp`
- Direct detail shape seen in indexed results: `showdetail2.jsp?can=<account>&ownerno=0`
- Status: official ACT Web portal found; current environment timed out connecting.
- Likely path: same adapter family as Montgomery.

### Travis

- Official landing page: `https://tax-office.traviscountytx.gov/properties/taxes/account-search`
- Search app: `https://travis.go2gov.net/cart/responsive/search.do`
- Working POST path: `POST /cart/responsive/quickSearch.do`
- Required form fields:
  - `formViewMode=responsive`
  - `criteria.searchStatus=1`
  - `pager.pageSize=10`
  - `pager.pageNumber=1`
  - `criteria.heuristicSearch=<name/address/account>`
- Status: accessible from Python requests; needs HTML results/detail parser.

## Ares tax overlay contract

Input priority:

1. owner name
2. property address
3. HCAD/CAD/tax account
4. candidate names as fallback/disambiguation

Lookup order:

1. owner-name search first
2. property-address search
3. exact account-number lookup
4. manual/browser fallback

Output fields Ares should store:

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

## Build order

1. Harden Harris parser first because Harris already has the working direct API and live target accounts.
2. Build Travis adapter second because the form POST path is accessible without a browser.
3. Build one ACT adapter for Dallas/Montgomery once connectivity is solved.
4. Treat Tarrant as browser/manual-session discovery until the Cloudflare wall is resolved.

## Hard rule

Do **not** set `tax_delinquent=true` in Ares from soft/partial parser output. Store `tax_overlay_status=unknown` or `soft_no_delinquency_signal` until high-confidence source parsing exists.

## Output files

- `docs/rollout-evidence/tax-overlay-discovery-2026-04-24/tax_overlay_portal_matrix.json`
- `docs/rollout-evidence/tax-overlay-discovery-2026-04-24/REPORT.md`
