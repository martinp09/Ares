import pytest

from app.db.client import STORE
from app.db.agents import AgentsRepository
from app.models.providers import ProviderCapability
from app.models.sessions import SessionCreateRequest
from app.models.turns import TurnResumeRequest, TurnStartRequest, TurnStatus, TurnToolCallRecord, TurnToolResultRecord, TurnEventType
from app.services.run_service import reset_control_plane_state
from app.services.session_service import SessionService
from app.services.turn_runner_service import TurnRunnerService


def make_published_session() -> tuple[str, str, str, TurnRunnerService, SessionService]:
    agents_repository = AgentsRepository()
    session_service = SessionService()
    turn_runner_service = TurnRunnerService()

    agent, revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Turn Agent",
        description="Coordinate turns",
        config={"prompt": "Coordinate outreach"},
    )
    agents_repository.publish_revision(agent.id, revision.id)
    session = session_service.create_session(
        SessionCreateRequest(
            agent_revision_id=revision.id,
            business_id="limitless",
            environment="dev",
            initial_message="Start outreach",
        )
    )
    return session.id, agent.id, revision.id, turn_runner_service, session_service


def test_turn_completes_without_tool_calls_and_replays_from_events() -> None:
    reset_control_plane_state()
    session_id, agent_id, revision_id, turn_runner_service, session_service = make_published_session()

    turn = turn_runner_service.start_turn(
        session_id,
        TurnStartRequest(
            input_message="Draft the first reply",
            assistant_message="Send the follow-up email",
        ),
    )

    assert turn.agent_id == agent_id
    assert turn.agent_revision_id == revision_id
    assert turn.status == TurnStatus.COMPLETED
    assert turn.assistant_message == "Send the follow-up email"
    assert [event.event_type for event in turn_runner_service.get_turn_events(turn.id)] == [
        TurnEventType.TURN_STARTED,
        TurnEventType.TURN_COMPLETED,
    ]
    assert [entry.event_type for entry in session_service.get_session(session_id).timeline][-2:] == [
        "turn_started",
        "turn_completed",
    ]

    STORE.turns.pop(turn.id)

    replayed = turn_runner_service.replay_turn(turn.id)
    assert replayed is not None
    assert replayed.status == TurnStatus.COMPLETED
    assert replayed.assistant_message == "Send the follow-up email"
    assert replayed.turn_number == 1


def test_turn_waits_for_tool_results_then_resumes_and_completes() -> None:
    reset_control_plane_state()
    session_id, _, _, turn_runner_service, session_service = make_published_session()

    turn = turn_runner_service.start_turn(
        session_id,
        TurnStartRequest(
            input_message="Check the property record",
            tool_calls=[
                TurnToolCallRecord(
                    id="call_1",
                    tool_name="lookup_property",
                    arguments={"apn": "123-456-789"},
                )
            ],
        ),
    )

    assert turn.status == TurnStatus.WAITING_FOR_TOOL
    assert [event.event_type for event in turn_runner_service.get_turn_events(turn.id)] == [
        TurnEventType.TURN_STARTED,
        TurnEventType.TOOL_CALL_REQUESTED,
        TurnEventType.TURN_WAITING_FOR_TOOL,
    ]

    with pytest.raises(ValueError, match="Tool results are required"):
        turn_runner_service.resume_turn(
            session_id,
            turn.id,
            TurnResumeRequest(assistant_message="Still waiting", tool_results=[]),
        )

    resumed = turn_runner_service.resume_turn(
        session_id,
        turn.id,
        TurnResumeRequest(
            assistant_message="Found the deed chain.",
            tool_results=[
                TurnToolResultRecord(
                    tool_call_id="call_1",
                    output={"status": "found", "owner": "Estate of Parker"},
                )
            ],
        ),
    )

    assert resumed.status == TurnStatus.COMPLETED
    assert resumed.assistant_message == "Found the deed chain."
    assert len(resumed.tool_results) == 1
    assert resumed.tool_results[0].tool_call_id == "call_1"
    assert [event.event_type for event in turn_runner_service.get_turn_events(turn.id)] == [
        TurnEventType.TURN_STARTED,
        TurnEventType.TOOL_CALL_REQUESTED,
        TurnEventType.TURN_WAITING_FOR_TOOL,
        TurnEventType.TURN_RESUMED,
        TurnEventType.TOOL_RESULT_RECORDED,
        TurnEventType.TURN_COMPLETED,
    ]
    assert [entry.event_type for entry in session_service.get_session(session_id).timeline][-6:] == [
        "turn_started",
        "tool_call_requested",
        "turn_waiting_for_tool",
        "turn_resumed",
        "tool_result_recorded",
        "turn_completed",
    ]


def test_turn_rejects_tool_calls_when_revision_lacks_tool_capability() -> None:
    reset_control_plane_state()
    agents_repository = AgentsRepository()
    session_service = SessionService()
    turn_runner_service = TurnRunnerService()

    agent, revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Capability Gate Agent",
        description="Tool gating",
        config={"prompt": "Gate tool use"},
        provider_capabilities=[ProviderCapability.STREAMING],
    )
    agents_repository.publish_revision(agent.id, revision.id)
    session = session_service.create_session(
        SessionCreateRequest(
            agent_revision_id=revision.id,
            business_id="limitless",
            environment="dev",
        )
    )

    with pytest.raises(ValueError, match="does not support tool calls"):
        turn_runner_service.start_turn(
            session.id,
            TurnStartRequest(
                input_message="Check the property record",
                tool_calls=[
                    TurnToolCallRecord(
                        id="call_gate",
                        tool_name="lookup_property",
                        arguments={"apn": "123-456-789"},
                    )
                ],
            ),
        )
