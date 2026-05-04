# Instantly Plan / HTTP 402 Research

## First-party sources checked

- `https://developer.instantly.ai/getting-started/getting-started.md`
- `https://developer.instantly.ai/getting-started/authorization.md`
- `https://api.instantly.ai/openapi/api_v2.json`
- `https://instantly.ai/pricing`

## Findings

- Instantly API v2 uses bearer-token auth.
- API keys are created under `Settings > Integrations > API Keys`, and each key has selected scopes.
- The OpenAPI spec documents `402` on many API endpoints as: `This request cannot be fulfilled because the workspace does not have an active paid plan`.
- The current OpenAPI spec has 165 endpoints with that `402` paid-plan response.
- Pricing page Outreach tab lists:
  - Growth: `$47/monthly`
  - Hypergrowth: `$97/monthly`
  - Light Speed: `$358/monthly`
  - Enterprise: custom
- Pricing comparison visibly includes `API, webhooks, and integrations` for Outreach plans.
- The pricing page also has an `Instantly Credits` tab; paid credits/lead-finder products appear separate from Outreach campaign/warmup plans.

## Live key diagnostics

Safe read-only calls with the newly supplied key returned the same `402` response for:

- `GET /api/v2/workspaces/current`
- `GET /api/v2/workspace-billing/plan-details`
- `GET /api/v2/workspace-billing/subscription-details`
- `GET /api/v2/api-keys`
- `GET /api/v2/campaigns?limit=1`

This means the API is rejecting the workspace before campaign reads/writes. It does not look like a missing scope problem; missing scopes would be expected to fail differently than the documented paid-plan `402`.

## Likely causes to verify in UI

1. The key was created in a different workspace than the paid workspace.
2. The paid subscription is for Instantly Credits / Lead Finder / another product, not the Outreach workspace required for campaigns/API.
3. Billing is paid but the workspace subscription is inactive/cancelled/trial/not fully activated in Instantly's backend.
4. Less likely: Instantly has a support-side billing state mismatch and needs to refresh/fix the workspace plan.
