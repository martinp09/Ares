from typing import Literal

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hermes Central Command Runtime"
    runtime_api_key: str = "dev-runtime-key"
    control_plane_backend: Literal["memory", "supabase"] = "memory"
    database_url: str | None = None
    site_events_backend: Literal["memory", "supabase"] = "supabase"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    textgrid_base_url: str = "https://api.textgrid.com"
    textgrid_sms_url: str | None = None
    textgrid_account_sid: str | None = None
    textgrid_auth_token: str | None = None
    textgrid_from_number: str | None = None
    resend_email_url: str = "https://api.resend.com/emails"
    resend_api_key: str | None = None
    resend_from_email: str | None = None
    resend_reply_to_email: str | None = None
    provider_request_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
