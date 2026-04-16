from app.db.agents import AgentsRepository
from app.db.client import STORE
from app.db.sessions import SessionsRepository
from app.db.turn_events import TurnEventsRepository
from app.models.sessions import SessionCreateRequest
from app.models.turns import TurnEventType, TurnResumeRequest, TurnStartRequest, TurnStatus, TurnToolCallRecord, TurnToolResultRecord
from app.services.run_service import reset_control_plane_state
from app.services.session_service import SessionService


def test_turn_events_repository_replays_completed_turn_from_events() -> None:
    reset_control_plane_state()

    agents_repository = AgentsRepository()
    sessions_repository = SessionsRepository()
    session_service = SessionService(sessions_repository, agents_repository)
    turn_events_repository = TurnEventsRepository()

    agent, revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Repo Agent",
        description=None,
        config={"prompt": "Coordinate outreach"},
    )
    agents_repository.publish_revision(agent.id, revision.id)
    session = session_service.create_session(
        SessionCreateRequest(
            agent_revision_id=revision.id,
            business_id="limitless",
            environment="dev",
        )
    )

    turn, events = turn_events_repository.create_turn(
        session_id=session.id,
        agent_id=agent.id,
        agent_revision_id=revision.id,
        request=TurnStartRequest(
            input_message="Start the loop",
            assistant_message="All set",
        ),
        resumed_from_turn_id="origin_turn",
    )

    assert turn.status == TurnStatus.COMPLETED
    assert [event.event_type for event in events] == [TurnEventType.TURN_STARTED, TurnEventType.TURN_COMPLETED]
    assert turn_events_repository.list_turns_for_session(session.id)[0].id == turn.id

    STORE.turns.pop(turn.id)
    replayed = turn_events_repository.replay_turn(turn.id)

    assert replayed is not None
    assert replayed.agent_id == agent.id
    assert replayed.agent_revision_id == revision.id
    assert replayed.resumed_from_turn_id == "origin_turn"
    assert replayed.status == TurnStatus.COMPLETED
    assert replayed.assistant_message == "All set"
    assert [event.event_type for event in turn_events_repository.get_turn_events(turn.id)] == [
        TurnEventType.TURN_STARTED,
        TurnEventType.TURN_COMPLETED,
    ]


def test_turn_events_repository_records_resume_sequence() -> None:
    reset_control_plane_state()

    agents_repository = AgentsRepository()
    turn_events_repository = TurnEventsRepository()
    session_service = SessionService(SessionsRepository(), agents_repository)

    agent, revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Repo Agent",
        description=None,
        config={"prompt": "Coordinate outreach"},
    )
    agents_repository.publish_revision(agent.id, revision.id)
    session = session_service.create_session(
        SessionCreateRequest(
            agent_revision_id=revision.id,
            business_id="limitless",
            environment="dev",
        )
    )
    turn, _ = turn_events_repository.create_turn(
        session_id=session.id,
        agent_id=agent.id,
        agent_revision_id=revision.id,
        request=TurnStartRequest(
            input_message="Check a tool",
            tool_calls=[TurnToolCallRecord(id="call_1", tool_name="lookup", arguments={"id": "abc"})],
        ),
    )

    resumed_turn, events = turn_events_repository.resume_turn(
        turn.id,
        TurnResumeRequest(
            assistant_message="Done",
            tool_results=[TurnToolResultRecord(tool_call_id="call_1", output={"ok": True})],
        ),
    )

    assert resumed_turn.status == TurnStatus.COMPLETED
    assert [event.event_type for event in events] == [
        TurnEventType.TURN_RESUMED,
        TurnEventType.TOOL_RESULT_RECORDED,
        TurnEventType.TURN_COMPLETED,
    ]
