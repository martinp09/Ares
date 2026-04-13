from fastapi import Header, HTTPException, status

from app.core.config import Settings, get_settings


def settings_dependency() -> Settings:
    return get_settings()


def runtime_api_key_dependency(authorization: str | None = Header(default=None)) -> Settings:
    settings = get_settings()
    expected = f"Bearer {settings.runtime_api_key}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return settings
