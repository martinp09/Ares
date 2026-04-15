from fastapi import Depends, FastAPI

from app.api.agent_assets import router as agent_assets_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.api.hermes_tools import router as hermes_tools_router
from app.api.marketing import router as marketing_router
from app.api.mission_control import router as mission_control_router
from app.api.outcomes import router as outcomes_router
from app.api.permissions import router as permissions_router
from app.api.replays import router as replays_router
from app.api.runs import router as runs_router
from app.api.sessions import router as sessions_router
from app.api.site_events import router as site_events_router
from app.api.trigger_callbacks import router as trigger_callbacks_router
from app.core.config import Settings
from app.core.dependencies import runtime_api_key_dependency, settings_dependency


def create_app() -> FastAPI:
    app = FastAPI(title="Hermes Central Command Runtime")

    protected_dependencies = [Depends(runtime_api_key_dependency)]

    app.include_router(commands_router, dependencies=protected_dependencies)
    app.include_router(approvals_router, dependencies=protected_dependencies)
    app.include_router(runs_router, dependencies=protected_dependencies)
    app.include_router(replays_router, dependencies=protected_dependencies)
    app.include_router(hermes_tools_router, dependencies=protected_dependencies)
    app.include_router(agents_router, dependencies=protected_dependencies)
    app.include_router(sessions_router, dependencies=protected_dependencies)
    app.include_router(permissions_router, dependencies=protected_dependencies)
    app.include_router(outcomes_router, dependencies=protected_dependencies)
    app.include_router(agent_assets_router, dependencies=protected_dependencies)
    app.include_router(mission_control_router, dependencies=protected_dependencies)
    app.include_router(site_events_router, dependencies=protected_dependencies)
    app.include_router(trigger_callbacks_router, dependencies=protected_dependencies)
    app.include_router(marketing_router, dependencies=protected_dependencies)

    @app.get("/health")
    def health_check(_: Settings = Depends(settings_dependency)) -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
