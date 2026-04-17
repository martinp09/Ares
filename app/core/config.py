from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hermes Central Command Runtime"
    runtime_api_key: str = "dev-runtime-key"
    control_plane_backend: Literal["memory", "supabase"] = "memory"
    marketing_backend: Literal["memory", "supabase"] = "memory"
    lead_machine_backend: Literal["memory", "supabase"] = "memory"
    database_url: str | None = None
    site_events_backend: Literal["memory", "supabase"] = "supabase"
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
    provider_request_max_retries: int = Field(
        default=2,
        validation_alias=AliasChoices("provider_request_max_retries", "PROVIDER_REQUEST_MAX_RETRIES"),
    )
    provider_retry_base_delay_seconds: float = Field(
        default=1.0,
        validation_alias=AliasChoices(
            "provider_retry_base_delay_seconds",
            "PROVIDER_RETRY_BASE_DELAY_SECONDS",
        ),
    )
    provider_retry_max_delay_seconds: float = Field(
        default=8.0,
        validation_alias=AliasChoices(
            "provider_retry_max_delay_seconds",
            "PROVIDER_RETRY_MAX_DELAY_SECONDS",
        ),
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
    resend_from_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("resend_from_email", "RESEND_FROM_EMAIL", "RESEND_EMAIL_URL"),
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
