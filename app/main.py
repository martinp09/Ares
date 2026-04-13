from fastapi import Depends, FastAPI

from app.core.config import Settings
from app.core.dependencies import settings_dependency


def create_app() -> FastAPI:
    app = FastAPI(title="Hermes Central Command Runtime")

    @app.get("/health")
    def health_check(_: Settings = Depends(settings_dependency)) -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
