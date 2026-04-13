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
        CommandsRepository,
        EventsRepository,
        InMemoryControlPlaneClient,
        OutcomesRepository,
        PermissionsRepository,
        RunsRepository,
        SessionsRepository,
    )
    from app.db.agent_assets import AgentAssetsRepository as agent_assets_repository_module
    from app.db.agents import AgentsRepository as agents_repository_module
    from app.db.approvals import ApprovalsRepository as approvals_repository_module
    from app.db.artifacts import ArtifactsRepository as artifacts_repository_module
    from app.db.client import InMemoryControlPlaneClient as client_module
    from app.db.commands import CommandsRepository as commands_repository_module
    from app.db.events import EventsRepository as events_repository_module
    from app.db.outcomes import OutcomesRepository as outcomes_repository_module
    from app.db.permissions import PermissionsRepository as permissions_repository_module
    from app.db.runs import RunsRepository as runs_repository_module
    from app.db.sessions import SessionsRepository as sessions_repository_module

    assert AgentAssetsRepository is agent_assets_repository_module
    assert AgentsRepository is agents_repository_module
    assert ApprovalsRepository is approvals_repository_module
    assert ArtifactsRepository is artifacts_repository_module
    assert CommandsRepository is commands_repository_module
    assert EventsRepository is events_repository_module
    assert InMemoryControlPlaneClient is client_module
    assert OutcomesRepository is outcomes_repository_module
    assert PermissionsRepository is permissions_repository_module
    assert RunsRepository is runs_repository_module
    assert SessionsRepository is sessions_repository_module


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
