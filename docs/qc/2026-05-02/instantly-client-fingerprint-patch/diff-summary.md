# Diff Summary

## `app/providers/instantly.py`
- Added `_DEFAULT_USER_AGENT = "Mozilla/5.0 Ares/1.0 InstantlyClient"`.
- Added `Accept: application/json` to the Instantly request headers.
- Added `User-Agent: Mozilla/5.0 Ares/1.0 InstantlyClient` to the Instantly request headers.

## `tests/providers/test_instantly.py`
- Extended `test_build_request_uses_bearer_auth` to assert `Accept`, `Content-Type`, and `User-Agent` headers.

## QC artifacts
- Added this QC packet under `docs/qc/2026-05-02/instantly-client-fingerprint-patch/`.
