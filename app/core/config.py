from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
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
    marketplace_publish_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("marketplace_publish_enabled", "MARKETPLACE_PUBLISH_ENABLED"),
    )
    control_plane_backend: Literal["memory", "supabase"] = "memory"
    marketing_backend: Literal["memory", "supabase"] = "memory"
    lead_machine_backend: Literal["memory", "supabase"] = "memory"
    database_url: str | None = None
    site_events_backend: Literal["memory", "supabase"] = "memory"
    runtime_provider_default: Literal["anthropic", "openai_compat", "local"] = "anthropic"
    supabase_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("supabase_url", "SUPABASE_URL"),
    )
    supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "supabase_service_role_key",
            "SUPABASE_SERVICE_ROLE_KEY",
            "SUPABASE_SECRET_KEY",
        ),
    )
    lead_machine_supabase_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("lead_machine_supabase_url", "LEAD_MACHINE_SUPABASE_URL"),
    )
    lead_machine_supabase_service_role_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "lead_machine_supabase_service_role_key",
            "LEAD_MACHINE_SUPABASE_SERVICE_ROLE_KEY",
            "LEAD_MACHINE_SUPABASE_SECRET_KEY",
        ),
    )
    instantly_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("instantly_api_key", "INSTANTLY_API_KEY"),
    )
    instantly_webhook_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("instantly_webhook_secret", "INSTANTLY_WEBHOOK_SECRET"),
    )
    instantly_base_url: str = Field(
        default="https://api.instantly.ai",
        validation_alias=AliasChoices("instantly_base_url", "INSTANTLY_BASE_URL"),
    )
    instantly_batch_size: int = Field(
        default=100,
        validation_alias=AliasChoices("instantly_batch_size", "INSTANTLY_BATCH_SIZE"),
    )
    instantly_batch_wait_seconds: float = Field(
        default=0.25,
        validation_alias=AliasChoices("instantly_batch_wait_seconds", "INSTANTLY_BATCH_WAIT_SECONDS"),
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("anthropic_api_key", "ANTHROPIC_API_KEY"),
    )
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com",
        validation_alias=AliasChoices("anthropic_base_url", "ANTHROPIC_BASE_URL"),
    )
    openai_compat_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("openai_compat_api_key", "OPENAI_COMPAT_API_KEY"),
    )
    openai_compat_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("openai_compat_base_url", "OPENAI_COMPAT_BASE_URL"),
    )
    local_provider_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("local_provider_enabled", "LOCAL_PROVIDER_ENABLED"),
    )
    provider_request_max_retries: int = Field(
        default=2,
        validation_alias=AliasChoices("provider_request_max_retries", "PROVIDER_REQUEST_MAX_RETRIES"),
    )
    provider_request_timeout_seconds: float = Field(
        default=10.0,
        validation_alias=AliasChoices(
            "provider_request_timeout_seconds",
            "PROVIDER_REQUEST_TIMEOUT_SECONDS",
        ),
    )
    provider_retry_base_delay_seconds: float = Field(
        default=0.25,
        validation_alias=AliasChoices(
            "provider_retry_base_delay_seconds",
            "PROVIDER_RETRY_BASE_DELAY_SECONDS",
        ),
    )
    provider_retry_max_delay_seconds: float = Field(
        default=2.0,
        validation_alias=AliasChoices(
            "provider_retry_max_delay_seconds",
            "PROVIDER_RETRY_MAX_DELAY_SECONDS",
        ),
    )
    provider_tool_schema_max_bytes: int = Field(
        default=32768,
        validation_alias=AliasChoices(
            "provider_tool_schema_max_bytes",
            "PROVIDER_TOOL_SCHEMA_MAX_BYTES",
        ),
    )
    textgrid_base_url: str = Field(
        default="https://api.textgrid.com",
        validation_alias=AliasChoices("textgrid_base_url", "TEXTGRID_BASE_URL"),
    )
    textgrid_account_sid: str | None = Field(
        default=None,
        validation_alias=AliasChoices("textgrid_account_sid", "TEXTGRID_ACCOUNT_SID"),
    )
    textgrid_auth_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("textgrid_auth_token", "TEXTGRID_AUTH_TOKEN"),
    )
    textgrid_from_number: str | None = Field(
        default=None,
        validation_alias=AliasChoices("textgrid_from_number", "TEXTGRID_FROM_NUMBER"),
    )
    textgrid_sms_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("textgrid_sms_url", "TEXTGRID_SMS_URL"),
    )
    textgrid_webhook_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("textgrid_webhook_secret", "TEXTGRID_WEBHOOK_SECRET"),
    )
    resend_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("resend_api_key", "RESEND_API_KEY"),
    )
    resend_email_url: str = Field(
        default="https://api.resend.com/emails",
        validation_alias=AliasChoices("resend_email_url", "RESEND_EMAIL_URL"),
    )
    resend_from_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("resend_from_email", "RESEND_FROM_EMAIL", "RESEND_EMAIL_URL"),
    )
    resend_reply_to_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("resend_reply_to_email", "RESEND_REPLY_TO_EMAIL"),
    )
    cal_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("cal_api_key", "CAL_API_KEY", "Cal_API_key"),
    )
    cal_booking_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("cal_booking_url", "CAL_BOOKING_URL", "NEXT_PUBLIC_CAL_BOOKING_URL"),
    )
    cal_webhook_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("cal_webhook_secret", "CAL_WEBHOOK_SECRET"),
    )
    trigger_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("trigger_secret_key", "TRIGGER_SECRET_KEY"),
    )
    trigger_api_url: str = Field(
        default="https://api.trigger.dev",
        validation_alias=AliasChoices("trigger_api_url", "TRIGGER_API_URL"),
    )
    trigger_non_booker_check_task_id: str = Field(
        default="marketing-check-submitted-lead-booking",
        validation_alias=AliasChoices(
            "trigger_non_booker_check_task_id",
            "TRIGGER_NON_BOOKER_CHECK_TASK_ID",
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
