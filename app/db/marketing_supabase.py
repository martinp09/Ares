from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, parse, request

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class MarketingTenant:
    business_pk: int
    environment: str


def marketing_backend_enabled(settings: Settings | None = None) -> bool:
    active = settings or get_settings()
    return active.marketing_backend == "supabase"


def _headers(settings: Settings, *, prefer: str | None = None) -> dict[str, str]:
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for marketing persistence")
    headers = {
        "Content-Type": "application/json",
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _endpoint(table: str, settings: Settings) -> str:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required for marketing persistence")
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{table}"


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
) -> MarketingTenant:
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
    return MarketingTenant(business_pk=int(row["business_id"]), environment=str(row["environment"]))
