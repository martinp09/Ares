from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.api.ares import router as ares_router
from app.api.agent_assets import router as agent_assets_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.agent_installs import router as agent_installs_router
from app.api.commands import router as commands_router
from app.api.catalog import router as catalog_router
from app.api.hermes_tools import router as hermes_tools_router
from app.api.hubspot_crm import router as hubspot_crm_router
from app.api.lead_machine import router as lead_machine_router
from app.api.marketing import router as marketing_router
from app.api.memberships import router as memberships_router
from app.api.mission_control import router as mission_control_router
from app.api.organizations import router as organizations_router
from app.api.outcomes import router as outcomes_router
from app.api.permissions import router as permissions_router
from app.api.rbac import router as rbac_router
from app.api.release_management import router as release_management_router
from app.api.replays import router as replays_router
from app.api.runs import router as runs_router
from app.api.secrets import router as secrets_router
from app.api.sessions import router as sessions_router
from app.api.skills import router as skills_router
from app.api.site_events import router as site_events_router
from app.api.audit import router as audit_router
from app.api.sms_agent import router as sms_agent_router
from app.api.usage import router as usage_router
from app.api.trigger_callbacks import router as trigger_callbacks_router
from app.api.voice_agents import router as voice_agents_router
from app.core.config import Settings, get_settings
from app.core.dependencies import runtime_api_key_dependency, settings_dependency
from app.services.ares_autonomous_operator_service import autonomous_operator_service


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Ares Runtime",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    autonomous_operator_service.initialize_surface()

    protected_dependencies = [Depends(runtime_api_key_dependency)]

    if settings.runtime_docs_enabled:

        @app.get("/openapi.json", include_in_schema=False, dependencies=protected_dependencies)
        def protected_openapi() -> dict[str, object]:
            return app.openapi()

        @app.get("/docs", include_in_schema=False, dependencies=protected_dependencies)
        def protected_docs():  # type: ignore[no-untyped-def]
            return get_swagger_ui_html(openapi_url="/openapi.json", title="Ares Runtime - Swagger UI")

        @app.get("/redoc", include_in_schema=False, dependencies=protected_dependencies)
        def protected_redoc():  # type: ignore[no-untyped-def]
            return get_redoc_html(openapi_url="/openapi.json", title="Ares Runtime - ReDoc")

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        safe_errors = []
        for error in exc.errors():
            redacted = dict(error)
            redacted.pop("input", None)
            redacted.pop("ctx", None)
            safe_errors.append(redacted)
        return JSONResponse(status_code=422, content={"detail": safe_errors})

    app.include_router(commands_router, dependencies=protected_dependencies)
    app.include_router(approvals_router, dependencies=protected_dependencies)
    app.include_router(runs_router, dependencies=protected_dependencies)
    app.include_router(replays_router, dependencies=protected_dependencies)
    app.include_router(hermes_tools_router, dependencies=protected_dependencies)
    app.include_router(hubspot_crm_router, dependencies=protected_dependencies)
    app.include_router(agents_router, dependencies=protected_dependencies)
    app.include_router(catalog_router, dependencies=protected_dependencies)
    app.include_router(agent_installs_router, dependencies=protected_dependencies)
    app.include_router(organizations_router, dependencies=protected_dependencies)
    app.include_router(memberships_router, dependencies=protected_dependencies)
    app.include_router(sessions_router, dependencies=protected_dependencies)
    app.include_router(skills_router, dependencies=protected_dependencies)
    app.include_router(permissions_router, dependencies=protected_dependencies)
    app.include_router(rbac_router, dependencies=protected_dependencies)
    app.include_router(release_management_router, dependencies=protected_dependencies)
    app.include_router(secrets_router, dependencies=protected_dependencies)
    app.include_router(audit_router, dependencies=protected_dependencies)
    app.include_router(usage_router, dependencies=protected_dependencies)
    app.include_router(outcomes_router, dependencies=protected_dependencies)
    app.include_router(agent_assets_router, dependencies=protected_dependencies)
    app.include_router(mission_control_router, dependencies=protected_dependencies)
    app.include_router(site_events_router, dependencies=protected_dependencies)
    app.include_router(trigger_callbacks_router, dependencies=protected_dependencies)
    app.include_router(marketing_router, dependencies=protected_dependencies)
    app.include_router(sms_agent_router, dependencies=protected_dependencies)
    app.include_router(voice_agents_router, dependencies=protected_dependencies)
    app.include_router(lead_machine_router, dependencies=protected_dependencies)
    app.include_router(ares_router, dependencies=protected_dependencies)

    @app.get("/health")
    def health_check(_: Settings = Depends(settings_dependency)) -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
