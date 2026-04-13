from fastapi import APIRouter, HTTPException

from app.models.sessions import SessionAppendEventRequest, SessionCreateRequest, SessionRecord
from app.services.session_service import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRecord)
def create_session(request: SessionCreateRequest) -> SessionRecord:
    try:
        return session_service.create_session(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=SessionRecord)
def get_session(session_id: str) -> SessionRecord:
    session = session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/events", response_model=SessionRecord)
def append_session_event(session_id: str, request: SessionAppendEventRequest) -> SessionRecord:
    session = session_service.append_event(session_id, request)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
