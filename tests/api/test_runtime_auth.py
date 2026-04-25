from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.dependencies import runtime_api_key_dependency


def test_runtime_auth_accepts_query_api_key_for_provider_callbacks() -> None:
    app = FastAPI()

    @app.post("/protected", dependencies=[Depends(runtime_api_key_dependency)])
    def protected() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(app).post("/protected?runtime_api_key=dev-runtime-key")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
