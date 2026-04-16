from typing import Literal

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_INTERNAL_ORG_ID = "org_internal"
DEFAULT_INTERNAL_ACTOR_ID = "ares-runtime"
DEFAULT_INTERNAL_ACTOR_TYPE = "service"


class Settings(BaseSettings):
    app_name: str = "Ares Runtime"
    runtime_api_key: str = "dev-runtime-key"
    default_org_id: str = DEFAULT_INTERNAL_ORG_ID
    default_actor_id: str = DEFAULT_INTERNAL_ACTOR_ID
    default_actor_type: Literal["user", "service", "system"] = DEFAULT_INTERNAL_ACTOR_TYPE
    control_plane_backend: Literal["memory", "supabase"] = "memory"
    marketing_backend: Literal["memory", "supabase"] = "memory"
    database_url: str | None = None
    site_events_backend: Literal["memory", "supabase"] = "supabase"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    cal_api_key: str | None = None
    cal_booking_url: str | None = None
    cal_webhook_secret: str | None = None
    trigger_secret_key: str | None = None
    trigger_api_url: str | None = None
    trigger_non_booker_check_task_id: str | None = None
    textgrid_base_url: str = "https://api.textgrid.com"
    textgrid_sms_url: str | None = None
    textgrid_webhook_secret: str | None = None
    textgrid_account_sid: str | None = None
    textgrid_auth_token: str | None = None
    textgrid_from_number: str | None = None
    resend_email_url: str = "https://api.resend.com/emails"
    resend_api_key: str | None = None
    resend_from_email: str | None = None
    resend_reply_to_email: str | None = None
    instantly_api_key: str | None = None
    instantly_base_url: str = "https://api.instantly.ai"
    instantly_webhook_secret: str | None = None
    instantly_batch_size: int = 100
    instantly_batch_wait_seconds: float = 0.25
    runtime_provider_default: Literal["anthropic", "openai_compat", "local"] = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    openai_compat_api_key: str | None = None
    openai_compat_base_url: str | None = None
    local_provider_enabled: bool = True
    provider_request_timeout_seconds: float = 10.0
    provider_request_max_retries: int = 2
    provider_retry_base_delay_seconds: float = 0.25
    provider_retry_max_delay_seconds: float = 2.0
    provider_tool_schema_max_bytes: int = 32768

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
