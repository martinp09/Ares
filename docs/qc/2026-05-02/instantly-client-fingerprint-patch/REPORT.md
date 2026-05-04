# Instantly Client Fingerprint Patch — QC Report

## Scope
- Patched `app/providers/instantly.py` so all Instantly API requests include a non-urllib client fingerprint:
  - `Accept: application/json`
  - `User-Agent: Mozilla/5.0 Ares/1.0 InstantlyClient`
- Updated provider unit coverage in `tests/providers/test_instantly.py` to assert the headers are present.

## Why
The current host could reach Instantly with the configured API key when a normal `User-Agent` was supplied, but Cloudflare returned HTTP 403 / `error code: 1010` for the default Python urllib fingerprint.

## Verification
- Focused unit tests passed: `uv run pytest tests/providers/test_instantly.py tests/services/test_instantly_client_rate_limit.py -q`
- Live Instantly preflight via patched `InstantlyClient.list_campaigns(limit=1)` returned `{'ok': True, 'item_count': 0, 'keys': ['items']}`.

## Safety
- No campaign creation, lead upload, send, activation, or provider mutation was performed.
- Instantly token value was loaded only from `.env` for preflight and was not printed or stored.

## Result
Patch is applied and verified. The Ares Instantly client can now list campaigns from this host with the existing API token.
