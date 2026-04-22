from fastapi import APIRouter, HTTPException, Query

from app.models.secrets import (
    SecretBindingCreateRequest,
    SecretBindingListResponse,
    SecretBindingRecord,
    SecretCreateRequest,
    SecretListResponse,
    SecretSummaryRecord,
)
from app.services.secrets_service import secret_service

router = APIRouter(prefix="/secrets", tags=["secrets"])


def _status_code_for_secret_error(message: str) -> int:
    return 404 if "not found" in message.lower() else 422


@router.post("", response_model=SecretSummaryRecord)
def create_secret(request: SecretCreateRequest) -> SecretSummaryRecord:
    return secret_service.create_secret(request)


@router.get("", response_model=SecretListResponse)
def list_secrets(org_id: str | None = Query(default=None)) -> SecretListResponse:
    return SecretListResponse(secrets=secret_service.list_secrets(org_id=org_id))


@router.post("/{secret_id}/bindings", response_model=SecretBindingRecord)
def bind_secret(secret_id: str, request: SecretBindingCreateRequest) -> SecretBindingRecord:
    try:
        return secret_service.bind_secret(secret_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_secret_error(str(exc)), detail=str(exc)) from exc


@router.get("/revisions/{revision_id}", response_model=SecretBindingListResponse)
def list_bindings_for_revision(revision_id: str) -> SecretBindingListResponse:
    try:
        return SecretBindingListResponse(bindings=secret_service.list_bindings_for_revision(revision_id))
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_secret_error(str(exc)), detail=str(exc)) from exc
