from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hermes Central Command Runtime"
    runtime_api_key: str = "dev-runtime-key"
    control_plane_backend: Literal["memory", "supabase"] = "memory"
    marketing_backend: Literal["memory", "supabase"] = "memory"
    database_url: str | None = None
    site_events_backend: Literal["memory", "supabase"] = "supabase"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
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
