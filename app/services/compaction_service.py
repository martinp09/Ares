from __future__ import annotations

from collections.abc import Iterable

from app.db.sessions import SessionsRepository
from app.db.turn_events import TurnEventsRepository
from app.models.session_journal import (
    SessionCompactedTurn,
    SessionJournalRecord,
    SessionMemorySummary,
    SessionToolInteractionSummary,
    SessionToolResultSummary,
)
from app.models.turns import TurnRecord, TurnStatus


class CompactionService:
    def __init__(
        self,
        sessions_repository: SessionsRepository | None = None,
        turn_events_repository: TurnEventsRepository | None = None,
    ) -> None:
        self.sessions_repository = sessions_repository or SessionsRepository()
        self.turn_events_repository = turn_events_repository or TurnEventsRepository()

    def refresh_session_summary(self, session_id: str) -> SessionMemorySummary | None:
        session = self.sessions_repository.get(session_id)
        if session is None:
            raise ValueError("Session not found")

        turns = self.turn_events_repository.list_turns_for_session(session_id)
        if not turns:
            return self.sessions_repository.get_memory_summary(session_id)

        compacted_turns = [self._compact_turn(turn) for turn in turns]
        source_event_count = sum(len(self.turn_events_repository.get_turn_events(turn.id)) for turn in turns)
        current_summary = self.sessions_repository.get_memory_summary(session_id)
        summary_version = 1 if current_summary is None else current_summary.summary_version + 1
        last_turn = turns[-1]

        summary = SessionMemorySummary(
            session_id=session_id,
            summary_version=summary_version,
            compacted_turn_ids=[turn.id for turn in turns],
            compacted_turn_count=len(turns),
            compacted_through_turn_id=last_turn.id,
            compacted_through_turn_number=last_turn.turn_number,
            source_event_count=source_event_count,
            goals=self._unique_items(item for turn in compacted_turns for item in turn.goals),
            completed_work=self._unique_items(item for turn in compacted_turns for item in turn.completed_work),
            pending_work=self._unique_items(item for turn in compacted_turns for item in turn.pending_work),
            blockers=self._unique_items(item for turn in compacted_turns for item in turn.blockers),
            turns=compacted_turns,
            continuation_prompt="",
            updated_at=last_turn.updated_at,
        )
        summary.continuation_prompt = self._build_continuation_prompt(summary)
        return self.sessions_repository.upsert_memory_summary(summary)

    def get_session_summary(self, session_id: str) -> SessionMemorySummary | None:
        return self.sessions_repository.get_memory_summary(session_id)

    def get_session_journal(self, session_id: str) -> SessionJournalRecord | None:
        session = self.sessions_repository.get(session_id)
        if session is None:
            return None
        turns = self.turn_events_repository.list_turns_for_session(session_id)
        return SessionJournalRecord(
            session_id=session.id,
            agent_id=session.agent_id,
            agent_revision_id=session.agent_revision_id,
            org_id=session.org_id,
            business_id=session.business_id,
            environment=session.environment,
            status=session.status.value,
            timeline_length=len(session.timeline),
            turn_count=len(turns),
            compaction=session.compaction,
            memory_summary=self.sessions_repository.get_memory_summary(session_id),
        )

    def _compact_turn(self, turn: TurnRecord) -> SessionCompactedTurn:
        tool_results_by_id = {result.tool_call_id: result for result in turn.tool_results}
        tool_interactions = [
            SessionToolInteractionSummary(
                tool_call_id=tool_call.id,
                tool_name=tool_call.tool_name,
                arguments=dict(tool_call.arguments),
                result=(
                    SessionToolResultSummary(
                        success=tool_results_by_id[tool_call.id].success,
                        output=dict(tool_results_by_id[tool_call.id].output),
                    )
                    if tool_call.id in tool_results_by_id
                    else None
                ),
            )
            for tool_call in turn.tool_calls
        ]

        pending_work: list[str] = []
        if turn.status == TurnStatus.WAITING_FOR_TOOL and turn.tool_calls:
            pending_work.append(f"Await tool results for {', '.join(tool_call.tool_name for tool_call in turn.tool_calls)}")
        elif turn.status == TurnStatus.RUNNING:
            pending_work.append("Turn execution is still in progress")

        blockers: list[str] = []
        if turn.status == TurnStatus.FAILED:
            blocker = turn.metadata.get("error_message") or turn.assistant_message or "Turn failed"
            blockers.append(str(blocker))

        completed_work: list[str] = []
        if turn.status == TurnStatus.COMPLETED and turn.assistant_message:
            completed_work.append(turn.assistant_message)

        goals: list[str] = []
        if turn.input_message:
            goals.append(turn.input_message)

        return SessionCompactedTurn(
            turn_id=turn.id,
            turn_number=turn.turn_number,
            status=turn.status,
            input_message=turn.input_message,
            assistant_message=turn.assistant_message,
            metadata=dict(turn.metadata),
            goals=goals,
            completed_work=completed_work,
            pending_work=pending_work,
            blockers=blockers,
            tool_interactions=tool_interactions,
        )

    def _build_continuation_prompt(self, summary: SessionMemorySummary) -> str:
        lines = [f"Continue session {summary.session_id} using the structured memory below."]
        lines.extend(self._format_section("Goals", summary.goals))
        lines.extend(self._format_section("Completed work", summary.completed_work))
        lines.extend(self._format_section("Pending work", summary.pending_work))
        lines.extend(self._format_section("Blockers", summary.blockers))

        if summary.turns:
            lines.append("Recent compacted turns:")
            for turn in summary.turns[-3:]:
                lines.append(f"- Turn {turn.turn_number} [{turn.status.value}]: {turn.input_message or 'No operator input'}")
                for tool_interaction in turn.tool_interactions:
                    tool_state = "pending"
                    if tool_interaction.result is not None:
                        tool_state = "success" if tool_interaction.result.success else "failed"
                    lines.append(f"  - Tool {tool_interaction.tool_name} ({tool_state})")
        return "\n".join(lines)

    @staticmethod
    def _format_section(title: str, items: list[str]) -> list[str]:
        lines = [f"{title}:"]
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- none")
        return lines

    @staticmethod
    def _unique_items(items: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in items:
            value = item.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered
