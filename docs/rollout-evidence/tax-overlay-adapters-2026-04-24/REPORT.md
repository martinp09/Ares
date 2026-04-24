# Tax Overlay Adapter Implementation Smoke — 2026-04-24

## Result

Implemented the first Ares tax-overlay adapter slice for the four priority counties excluding Tarrant.

Covered in code:

- Harris tax statement parser/hardening
- Travis quick-search adapter/parser
- Dallas/Montgomery ACT Web detail parser scaffold

## Files

- `app/services/tax_overlay_service.py`
- `tests/services/test_tax_overlay_service.py`
- `docs/rollout-evidence/tax-overlay-adapters-2026-04-24/tax_overlay_adapter_smoke.json`

## Harris live smoke

Confirmed Harris statement parsing for the two current HCAD-matched leads.

### Tangie Renee Williams / Fallbrook

- Account: `1091100001181`
- Owner parsed: `WILLIAMS TANGIE`
- Property address parsed: `1407 GREEN TRAIL DR`
- Status: `tax_overlay_verified_current`
- Delinquent: `false`
- Amount owed: `$0.00`
- Tax value parsed from tax statement: `$214,867`
- Parser warnings: none

### Janet Marie Mcmahan

- Account: `1172610010016`
- Owner parsed: `MCMAHAN PATRICK K & JANET`
- Property address parsed: `5073 N NELSON AVE`
- Status: `tax_overlay_verified_current`
- Delinquent: `false`
- Amount owed: `$0.00`
- Tax value parsed from tax statement: `$320,544`
- Parser warnings: none

## Travis live smoke

Query:

```text
01150409100000
```

Parsed result:

- Account: `01150409100000`
- Owner: `BARRY ALEX T`
- Property address: `1901 VISTA LN`
- Amount shown in quick-search row: `$0.00`
- Status: `tax_overlay_soft_signal`
- Warning: quick search result still requires detail-page verification before final `verified_current` or `verified_delinquent` status.

## Dallas/Montgomery ACT Web

The parser scaffold is implemented and fixture-tested for the known ACT Web detail page shape:

```text
showdetail2.jsp?can=<account>&ownerno=0
```

Live Dallas/Montgomery access was not re-proven in this slice because the environment previously timed out against both ACT Web hosts. This code is ready for the first reachable HTML sample.

## State policy

The implementation keeps the hard rule:

> Do not set final `tax_delinquent=true` from soft or partial parser output.

Final delinquency requires `tax_overlay_verified_delinquent`.

Quick-search rows use `tax_overlay_soft_signal` until a detail page is parsed.
