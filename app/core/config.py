from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_INTERNAL_ORG_ID = "org_internal"
DEFAULT_INTERNAL_ACTOR_ID = "ares-runtime"
DEFAULT_INTERNAL_ACTOR_TYPE = "service"


class Settings(BaseSettings):
    app_name: str = "Ares Runtime"
    runtime_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("runtime_api_key", "RUNTIME_API_KEY"),
    )
    runtime_docs_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("runtime_docs_enabled", "RUNTIME_DOCS_ENABLED"),
    )
    runtime_actor_header_overrides_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "runtime_actor_header_overrides_enabled",
            "RUNTIME_ACTOR_HEADER_OVERRIDES_ENABLED",
        ),
    )
    provider_webhook_signatures_required: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "provider_webhook_signatures_required",
            "PROVIDER_WEBHOOK_SIGNATURES_REQUIRED",
        ),
    )
    provider_live_sends_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("provider_live_sends_enabled", "PROVIDER_LIVE_SENDS_ENABLED"),
    )
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
    lead_machine_source_runs_state_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices("lead_machine_source_runs_state_path", "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH"),
    )
    lead_machine_artifact_root: str | None = Field(
        default=None,
        validation_alias=AliasChoices("lead_machine_artifact_root", "LEAD_MACHINE_ARTIFACT_ROOT"),
    )
    lead_machine_live_source_calls_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "lead_machine_live_source_calls_enabled",
            "LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED",
        ),
    )
    lead_machine_source_adapter_preview_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "lead_machine_source_adapter_preview_enabled",
            "LEAD_MACHINE_SOURCE_ADAPTER_PREVIEW_ENABLED",
        ),
    )
    lead_machine_live_cad_calls_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "lead_machine_live_cad_calls_enabled",
            "LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED",
        ),
    )
    lead_machine_live_tax_calls_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "lead_machine_live_tax_calls_enabled",
            "LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED",
        ),
    )
    lead_machine_live_land_record_calls_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "lead_machine_live_land_record_calls_enabled",
            "LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED",
        ),
    )
    lead_machine_live_case_detail_calls_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "lead_machine_live_case_detail_calls_enabled",
            "LEAD_MACHINE_LIVE_CASE_DETAIL_CALLS_ENABLED",
        ),
    )
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
    instantly_provider_live_enrollment_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "instantly_provider_live_enrollment_enabled",
            "INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED",
        ),
    )
    tracerfy_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("tracerfy_api_key", "TRACERFY_API_KEY"),
    )
    tracerfy_base_url: str = Field(
        default="https://tracerfy.com/v1/api",
        validation_alias=AliasChoices("tracerfy_base_url", "TRACERFY_BASE_URL"),
    )
    hubspot_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "hubspot_access_token",
            "HUBSPOT_ACCESS_TOKEN",
            "HUBSPOT_PERSONAL_KEY",
            "HUBSPOT_PRIVATE_APP_TOKEN",
            "hubspot_personal_key",
        ),
    )
    hubspot_developer_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "hubspot_developer_key",
            "hubspot_developer_keys",
            "HUBSPOT_DEVELOPER_KEY",
            "HUBSPOT_DEVELOPER_KEYS",
            "hubspot-developer_keys",
        ),
    )
    hubspot_base_url: str = Field(
        default="https://api.hubapi.com",
        validation_alias=AliasChoices("hubspot_base_url", "HUBSPOT_BASE_URL"),
    )
    hubspot_provider_live_writes_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "hubspot_provider_live_writes_enabled",
            "HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED",
        ),
    )
    hubspot_default_pipeline_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("hubspot_default_pipeline_id", "HUBSPOT_DEFAULT_PIPELINE_ID"),
    )
    hubspot_default_deal_stage_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("hubspot_default_deal_stage_id", "HUBSPOT_DEFAULT_DEAL_STAGE_ID"),
    )
    hubspot_owner_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("hubspot_owner_id", "HUBSPOT_OWNER_ID"),
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
    textgrid_status_callback_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("textgrid_status_callback_url", "TEXTGRID_STATUS_CALLBACK_URL"),
    )
    sms_agent_mode: Literal["record_only", "draft_only", "auto_ack"] = Field(
        default="draft_only",
        validation_alias=AliasChoices("sms_agent_mode", "SMS_AGENT_MODE"),
    )
    sms_agent_auto_replies_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "sms_agent_auto_replies_enabled",
            "SMS_AGENT_AUTO_REPLIES_ENABLED",
        ),
    )
    sms_agent_allowed_from_numbers: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "sms_agent_allowed_from_numbers",
            "SMS_AGENT_ALLOWED_FROM_NUMBERS",
        ),
    )
    sms_agent_process_batch_size: int = Field(
        default=25,
        validation_alias=AliasChoices(
            "sms_agent_process_batch_size",
            "SMS_AGENT_PROCESS_BATCH_SIZE",
        ),
    )
    sms_agent_max_attempts: int = Field(
        default=5,
        validation_alias=AliasChoices("sms_agent_max_attempts", "SMS_AGENT_MAX_ATTEMPTS"),
    )
    sms_agent_lock_seconds: int = Field(
        default=120,
        validation_alias=AliasChoices("sms_agent_lock_seconds", "SMS_AGENT_LOCK_SECONDS"),
    )
    sms_agent_retention_days: int = Field(
        default=90,
        validation_alias=AliasChoices("sms_agent_retention_days", "SMS_AGENT_RETENTION_DAYS"),
    )
    sms_agent_archive_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("sms_agent_archive_enabled", "SMS_AGENT_ARCHIVE_ENABLED"),
    )
    sms_agent_obsidian_archive_root: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "sms_agent_obsidian_archive_root",
            "SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT",
        ),
    )
    sms_agent_prompt_version: str = Field(
        default="sms_reply_agent_v1",
        validation_alias=AliasChoices("sms_agent_prompt_version", "SMS_AGENT_PROMPT_VERSION"),
    )
    sms_agent_llm_replies_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("sms_agent_llm_replies_enabled", "SMS_AGENT_LLM_REPLIES_ENABLED"),
    )
    sms_agent_llm_provider: Literal["anthropic", "openai_compat"] = Field(
        default="openai_compat",
        validation_alias=AliasChoices("sms_agent_llm_provider", "SMS_AGENT_LLM_PROVIDER"),
    )
    sms_agent_llm_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("sms_agent_llm_model", "SMS_AGENT_LLM_MODEL"),
    )
    sms_agent_llm_temperature: float = Field(
        default=0.4,
        validation_alias=AliasChoices("sms_agent_llm_temperature", "SMS_AGENT_LLM_TEMPERATURE"),
    )
    sms_agent_llm_timeout_seconds: float = Field(
        default=8.0,
        validation_alias=AliasChoices("sms_agent_llm_timeout_seconds", "SMS_AGENT_LLM_TIMEOUT_SECONDS"),
    )
    appointment_setter_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("appointment_setter_enabled", "APPOINTMENT_SETTER_ENABLED"),
    )
    appointment_setter_calendar_actions_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "appointment_setter_calendar_actions_enabled",
            "APPOINTMENT_SETTER_CALENDAR_ACTIONS_ENABLED",
        ),
    )
    appointment_setter_slack_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("appointment_setter_slack_enabled", "APPOINTMENT_SETTER_SLACK_ENABLED"),
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
        validation_alias=AliasChoices("resend_from_email", "RESEND_FROM_EMAIL"),
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
    trigger_appointment_reminder_task_id: str = Field(
        default="marketing-send-appointment-reminder",
        validation_alias=AliasChoices(
            "trigger_appointment_reminder_task_id",
            "TRIGGER_APPOINTMENT_REMINDER_TASK_ID",
        ),
    )
    marketing_appointment_reminders_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "marketing_appointment_reminders_enabled",
            "MARKETING_APPOINTMENT_REMINDERS_ENABLED",
        ),
    )
    slack_bot_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_bot_token", "SLACK_BOT_TOKEN"),
    )
    slack_notifications_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("slack_notifications_enabled", "SLACK_NOTIFICATIONS_ENABLED"),
    )
    slack_channel_lead_runs: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_lead_runs", "SLACK_CHANNEL_LEAD_RUNS"),
    )
    slack_channel_leads: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_leads", "SLACK_CHANNEL_LEADS"),
    )
    slack_channel_intake: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_intake", "SLACK_CHANNEL_INTAKE"),
    )
    slack_channel_hot_leads: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_hot_leads", "SLACK_CHANNEL_HOT_LEADS"),
    )
    slack_channel_chief_of_staff: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_chief_of_staff", "SLACK_CHANNEL_CHIEF_OF_STAFF"),
    )
    slack_channel_appointment_setter: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_appointment_setter", "SLACK_CHANNEL_APPOINTMENT_SETTER"),
    )
    ares_chief_of_staff_artifact_root: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ares_chief_of_staff_artifact_root", "ARES_CHIEF_OF_STAFF_ARTIFACT_ROOT"),
    )
    ares_chief_of_staff_scheduled_slack_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "ares_chief_of_staff_scheduled_slack_enabled",
            "ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED",
        ),
    )
    slack_channel_instantly_replies: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_instantly_replies", "SLACK_CHANNEL_INSTANTLY_REPLIES"),
    )
    slack_channel_lease_option_inbound: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_lease_option_inbound", "SLACK_CHANNEL_LEASE_OPTION_INBOUND"),
    )
    slack_channel_sms_calls: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_sms_calls", "SLACK_CHANNEL_SMS_CALLS"),
    )
    slack_channel_errors: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_errors", "SLACK_CHANNEL_ERRORS"),
    )
    slack_channel_qc: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_channel_qc", "SLACK_CHANNEL_QC"),
    )
    vapi_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vapi_api_key", "VAPI_API_KEY", "VAPI_PRIVATE_KEY"),
    )
    vapi_private_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vapi_private_key", "VAPI_PRIVATE_KEY"),
    )
    vapi_public_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vapi_public_key", "VAPI_PUBLIC_KEY"),
    )
    vapi_base_url: str = Field(
        default="https://api.vapi.ai",
        validation_alias=AliasChoices("vapi_base_url", "VAPI_BASE_URL"),
    )
    vapi_webhook_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vapi_webhook_secret", "VAPI_WEBHOOK_SECRET"),
    )
    vapi_webhook_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vapi_webhook_url", "VAPI_WEBHOOK_URL"),
    )
    vapi_default_assistant_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vapi_default_assistant_id", "VAPI_DEFAULT_ASSISTANT_ID"),
    )
    vapi_default_phone_number_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vapi_default_phone_number_id", "VAPI_DEFAULT_PHONE_NUMBER_ID"),
    )
    vapi_provider_live_sends_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("vapi_provider_live_sends_enabled", "VAPI_PROVIDER_LIVE_SENDS_ENABLED"),
    )
    vapi_default_model_provider: str = Field(
        default="openai",
        validation_alias=AliasChoices("vapi_default_model_provider", "VAPI_DEFAULT_MODEL_PROVIDER"),
    )
    vapi_default_model: str = Field(
        default="gpt-4o",
        validation_alias=AliasChoices("vapi_default_model", "VAPI_DEFAULT_MODEL"),
    )
    vapi_default_voice_provider: str = Field(
        default="11labs",
        validation_alias=AliasChoices("vapi_default_voice_provider", "VAPI_DEFAULT_VOICE_PROVIDER"),
    )
    vapi_default_voice_id: str = Field(
        default="cgSgspJ2msm6clMCkdW9",
        validation_alias=AliasChoices("vapi_default_voice_id", "VAPI_DEFAULT_VOICE_ID"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
