from fastapi import Header, HTTPException, Query, status

from app.core.config import Settings, get_settings
from app.models.actors import ActorContext


def settings_dependency() -> Settings:
    return get_settings()


def runtime_api_key_dependency(
    authorization: str | None = Header(default=None),
    runtime_api_key: str | None = Query(default=None),
) -> Settings:
    settings = get_settings()
    expected = f"Bearer {settings.runtime_api_key}"
    if authorization != expected and runtime_api_key != settings.runtime_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return settings


def actor_context_dependency(
    x_ares_org_id: str | None = Header(default=None),
    x_ares_actor_id: str | None = Header(default=None),
    x_ares_actor_type: str | None = Header(default=None),
) -> ActorContext:
    settings = get_settings()
    return ActorContext(
        org_id=x_ares_org_id or settings.default_org_id,
        actor_id=x_ares_actor_id or settings.default_actor_id,
        actor_type=x_ares_actor_type or settings.default_actor_type,
    )
