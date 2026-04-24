from __future__ import annotations

import json
import os
import sys
from urllib import error, request


def _env(name: str, fallback: str | None = None) -> str:
    value = os.environ.get(name) or (os.environ.get(fallback) if fallback else None)
    if not value:
        raise SystemExit(f"Missing {name}" + (f" or {fallback}" if fallback else ""))
    return value.rstrip("/") if name.endswith("BASE_URL") else value


def _request(method: str, url: str, *, api_key: str | None = None, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise SystemExit(f"{method} {url} failed: {exc.code} {body}") from exc


def main() -> int:
    base_url = _env("HERMES_RUNTIME_API_BASE_URL", "RUNTIME_API_BASE_URL")
    api_key = os.environ.get("HERMES_RUNTIME_API_KEY") or os.environ.get("RUNTIME_API_KEY")
    if not api_key:
        raise SystemExit("Missing HERMES_RUNTIME_API_KEY or RUNTIME_API_KEY")

    health = _request("GET", f"{base_url}/health")
    tools = _request("GET", f"{base_url}/hermes/tools", api_key=api_key)
    invoke = _request(
        "POST",
        f"{base_url}/hermes/tools/run_market_research/invoke",
        api_key=api_key,
        payload={
            "business_id": os.environ.get("ARES_SMOKE_BUSINESS_ID", "limitless"),
            "environment": os.environ.get("ARES_SMOKE_ENVIRONMENT", "dev"),
            "idempotency_key": os.environ.get("ARES_SMOKE_IDEMPOTENCY_KEY", "hermes-runtime-adapter-smoke"),
            "payload": {"topic": os.environ.get("ARES_SMOKE_TOPIC", "houston tired landlords")},
        },
    )

    print(
        json.dumps(
            {
                "health": health,
                "tool_count": len(tools.get("tools", [])),
                "command_id": invoke.get("id"),
                "run_id": invoke.get("run_id"),
                "approval_id": invoke.get("approval_id"),
                "deduped": invoke.get("deduped"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
