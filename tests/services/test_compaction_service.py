from app.db.agents import AgentsRepository
from app.models.sessions import SessionCreateRequest
from app.models.turns import TurnResumeRequest, TurnStartRequest, TurnToolCallRecord, TurnToolResultRecord
from app.services.compaction_service import CompactionService
from app.services.run_service import reset_control_plane_state
from app.services.session_service import SessionService
from app.services.turn_runner_service import TurnRunnerService


def make_published_session() -> tuple[str, TurnRunnerService, SessionService, CompactionService]:
    agents_repository = AgentsRepository()
    session_service = SessionService()
    turn_runner_service = TurnRunnerService()
    compaction_service = CompactionService()

    agent, revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Compaction Agent",
        description="Summarize session memory",
        config={"prompt": "Summarize state"},
    )
    agents_repository.publish_revision(agent.id, revision.id)
    session = session_service.create_session(
        SessionCreateRequest(
            agent_revision_id=revision.id,
            business_id="limitless",
            environment="dev",
            initial_message="Keep the session memory fresh",
        )
    )
    return session.id, turn_runner_service, session_service, compaction_service


def test_compaction_summary_is_created_and_updated_across_turn_lifecycle() -> None:
    reset_control_plane_state()
    session_id, turn_runner_service, session_service, compaction_service = make_published_session()

    turn_runner_service.start_turn(
        session_id,
        TurnStartRequest(
            input_message="Confirm the outreach plan",
            assistant_message="Outreach plan confirmed and queued.",
        ),
    )

    first_summary = compaction_service.get_session_summary(session_id)
    assert first_summary is not None
    assert first_summary.summary_version == 1
    assert first_summary.compacted_turn_count == 1
    assert first_summary.goals == ["Confirm the outreach plan"]
    assert first_summary.completed_work == ["Outreach plan confirmed and queued."]
    assert first_summary.pending_work == []
    assert first_summary.blockers == []
    assert first_summary.source_event_count == 2

    waiting_turn = turn_runner_service.start_turn(
        session_id,
        TurnStartRequest(
            input_message="Look up the probate filing",
            tool_calls=[
                TurnToolCallRecord(
                    id="call_1",
                    tool_name="lookup_probate_case",
                    arguments={"county": "Harris", "cause_number": "2024-12345"},
                )
            ],
        ),
    )

    second_summary = compaction_service.get_session_summary(session_id)
    assert second_summary is not None
    assert second_summary.summary_version == 2
    assert second_summary.compacted_turn_count == 2
    assert second_summary.pending_work == ["Await tool results for lookup_probate_case"]
    assert second_summary.turns[-1].turn_id == waiting_turn.id
    assert second_summary.turns[-1].tool_interactions[0].tool_name == "lookup_probate_case"
    assert second_summary.turns[-1].tool_interactions[0].result is None

    turn_runner_service.resume_turn(
        session_id,
        waiting_turn.id,
        TurnResumeRequest(
            assistant_message="Probate filing located and attached to the case notes.",
            tool_results=[
                TurnToolResultRecord(
                    tool_call_id="call_1",
                    output={"status": "found", "filing_date": "2024-05-01"},
                    success=True,
                )
            ],
        ),
    )

    third_summary = compaction_service.get_session_summary(session_id)
    assert third_summary is not None
    assert third_summary.summary_version == 3
    assert third_summary.compacted_turn_count == 2
    assert third_summary.pending_work == []
    assert third_summary.completed_work == [
        "Outreach plan confirmed and queued.",
        "Probate filing located and attached to the case notes.",
    ]
    assert third_summary.source_event_count == 8
    assert third_summary.turns[-1].tool_interactions[0].result is not None
    assert third_summary.turns[-1].tool_interactions[0].result.output == {
        "status": "found",
        "filing_date": "2024-05-01",
    }
    assert session_service.get_session(session_id).compaction.summary_version == 3


def test_session_journal_can_read_back_structured_memory_summary() -> None:
    reset_control_plane_state()
    session_id, turn_runner_service, session_service, _ = make_published_session()

    turn_runner_service.start_turn(
        session_id,
        TurnStartRequest(
            input_message="Capture the operator goals",
            assistant_message="Operator goals captured for the next outreach run.",
        ),
    )

    journal = session_service.get_session_journal(session_id)
    assert journal is not None
    assert journal.session_id == session_id
    assert journal.turn_count == 1
    assert journal.compaction.compacted_turn_count == 1
    assert journal.memory_summary is not None
    assert journal.memory_summary.turns[0].goals == ["Capture the operator goals"]
    assert journal.memory_summary.continuation_prompt.startswith("Continue session")