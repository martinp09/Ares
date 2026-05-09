from secrets import compare_digest

from fastapi import Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.models.actors import ActorContext


def settings_dependency() -> Settings:
    return get_settings()


def runtime_api_key_dependency(
    authorization: str | None = Header(default=None),
) -> Settings:
    settings = get_settings()
    if not settings.runtime_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Runtime API key is not configured",
        )
    expected = f"Bearer {settings.runtime_api_key}"
    if not compare_digest(authorization or "", expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return settings


def actor_context_dependency(
    x_ares_org_id: str | None = Header(default=None),
    x_ares_actor_id: str | None = Header(default=None),
    x_ares_actor_type: str | None = Header(default=None),
) -> ActorContext:
    settings = get_settings()
    if not settings.runtime_actor_header_overrides_enabled:
        return ActorContext(
            org_id=settings.default_org_id,
            actor_id=settings.default_actor_id,
            actor_type=settings.default_actor_type,
        )
    return ActorContext(
        org_id=x_ares_org_id or settings.default_org_id,
        actor_id=x_ares_actor_id or settings.default_actor_id,
        actor_type=x_ares_actor_type or settings.default_actor_type,
    )
