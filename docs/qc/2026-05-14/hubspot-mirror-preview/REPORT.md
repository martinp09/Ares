# HubSpot Mirror Preview QC

## Scope

Implemented Phase 1 of `docs/superpowers/plans/2026-05-14-hubspot-operating-spine-agentic-company-plan.md` for HubSpot provider adapter and dry-run mirror previews only, applied review-blocker fixes for safe error handling, score mapping, and explicit non-implementation of live apply, then completed the final Phase 1 provider-header security pass.

## What changed

- Hardened `HubSpotClient` provider error handling:
  - Unexpected transport exceptions are wrapped with bounded sanitized messages using provider + method/path + exception type only.
  - Default `HTTPError` handling reports provider + method/path + status only.
  - Raised error messages do not echo access tokens, Authorization headers, or raw provider response bodies.
  - `ProviderTransportError.headers` is now sanitized before re-raise: sensitive/raw provider headers are dropped, while safe retry metadata (`Retry-After`, `X-RateLimit-*`) is preserved for retry behavior.
  - Injected `ProviderTransportError` instances are no longer trusted as pre-sanitized; they are re-wrapped with sanitized message, status, and headers.
- Fixed HubSpot deal score mapping so valid `lead_score=0` is preserved instead of falling back to `data_quality_score`.
- Made `dry_run=false` explicit and safe for Phase 1:
  - Existing live-write gate and token checks still run first.
  - After those checks pass, Phase 1 rejects live apply with `HubSpot live apply is not implemented in Phase 1; use dry_run=true.`
  - No provider call is made for preview/live-apply rejection paths.
- Added/updated provider, service, and API tests for these review blockers.

## Safety result

- No live HubSpot API calls were made.
- No HubSpot provider write path is called by preview endpoints.
- Raw provider/proxy response headers such as `Authorization`, bearer/token values, cookies, and content headers are not retained on HubSpot `ProviderTransportError.headers`.
- Safe retry headers remain available so retry/backoff behavior still works.
- Dry-run defaults to `true` and does not require `HUBSPOT_ACCESS_TOKEN`.
- `dry_run=false` fails before provider calls when live writes are disabled or the access token is missing.
- `dry_run=false` also fails safely after gate/token checks because live apply remains intentionally unimplemented in Phase 1.

## Test results

- Runtime config contract regression check: `1 passed`.
- Focused final HubSpot security pass: `19 passed`.
- Full backend suite: `639 passed`.

See `test-output.txt` for captured command output.

## Risks / follow-up

- Live HubSpot customization apply and record mutation remain intentionally unimplemented for Phase 1.
- Provider object links/sync cursors are still Phase 2.
- Pipeline/stage IDs in preview are deterministic placeholders until a live apply phase stores HubSpot-generated IDs.
