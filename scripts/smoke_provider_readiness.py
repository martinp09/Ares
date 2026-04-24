from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.providers.resend import build_send_email_request
from app.providers.textgrid import build_outbound_sms_request


def provider_readiness(*, allow_live: bool = False) -> dict[str, Any]:
    sms_opted_in = os.environ.get("ARES_SMOKE_SEND_SMS") == "1"
    email_opted_in = os.environ.get("ARES_SMOKE_SEND_EMAIL") == "1"
    if (sms_opted_in or email_opted_in) and not allow_live:
        raise RuntimeError("Live provider flags are set; rerun with --allow-live to acknowledge live smoke intent.")

    sms_request = build_outbound_sms_request(
        account_sid=os.environ.get("TEXTGRID_ACCOUNT_SID", "acct_smoke"),
        auth_token=os.environ.get("TEXTGRID_AUTH_TOKEN", "token_smoke"),
        from_number=os.environ.get("TEXTGRID_FROM_NUMBER", "+15550000000"),
        to_number=os.environ.get("ARES_SMOKE_TO_PHONE", "+15551112222"),
        body="Ares provider readiness smoke",
        status_callback_url=os.environ.get("TEXTGRID_STATUS_CALLBACK_URL", "https://runtime.example.com/marketing/webhooks/textgrid"),
    )
    email_request = build_send_email_request(
        api_key=os.environ.get("RESEND_API_KEY", "re_smoke"),
        from_email=os.environ.get("RESEND_FROM_EMAIL", "smoke@example.com"),
        to_email=os.environ.get("ARES_SMOKE_TO_EMAIL", "operator@example.com"),
        subject="Ares provider readiness smoke",
        text_body="Provider readiness shape only.",
    )

    return {
        "live_sms_requested": sms_opted_in,
        "live_email_requested": email_opted_in,
        "textgrid": {
            "endpoint": sms_request["endpoint"],
            "has_authorization": bool(sms_request["headers"].get("Authorization")),
            "payload_keys": sorted(sms_request["payload"].keys()),
            "to": sms_request["payload"]["To"],
            "status_callback": sms_request["payload"].get("StatusCallback"),
        },
        "resend": {
            "endpoint": email_request["endpoint"],
            "has_authorization": bool(email_request["headers"].get("Authorization")),
            "payload_keys": sorted(email_request["payload"].keys()),
            "to": email_request["payload"]["to"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(provider_readiness(allow_live=args.allow_live), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
