from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import parse, request

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class LeadMachineTenant:
    business_pk: int
    environment: str


def lead_machine_backend_enabled(settings: Settings | None = None) -> bool:
    active = settings or get_settings()
    return active.lead_machine_backend == "supabase"


def _supabase_url(settings: Settings) -> str:
    value = settings.lead_machine_supabase_url or settings.supabase_url
    if not value:
        raise RuntimeError("SUPABASE_URL is required for lead-machine persistence")
    return value.rstrip("/")


def _service_role_key(settings: Settings) -> str:
    value = settings.lead_machine_supabase_service_role_key or settings.supabase_service_role_key
    if not value:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for lead-machine persistence")
    return value


def _headers(settings: Settings, *, prefer: str | None = None) -> dict[str, str]:
    service_role_key = _service_role_key(settings)
    headers = {
        "Content-Type": "application/json",
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _endpoint(table: str, settings: Settings) -> str:
    return f"{_supabase_url(settings)}/rest/v1/{table}"


def fetch_rows(
    table: str,
    *,
    params: dict[str, str],
    settings: Settings | None = None,
) -> list[dict]:
    active = settings or get_settings()
    query = parse.urlencode(params)
    req = request.Request(
        f"{_endpoint(table, active)}?{query}",
        headers=_headers(active),
        method="GET",
    )
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def insert_rows(
    table: str,
    rows: list[dict],
    *,
    select: str | None = None,
    prefer: str = "return=representation",
    settings: Settings | None = None,
) -> list[dict]:
    active = settings or get_settings()
    suffix = f"?select={parse.quote(select, safe=',*')}" if select else ""
    req = request.Request(
        f"{_endpoint(table, active)}{suffix}",
        data=json.dumps(rows).encode("utf-8"),
        headers=_headers(active, prefer=prefer),
        method="POST",
    )
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def patch_rows(
    table: str,
    *,
    params: dict[str, str],
    row: dict,
    select: str | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    active = settings or get_settings()
    query = parse.urlencode(params)
    suffix = f"&select={parse.quote(select, safe=',*')}" if select else ""
    req = request.Request(
        f"{_endpoint(table, active)}?{query}{suffix}",
        data=json.dumps(row).encode("utf-8"),
        headers=_headers(active, prefer="return=representation"),
        method="PATCH",
    )
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_tenant(
    business_id: str,
    environment: str,
    *,
    settings: Settings | None = None,
) -> LeadMachineTenant:
    active = settings or get_settings()
    field = "business_id" if business_id.isdigit() else "slug"
    rows = fetch_rows(
        "businesses",
        params={
            "select": "business_id,environment",
            field: f"eq.{business_id}",
            "environment": f"eq.{environment}",
            "limit": "1",
        },
        settings=active,
    )
    if not rows:
        raise RuntimeError(f"No business found for {business_id}/{environment}")
    row = rows[0]
    return LeadMachineTenant(business_pk=int(row["business_id"]), environment=str(row["environment"]))


def external_id(prefix: str, row_id: int | str) -> str:
    return f"{prefix}_{row_id}"


def row_id_from_external_id(value: str | None, prefix: str) -> int | None:
    if not value:
        return None
    raw = str(value).strip()
    token = raw[len(prefix) + 1 :] if raw.startswith(f"{prefix}_") else raw
    return int(token) if token.isdigit() else None
