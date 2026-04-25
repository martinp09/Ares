from __future__ import annotations

import json
import os
import sys
from urllib import parse
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


def _scope_query(business_id: str, environment: str) -> str:
    return parse.urlencode({"business_id": business_id, "environment": environment})


def _find_by_id(items: list[dict], item_id: str | None) -> dict | None:
    if not item_id:
        return None
    return next((item for item in items if item.get("id") == item_id), None)


def _assert_readiness_result(result: dict) -> None:
    failures: list[str] = []
    if result["health"].get("status") != "ok":
        failures.append("runtime health status is not ok")
    if not result["tools"]["has_run_market_research"]:
        failures.append("run_market_research tool is missing")
    if not result["command"]["run_id"]:
        failures.append("safe tool invocation did not return run_id")
    if result["run"]["id"] != result["command"]["run_id"]:
        failures.append("safe run lookup did not return invoked run")
    if not result["mission_control"]["safe_run_readback"]:
        failures.append("Mission Control safe run readback failed")

    approval = result.get("approval")
    if approval:
        if approval.get("approval_status") != "approved":
            failures.append("approval path did not approve")
        if not approval.get("run_id"):
            failures.append("approval path did not return run_id")
        if approval.get("run_status") is None:
            failures.append("approval run lookup did not return status")
        if not result["mission_control"]["approval_run_readback"]:
            failures.append("Mission Control approval run readback failed")

    if failures:
        raise SystemExit("; ".join(failures))


def _run_approval_path(base_url: str, api_key: str, *, business_id: str, environment: str) -> dict | None:
    if os.environ.get("ARES_SMOKE_APPROVAL_PATH") not in {"1", "true", "TRUE", "yes"}:
        return None

    approval_tool = os.environ.get("ARES_SMOKE_APPROVAL_TOOL", "publish_campaign")
    approval_invoke = _request(
        "POST",
        f"{base_url}/hermes/tools/{approval_tool}/invoke",
        api_key=api_key,
        payload={
            "business_id": business_id,
            "environment": environment,
            "idempotency_key": os.environ.get(
                "ARES_SMOKE_APPROVAL_IDEMPOTENCY_KEY",
                "hermes-runtime-adapter-approval-smoke",
            ),
            "payload": {
                "campaign_id": os.environ.get("ARES_SMOKE_CAMPAIGN_ID", "hermes-runtime-adapter-smoke"),
                "note": "runtime adapter approval smoke",
            },
        },
    )
    approval_id = approval_invoke.get("approval_id")
    if not approval_id:
        raise SystemExit(f"Approval smoke expected approval_id from {approval_tool}")

    approved = _request(
        "POST",
        f"{base_url}/approvals/{approval_id}/approve",
        api_key=api_key,
        payload={"actor_id": os.environ.get("ARES_SMOKE_ACTOR_ID", "hermes-operator")},
    )
    run_id = approved.get("run_id")
    run = _request("GET", f"{base_url}/runs/{run_id}", api_key=api_key) if run_id else None
    return {
        "tool": approval_tool,
        "command_id": approval_invoke.get("id"),
        "approval_id": approval_id,
        "approval_status": approved.get("status"),
        "run_id": run_id,
        "run_status": run.get("status") if run else None,
    }


def main() -> int:
    base_url = _env("HERMES_RUNTIME_API_BASE_URL", "RUNTIME_API_BASE_URL")
    api_key = os.environ.get("HERMES_RUNTIME_API_KEY") or os.environ.get("RUNTIME_API_KEY")
    if not api_key:
        raise SystemExit("Missing HERMES_RUNTIME_API_KEY or RUNTIME_API_KEY")

    business_id = os.environ.get("ARES_SMOKE_BUSINESS_ID", "limitless")
    environment = os.environ.get("ARES_SMOKE_ENVIRONMENT", "dev")

    health = _request("GET", f"{base_url}/health")
    tools = _request("GET", f"{base_url}/hermes/tools", api_key=api_key)
    invoke = _request(
        "POST",
        f"{base_url}/hermes/tools/run_market_research/invoke",
        api_key=api_key,
        payload={
            "business_id": business_id,
            "environment": environment,
            "idempotency_key": os.environ.get("ARES_SMOKE_IDEMPOTENCY_KEY", "hermes-runtime-adapter-smoke"),
            "payload": {"topic": os.environ.get("ARES_SMOKE_TOPIC", "houston tired landlords")},
        },
    )
    run_id = invoke.get("run_id")
    run = _request("GET", f"{base_url}/runs/{run_id}", api_key=api_key) if run_id else None
    approval = _run_approval_path(base_url, api_key, business_id=business_id, environment=environment)

    query = _scope_query(business_id, environment)
    dashboard = _request("GET", f"{base_url}/mission-control/dashboard?{query}", api_key=api_key)
    mission_control_runs = _request("GET", f"{base_url}/mission-control/runs?{query}", api_key=api_key)
    mission_control_approvals = _request("GET", f"{base_url}/mission-control/approvals?{query}", api_key=api_key)
    readback_safe_run = _find_by_id(mission_control_runs.get("runs", []), run_id)
    readback_approval_run = _find_by_id(
        mission_control_runs.get("runs", []),
        approval.get("run_id") if approval else None,
    )

    result = {
        "health": health,
        "tools": {
            "tool_count": len(tools.get("tools", [])),
            "has_run_market_research": any(tool.get("name") == "run_market_research" for tool in tools.get("tools", [])),
        },
        "command": {
            "id": invoke.get("id"),
            "run_id": run_id,
            "approval_id": invoke.get("approval_id"),
            "deduped": invoke.get("deduped"),
        },
        "run": {
            "id": run.get("id") if run else None,
            "status": run.get("status") if run else None,
            "trigger_run_id": run.get("trigger_run_id") if run else None,
        },
        "mission_control": {
            "active_run_count": dashboard.get("active_run_count"),
            "recent_completed_count": dashboard.get("recent_completed_count"),
            "run_count": len(mission_control_runs.get("runs", [])),
            "approval_count": len(mission_control_approvals.get("approvals", [])),
            "safe_run_readback": readback_safe_run is not None,
            "approval_run_readback": readback_approval_run is not None if approval else None,
        },
    }
    if approval:
        result["approval"] = approval

    _assert_readiness_result(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
