from fastapi import Depends, FastAPI

from app.api.ares import router as ares_router
from app.api.agent_assets import router as agent_assets_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.api.hermes_tools import router as hermes_tools_router
from app.api.lead_machine import router as lead_machine_router
from app.api.marketing import router as marketing_router
from app.api.memberships import router as memberships_router
from app.api.mission_control import router as mission_control_router
from app.api.organizations import router as organizations_router
from app.api.outcomes import router as outcomes_router
from app.api.permissions import router as permissions_router
from app.api.rbac import router as rbac_router
from app.api.replays import router as replays_router
from app.api.runs import router as runs_router
from app.api.secrets import router as secrets_router
from app.api.sessions import router as sessions_router
from app.api.skills import router as skills_router
from app.api.site_events import router as site_events_router
from app.api.audit import router as audit_router
from app.api.usage import router as usage_router
from app.api.trigger_callbacks import router as trigger_callbacks_router
from app.core.config import Settings
from app.core.dependencies import runtime_api_key_dependency, settings_dependency
from app.services.ares_autonomous_operator_service import autonomous_operator_service


def create_app() -> FastAPI:
    app = FastAPI(title="Ares Runtime")
    autonomous_operator_service.initialize_surface()

    protected_dependencies = [Depends(runtime_api_key_dependency)]

    app.include_router(commands_router, dependencies=protected_dependencies)
    app.include_router(approvals_router, dependencies=protected_dependencies)
    app.include_router(runs_router, dependencies=protected_dependencies)
    app.include_router(replays_router, dependencies=protected_dependencies)
    app.include_router(hermes_tools_router, dependencies=protected_dependencies)
    app.include_router(agents_router, dependencies=protected_dependencies)
    app.include_router(organizations_router, dependencies=protected_dependencies)
    app.include_router(memberships_router, dependencies=protected_dependencies)
    app.include_router(sessions_router, dependencies=protected_dependencies)
    app.include_router(skills_router, dependencies=protected_dependencies)
    app.include_router(permissions_router, dependencies=protected_dependencies)
    app.include_router(rbac_router, dependencies=protected_dependencies)
    app.include_router(secrets_router, dependencies=protected_dependencies)
    app.include_router(audit_router, dependencies=protected_dependencies)
    app.include_router(usage_router, dependencies=protected_dependencies)
    app.include_router(outcomes_router, dependencies=protected_dependencies)
    app.include_router(agent_assets_router, dependencies=protected_dependencies)
    app.include_router(mission_control_router, dependencies=protected_dependencies)
    app.include_router(site_events_router, dependencies=protected_dependencies)
    app.include_router(trigger_callbacks_router, dependencies=protected_dependencies)
    app.include_router(marketing_router, dependencies=protected_dependencies)
    app.include_router(lead_machine_router, dependencies=protected_dependencies)
    app.include_router(ares_router, dependencies=protected_dependencies)

    @app.get("/health")
    def health_check(_: Settings = Depends(settings_dependency)) -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
