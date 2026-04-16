from __future__ import annotations

from collections.abc import Callable

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.turns import (
    TurnEventRecord,
    TurnEventType,
    TurnRecord,
    TurnResumeRequest,
    TurnStartRequest,
    TurnStatus,
    TurnToolCallRecord,
    TurnToolResultRecord,
)


EventCallback = Callable[[TurnEventRecord], None]


class TurnEventsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create_turn(
        self,
        *,
        session_id: str,
        agent_id: str,
        agent_revision_id: str,
        request: TurnStartRequest,
        resumed_from_turn_id: str | None = None,
        on_event: EventCallback | None = None,
    ) -> tuple[TurnRecord, list[TurnEventRecord]]:
        with self.client.transaction() as store:
            turn_ids = store.turn_ids_by_session.setdefault(session_id, [])
            turn_number = len(turn_ids) + 1
            turn_id = generate_id("trn")
            now = utc_now()
            turn = TurnRecord(
                id=turn_id,
                session_id=session_id,
                agent_id=agent_id,
                agent_revision_id=agent_revision_id,
                turn_number=turn_number,
                status=TurnStatus.RUNNING,
                input_message=request.input_message,
                assistant_message=None,
                tool_calls=[],
                tool_results=[],
                metadata=dict(request.metadata),
                resumed_from_turn_id=resumed_from_turn_id,
                created_at=now,
                updated_at=now,
            )
            store.turns[turn_id] = turn
            turn_ids.append(turn_id)
            store.turn_events[turn_id] = []

            self._append_event(
                store,
                turn,
                TurnEventType.TURN_STARTED,
                {
                    "agent_id": agent_id,
                    "agent_revision_id": agent_revision_id,
                    "turn_number": turn_number,
                    "input_message": request.input_message,
                    "assistant_message": request.assistant_message,
                    "metadata": request.metadata,
                    "tool_call_count": len(request.tool_calls),
                    "resumed_from_turn_id": resumed_from_turn_id,
                },
                on_event=on_event,
            )

            if request.tool_calls:
                for tool_call in request.tool_calls:
                    self._append_event(store, turn, TurnEventType.TOOL_CALL_REQUESTED, tool_call.model_dump(), on_event=on_event)
                self._append_event(store, turn, TurnEventType.TURN_WAITING_FOR_TOOL, {}, on_event=on_event)
            else:
                turn.assistant_message = request.assistant_message or ""
                self._append_event(
                    store,
                    turn,
                    TurnEventType.TURN_COMPLETED,
                    {
                        "assistant_message": turn.assistant_message,
                        "metadata": request.metadata,
                    },
                    on_event=on_event,
                )
                turn.status = TurnStatus.COMPLETED

            turn.updated_at = utc_now()
            store.turns[turn_id] = turn
            return turn, list(store.turn_events.get(turn_id, []))

    def get_turn(self, turn_id: str) -> TurnRecord | None:
        with self.client.transaction() as store:
            turn = store.turns.get(turn_id)
            if turn is not None:
                return turn
            replayed = self._replay_turn_from_store(store, turn_id)
            if replayed is not None:
                store.turns[turn_id] = replayed
            return replayed

    def get_turn_events(self, turn_id: str) -> list[TurnEventRecord]:
        with self.client.transaction() as store:
            return sorted(store.turn_events.get(turn_id, []), key=lambda event: event.sequence_number)

    def list_turns_for_session(self, session_id: str) -> list[TurnRecord]:
        with self.client.transaction() as store:
            turn_ids = store.turn_ids_by_session.get(session_id, [])
            turns = []
            for turn_id in turn_ids:
                turn = store.turns.get(turn_id) or self._replay_turn_from_store(store, turn_id)
                if turn is not None:
                    turns.append(turn)
            return sorted(turns, key=lambda turn: turn.turn_number)

    def resume_turn(
        self,
        turn_id: str,
        request: TurnResumeRequest,
        on_event: EventCallback | None = None,
    ) -> tuple[TurnRecord, list[TurnEventRecord]]:
        with self.client.transaction() as store:
            turn = store.turns.get(turn_id)
            if turn is None:
                turn = self._replay_turn_from_store(store, turn_id)
            if turn is None:
                raise ValueError("Turn not found")
            if turn.status != TurnStatus.WAITING_FOR_TOOL:
                raise ValueError("Turn is not waiting for tool results")

            requested_tool_ids = {tool_call.id for tool_call in turn.tool_calls}
            provided_tool_ids = [result.tool_call_id for result in request.tool_results]
            if not provided_tool_ids:
                raise ValueError("Tool results are required to resume a waiting turn")
            if len(set(provided_tool_ids)) != len(provided_tool_ids):
                raise ValueError("Duplicate tool result IDs are not allowed")
            missing_tool_ids = requested_tool_ids - set(provided_tool_ids)
            if missing_tool_ids:
                raise ValueError("Missing tool results for requested tool calls")
            unexpected_tool_ids = set(provided_tool_ids) - requested_tool_ids
            if unexpected_tool_ids:
                raise ValueError("Unknown tool result IDs were supplied")

            appended_events: list[TurnEventRecord] = []
            appended_events.append(self._append_event(store, turn, TurnEventType.TURN_RESUMED, {"metadata": request.metadata}, on_event=on_event))
            turn.status = TurnStatus.RUNNING
            turn.metadata.update(request.metadata)

            for result in request.tool_results:
                appended_events.append(self._append_event(store, turn, TurnEventType.TOOL_RESULT_RECORDED, result.model_dump(), on_event=on_event))

            if request.assistant_message is not None:
                turn.assistant_message = request.assistant_message

            appended_events.append(
                self._append_event(
                    store,
                    turn,
                    TurnEventType.TURN_COMPLETED,
                    {
                        "assistant_message": turn.assistant_message,
                        "metadata": request.metadata,
                    },
                    on_event=on_event,
                )
            )
            turn.status = TurnStatus.COMPLETED
            turn.updated_at = appended_events[-1].created_at
            store.turns[turn_id] = turn
            return turn, appended_events

    def replay_turn(self, turn_id: str) -> TurnRecord | None:
        with self.client.transaction() as store:
            replayed = self._replay_turn_from_store(store, turn_id)
            if replayed is not None:
                store.turns[turn_id] = replayed
            return replayed

    def _append_event(
        self,
        store,
        turn: TurnRecord,
        event_type: TurnEventType,
        payload: dict,
        *,
        on_event: EventCallback | None = None,
    ) -> TurnEventRecord:
        event = TurnEventRecord(
            id=generate_id("tev"),
            turn_id=turn.id,
            session_id=turn.session_id,
            event_type=event_type,
            payload=payload,
            sequence_number=len(store.turn_events.get(turn.id, [])) + 1,
            created_at=utc_now(),
        )
        store.turn_events.setdefault(turn.id, []).append(event)
        self._apply_event(turn, event)
        if on_event is not None:
            on_event(event)
        return event

    def _apply_event(self, turn: TurnRecord, event: TurnEventRecord) -> None:
        turn.updated_at = event.created_at
        if event.event_type == TurnEventType.TURN_STARTED:
            turn.agent_id = str(event.payload.get("agent_id") or turn.agent_id)
            turn.agent_revision_id = str(event.payload.get("agent_revision_id") or turn.agent_revision_id)
            turn.turn_number = int(event.payload.get("turn_number") or turn.turn_number)
            turn.resumed_from_turn_id = event.payload.get("resumed_from_turn_id") or turn.resumed_from_turn_id
            if event.payload.get("input_message") is not None:
                turn.input_message = event.payload.get("input_message")
            turn.metadata.update(event.payload.get("metadata") or {})
            assistant_message = event.payload.get("assistant_message")
            if assistant_message is not None:
                turn.assistant_message = assistant_message
            turn.status = TurnStatus.RUNNING
        elif event.event_type == TurnEventType.TURN_RESUMED:
            turn.status = TurnStatus.RUNNING
            turn.metadata.update(event.payload.get("metadata") or {})
        elif event.event_type == TurnEventType.TURN_WAITING_FOR_TOOL:
            turn.status = TurnStatus.WAITING_FOR_TOOL
        elif event.event_type == TurnEventType.TOOL_CALL_REQUESTED:
            turn.tool_calls.append(TurnToolCallRecord.model_validate(event.payload))
            turn.status = TurnStatus.WAITING_FOR_TOOL
        elif event.event_type == TurnEventType.TOOL_RESULT_RECORDED:
            turn.tool_results.append(TurnToolResultRecord.model_validate(event.payload))
        elif event.event_type == TurnEventType.TURN_COMPLETED:
            turn.status = TurnStatus.COMPLETED
            assistant_message = event.payload.get("assistant_message")
            if assistant_message is not None:
                turn.assistant_message = assistant_message
            turn.metadata.update(event.payload.get("metadata") or {})
        elif event.event_type == TurnEventType.TURN_FAILED:
            turn.status = TurnStatus.FAILED
            turn.metadata.update(event.payload.get("metadata") or {})

    def _replay_turn_from_store(self, store, turn_id: str) -> TurnRecord | None:
        events = sorted(store.turn_events.get(turn_id, []), key=lambda event: event.sequence_number)
        if not events:
            return None
        first = events[0]
        turn = TurnRecord(
            id=first.turn_id,
            session_id=first.session_id,
            agent_id=str(first.payload.get("agent_id") or ""),
            agent_revision_id=str(first.payload.get("agent_revision_id") or ""),
            turn_number=int(first.payload.get("turn_number") or 0),
            status=TurnStatus.RUNNING,
            input_message=first.payload.get("input_message"),
            assistant_message=first.payload.get("assistant_message"),
            resumed_from_turn_id=first.payload.get("resumed_from_turn_id"),
            metadata=dict(first.payload.get("metadata") or {}),
            created_at=first.created_at,
            updated_at=first.created_at,
        )
        for event in events:
            self._apply_event(turn, event)
        return turn
