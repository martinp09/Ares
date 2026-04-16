def test_core_modules_are_importable():
    from app.core.config import Settings, get_settings
    from app.core.dependencies import settings_dependency

    assert Settings is not None
    assert callable(get_settings)
    assert callable(settings_dependency)


def test_db_modules_are_importable():
    from app.db import (
        AgentAssetsRepository,
        AgentsRepository,
        ApprovalsRepository,
        ArtifactsRepository,
        AuditRepository,
        AutomationRunsRepository,
        CampaignMembershipsRepository,
        CampaignsRepository,
        CommandsRepository,
        EventsRepository,
        InMemoryControlPlaneClient,
        LeadEventsRepository,
        LeadsRepository,
        OutcomesRepository,
        PermissionsRepository,
        ProviderWebhooksRepository,
        RBACRepository,
        RunsRepository,
        SecretsRepository,
        SessionsRepository,
        SkillsRepository,
        HostAdapterDispatchesRepository,
        SuppressionRepository,
        TasksRepository,
        UsageRepository,
    )
    from app.db.agent_assets import AgentAssetsRepository as agent_assets_repository_module
    from app.db.agents import AgentsRepository as agents_repository_module
    from app.db.approvals import ApprovalsRepository as approvals_repository_module
    from app.db.artifacts import ArtifactsRepository as artifacts_repository_module
    from app.db.automation_runs import AutomationRunsRepository as automation_runs_repository_module
    from app.db.campaign_memberships import CampaignMembershipsRepository as campaign_memberships_repository_module
    from app.db.campaigns import CampaignsRepository as campaigns_repository_module
    from app.db.client import InMemoryControlPlaneClient as client_module
    from app.db.commands import CommandsRepository as commands_repository_module
    from app.db.events import EventsRepository as events_repository_module
    from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository as host_adapter_dispatches_repository_module
    from app.db.lead_events import LeadEventsRepository as lead_events_repository_module
    from app.db.leads import LeadsRepository as leads_repository_module
    from app.db.outcomes import OutcomesRepository as outcomes_repository_module
    from app.db.permissions import PermissionsRepository as permissions_repository_module
    from app.db.provider_webhooks import ProviderWebhooksRepository as provider_webhooks_repository_module
    from app.db.rbac import RBACRepository as rbac_repository_module
    from app.db.runs import RunsRepository as runs_repository_module
    from app.db.secrets import SecretsRepository as secrets_repository_module
    from app.db.sessions import SessionsRepository as sessions_repository_module
    from app.db.skills import SkillsRepository as skills_repository_module
    from app.db.audit import AuditRepository as audit_repository_module
    from app.db.suppression import SuppressionRepository as suppression_repository_module
    from app.db.tasks import TasksRepository as tasks_repository_module
    from app.db.usage import UsageRepository as usage_repository_module

    assert AgentAssetsRepository is agent_assets_repository_module
    assert AgentsRepository is agents_repository_module
    assert ApprovalsRepository is approvals_repository_module
    assert ArtifactsRepository is artifacts_repository_module
    assert AuditRepository is audit_repository_module
    assert AutomationRunsRepository is automation_runs_repository_module
    assert CampaignMembershipsRepository is campaign_memberships_repository_module
    assert CampaignsRepository is campaigns_repository_module
    assert CommandsRepository is commands_repository_module
    assert EventsRepository is events_repository_module
    assert HostAdapterDispatchesRepository is host_adapter_dispatches_repository_module
    assert InMemoryControlPlaneClient is client_module
    assert LeadEventsRepository is lead_events_repository_module
    assert LeadsRepository is leads_repository_module
    assert OutcomesRepository is outcomes_repository_module
    assert PermissionsRepository is permissions_repository_module
    assert ProviderWebhooksRepository is provider_webhooks_repository_module
    assert RBACRepository is rbac_repository_module
    assert RunsRepository is runs_repository_module
    assert SecretsRepository is secrets_repository_module
    assert SessionsRepository is sessions_repository_module
    assert SkillsRepository is skills_repository_module
    assert SuppressionRepository is suppression_repository_module
    assert TasksRepository is tasks_repository_module
    assert UsageRepository is usage_repository_module


def test_mission_control_modules_are_importable():
    from app.api.mission_control import router
    from app.models.mission_control import (
        MissionControlDashboardResponse,
        MissionControlInboxResponse,
        MissionControlRunsResponse,
        MissionControlThreadRecord,
    )
    from app.services.mission_control_service import MissionControlService, mission_control_service

    assert router is not None
    assert MissionControlDashboardResponse is not None
    assert MissionControlInboxResponse is not None
    assert MissionControlRunsResponse is not None
    assert MissionControlThreadRecord is not None
    assert MissionControlService is not None
    assert mission_control_service is not None


def test_lead_machine_models_are_exported():
    from app.models import (
        AutomationRunRecord,
        CampaignMembershipRecord,
        CampaignRecord,
        LeadEventRecord,
        LeadRecord,
        ProbateLeadRecord,
        ProviderWebhookReceiptRecord,
        SuppressionRecord,
        TaskRecord,
    )
    from app.models.automation_runs import AutomationRunRecord as automation_run_record_module
    from app.models.campaigns import CampaignMembershipRecord as campaign_membership_record_module
    from app.models.campaigns import CampaignRecord as campaign_record_module
    from app.models.lead_events import LeadEventRecord as lead_event_record_module
    from app.models.lead_events import ProviderWebhookReceiptRecord as provider_webhook_receipt_record_module
    from app.models.leads import LeadRecord as lead_record_module
    from app.models.probate_leads import ProbateLeadRecord as probate_lead_record_module
    from app.models.suppression import SuppressionRecord as suppression_record_module
    from app.models.tasks import TaskRecord as task_record_module

    assert AutomationRunRecord is automation_run_record_module
    assert CampaignMembershipRecord is campaign_membership_record_module
    assert CampaignRecord is campaign_record_module
    assert LeadEventRecord is lead_event_record_module
    assert LeadRecord is lead_record_module
    assert ProbateLeadRecord is probate_lead_record_module
    assert ProviderWebhookReceiptRecord is provider_webhook_receipt_record_module
    assert SuppressionRecord is suppression_record_module
    assert TaskRecord is task_record_module
