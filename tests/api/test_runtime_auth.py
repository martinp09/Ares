from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import runtime_api_key_dependency


def _protected_app() -> FastAPI:
    app = FastAPI()

    @app.post("/protected", dependencies=[Depends(runtime_api_key_dependency)])
    def protected() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_runtime_auth_rejects_query_api_key_for_provider_callbacks() -> None:
    response = TestClient(_protected_app()).post("/protected?runtime_api_key=dev-runtime-key")

    assert response.status_code == 401


def test_runtime_auth_accepts_bearer_header() -> None:
    response = TestClient(_protected_app()).post(
        "/protected",
        headers={"Authorization": "Bearer dev-runtime-key"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
