# Ares env contract for landing intake

Required for landing contact submit:

- `RUNTIME_API_KEY`: must match landing `BUSINESS_RUNTIME_API_KEY`.
- `CAL_BOOKING_URL`: booking link returned in `/marketing/leads` responses.
- `PROVIDER_LIVE_SENDS_ENABLED=false`: safe default; confirmation SMS/email/Trigger scheduling is skipped unless explicitly enabled.

Only set/use for approved live provider smoke/deploy:

- `TEXTGRID_ACCOUNT_SID`
- `TEXTGRID_AUTH_TOKEN`
- `TEXTGRID_FROM_NUMBER`
- `TEXTGRID_STATUS_CALLBACK_URL=https://<ares-runtime>/marketing/webhooks/textgrid`
- Resend/Trigger provider keys as needed.

No live SMS/email sends were enabled or executed by this slice.
