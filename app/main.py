from fastapi import Depends, FastAPI

from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.api.hermes_tools import router as hermes_tools_router
from app.api.marketing import router as marketing_router
from app.api.replays import router as replays_router
from app.api.runs import router as runs_router
from app.api.site_events import router as site_events_router
from app.core.config import Settings
from app.core.dependencies import settings_dependency


def create_app() -> FastAPI:
    app = FastAPI(title="Hermes Central Command Runtime")

    app.include_router(commands_router)
    app.include_router(approvals_router)
    app.include_router(runs_router)
    app.include_router(replays_router)
    app.include_router(hermes_tools_router)
    app.include_router(site_events_router)
    app.include_router(marketing_router)

    @app.get("/health")
    def health_check(_: Settings = Depends(settings_dependency)) -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
