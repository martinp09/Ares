from fastapi import APIRouter, HTTPException

from app.models.sessions import SessionAppendEventRequest, SessionCreateRequest, SessionRecord
from app.models.session_journal import SessionJournalRecord
from app.models.turns import TurnRecord, TurnResumeRequest, TurnStartRequest, TurnEventRecord
from app.services.session_service import session_service
from app.services.turn_runner_service import turn_runner_service

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


@router.get("/{session_id}/journal", response_model=SessionJournalRecord)
def get_session_journal(session_id: str) -> SessionJournalRecord:
    journal = session_service.get_session_journal(session_id)
    if journal is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return journal


@router.post("/{session_id}/events", response_model=SessionRecord)
def append_session_event(session_id: str, request: SessionAppendEventRequest) -> SessionRecord:
    session = session_service.append_event(session_id, request)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/turns", response_model=TurnRecord)
def start_turn(session_id: str, request: TurnStartRequest) -> TurnRecord:
    try:
        return turn_runner_service.start_turn(session_id, request)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() or "belong" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{session_id}/turns/{turn_id}/resume", response_model=TurnRecord)
def resume_turn(session_id: str, turn_id: str, request: TurnResumeRequest) -> TurnRecord:
    try:
        return turn_runner_service.resume_turn(session_id, turn_id, request)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() or "belong" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/{session_id}/turns/{turn_id}", response_model=TurnRecord)
def get_turn(session_id: str, turn_id: str) -> TurnRecord:
    turn = turn_runner_service.get_turn(turn_id)
    if turn is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    if turn.session_id != session_id:
        raise HTTPException(status_code=404, detail="Turn not found")
    return turn


@router.get("/{session_id}/turns/{turn_id}/events", response_model=list[TurnEventRecord])
def get_turn_events(session_id: str, turn_id: str) -> list[TurnEventRecord]:
    turn = turn_runner_service.get_turn(turn_id)
    if turn is None or turn.session_id != session_id:
        raise HTTPException(status_code=404, detail="Turn not found")
    return turn_runner_service.get_turn_events(turn_id)
