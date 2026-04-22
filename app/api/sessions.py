from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.sessions import SessionAppendEventRequest, SessionCreateRequest, SessionRecord
from app.models.session_journal import SessionJournalRecord
from app.models.turns import TurnRecord, TurnResumeRequest, TurnStartRequest, TurnEventRecord
from app.services.session_service import session_service
from app.services.turn_runner_service import turn_runner_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRecord)
def create_session(
    request: SessionCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> SessionRecord:
    try:
        return session_service.create_session(request, org_id=actor_context.org_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/{session_id}", response_model=SessionRecord)
def get_session(
    session_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> SessionRecord:
    session = session_service.get_session(session_id, org_id=actor_context.org_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/journal", response_model=SessionJournalRecord)
def get_session_journal(
    session_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> SessionJournalRecord:
    journal = session_service.get_session_journal(session_id, org_id=actor_context.org_id)
    if journal is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return journal


@router.post("/{session_id}/events", response_model=SessionRecord)
def append_session_event(
    session_id: str,
    request: SessionAppendEventRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> SessionRecord:
    session = session_service.append_event(session_id, request, org_id=actor_context.org_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/turns", response_model=TurnRecord)
def start_turn(
    session_id: str,
    request: TurnStartRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> TurnRecord:
    try:
        return turn_runner_service.start_turn(session_id, request, org_id=actor_context.org_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() or "belong" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/{session_id}/turns/{turn_id}/resume", response_model=TurnRecord)
def resume_turn(
    session_id: str,
    turn_id: str,
    request: TurnResumeRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> TurnRecord:
    try:
        return turn_runner_service.resume_turn(session_id, turn_id, request, org_id=actor_context.org_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() or "belong" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/{session_id}/turns/{turn_id}", response_model=TurnRecord)
def get_turn(
    session_id: str,
    turn_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> TurnRecord:
    turn = turn_runner_service.get_turn(turn_id, org_id=actor_context.org_id)
    if turn is None or turn.session_id != session_id:
        raise HTTPException(status_code=404, detail="Turn not found")
    return turn


@router.get("/{session_id}/turns/{turn_id}/events", response_model=list[TurnEventRecord])
def get_turn_events(
    session_id: str,
    turn_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> list[TurnEventRecord]:
    turn = turn_runner_service.get_turn(turn_id, org_id=actor_context.org_id)
    if turn is None or turn.session_id != session_id:
        raise HTTPException(status_code=404, detail="Turn not found")
    return turn_runner_service.get_turn_events(turn_id, org_id=actor_context.org_id)
