# TextGrid Live Smoke After Funding — 2026-05-10

## Scope

One explicitly approved TextGrid SMS test to Martin's owned phone after Martin said funds were added.

## Routes hit

- `GET /mission-control/providers/status`
- `POST /mission-control/outbound/sms/test`

## Safety

- Used `/opt/ares/Ares/.env` in-process only.
- Did not copy or print raw secrets.
- Added `Authorization: Bearer <RUNTIME_API_KEY>` in-process for the protected Mission Control routes.
- Set `PROVIDER_LIVE_SENDS_ENABLED=true` only for this local smoke process.
- Sent one SMS to the already-approved operator-owned number `+1***5914`.

## Result

- Provider status route: `200`
- TextGrid configured: `true`
- TextGrid can_send: `true`
- SMS test route: `201`
- SMS provider result: `queued`
- Error: `null`
- From: `+1***1390`
- To: `+1***5914`
- Provider message id: masked in artifact

## Interpretation

The previous TextGrid funding blocker cleared. Ares reached TextGrid through the Mission Control route and TextGrid accepted the outbound request as queued. This proves provider routing/funding for this local route smoke; it does not prove final handset delivery until Martin confirms receipt or a TextGrid delivery callback/status is checked.

## Remaining activation blockers from the follow-up sanitized readiness run

- `PROVIDER_LIVE_SENDS_ENABLED=false` remains the safe default in the env file.
- `RESEND_FROM_EMAIL` is still not a valid sender identity.
- Slack token/channel are still missing, intentionally optional for now.
- `CAL_WEBHOOK_SECRET` is still missing.
