from __future__ import annotations

from datetime import UTC, datetime

from app.db.artifacts import ArtifactsRepository
from app.db.commands import CommandsRepository
from app.db.events import EventsRepository
from app.db.runs import RunsRepository
from app.models.actors import ActorContext
from app.models.run_events import (
    ArtifactProducedCallbackRequest,
    RunCompletedCallbackRequest,
    RunFailedCallbackRequest,
    RunLifecycleEvent,
    RunLifecycleResponse,
    RunStartedCallbackRequest,
)
from app.models.runs import ReplayLineageContext, RunStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunLifecycleService:
    def __init__(
        self,
        runs_repository: RunsRepository | None = None,
        events_repository: EventsRepository | None = None,
        artifacts_repository: ArtifactsRepository | None = None,
        commands_repository: CommandsRepository | None = None,
    ) -> None:
        self.runs_repository = runs_repository or RunsRepository()
        self.events_repository = events_repository or EventsRepository()
        self.artifacts_repository = artifacts_repository or ArtifactsRepository()
        self.commands_repository = commands_repository or CommandsRepository()

    def mark_run_started(self, run_id: str, request: RunStartedCallbackRequest) -> RunLifecycleResponse | None:
        run = self.runs_repository.get(run_id)
        if run is None:
            return None

        started_at = request.started_at or utc_now()
        run.status = RunStatus.IN_PROGRESS
        run.started_at = started_at
        run.trigger_run_id = request.trigger_run_id or run.trigger_run_id
        run.updated_at = started_at
        self.runs_repository.save(run)
        self.events_repository.append(
            run_id,
            event_type=RunLifecycleEvent.RUN_STARTED.value,
            payload=request.model_dump(mode="json"),
            created_at=started_at,
        )
        return RunLifecycleResponse(
            run_id=run.id,
            event_type=RunLifecycleEvent.RUN_STARTED.value,
            status=run.status.value,
            trigger_run_id=run.trigger_run_id,
        )

    def mark_run_completed(
        self, run_id: str, request: RunCompletedCallbackRequest
    ) -> RunLifecycleResponse | None:
        run = self.runs_repository.get(run_id)
        if run is None:
            return None

        completed_at = request.completed_at or utc_now()
        run.status = RunStatus.COMPLETED
        run.completed_at = completed_at
        run.trigger_run_id = request.trigger_run_id or run.trigger_run_id
        run.updated_at = completed_at
        self.runs_repository.save(run)
        self.events_repository.append(
            run_id,
            event_type=RunLifecycleEvent.RUN_COMPLETED.value,
            payload=request.model_dump(mode="json"),
            created_at=completed_at,
        )
        return RunLifecycleResponse(
            run_id=run.id,
            event_type=RunLifecycleEvent.RUN_COMPLETED.value,
            status=run.status.value,
            trigger_run_id=run.trigger_run_id,
        )

    def mark_run_failed(self, run_id: str, request: RunFailedCallbackRequest) -> RunLifecycleResponse | None:
        run = self.runs_repository.get(run_id)
        if run is None:
            return None

        failed_at = request.completed_at or utc_now()
        run.status = RunStatus.FAILED
        run.completed_at = failed_at
        run.trigger_run_id = request.trigger_run_id or run.trigger_run_id
        run.error_classification = request.error_classification
        run.error_message = request.error_message
        run.updated_at = failed_at
        self.runs_repository.save(run)
        self.events_repository.append(
            run_id,
            event_type=RunLifecycleEvent.RUN_FAILED.value,
            payload=request.model_dump(mode="json"),
            created_at=failed_at,
        )
        return RunLifecycleResponse(
            run_id=run.id,
            event_type=RunLifecycleEvent.RUN_FAILED.value,
            status=run.status.value,
            trigger_run_id=run.trigger_run_id,
            error_classification=run.error_classification,
            error_message=run.error_message,
        )

    def record_replay_lineage(
        self,
        parent_run_id: str,
        *,
        replay_reason: str | None,
        triggering_actor: ActorContext,
        lineage: ReplayLineageContext,
        child_run_id: str | None = None,
        approval_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> dict[str, object] | None:
        parent_run = self.runs_repository.get(parent_run_id)
        if parent_run is None:
            return None

        event_created_at = occurred_at or utc_now()
        parent_payload = {
            "replay_reason": replay_reason,
            "requires_approval": approval_id is not None,
            "child_run_id": child_run_id,
            "approval_id": approval_id,
            "triggering_actor": lineage.triggering_actor.model_dump(mode="json"),
            "source": lineage.source.model_dump(mode="json") if lineage.source is not None else None,
            "replay": lineage.replay.model_dump(mode="json") if lineage.replay is not None else None,
        }
        self.events_repository.append(
            parent_run_id,
            event_type="replay_requested",
            payload=parent_payload,
            created_at=event_created_at,
        )
        if child_run_id is not None:
            self.record_replay_child_lineage(
                child_run_id,
                parent_run_id=parent_run_id,
                replay_reason=replay_reason,
                triggering_actor=triggering_actor,
                lineage=lineage,
                occurred_at=event_created_at,
            )
        return parent_payload

    def record_replay_child_lineage(
        self,
        child_run_id: str,
        *,
        parent_run_id: str,
        replay_reason: str | None,
        triggering_actor: ActorContext,
        lineage: ReplayLineageContext,
        occurred_at: datetime | None = None,
    ) -> dict[str, object] | None:
        child_run = self.runs_repository.get(child_run_id)
        if child_run is None:
            return None

        payload = {
            "parent_run_id": parent_run_id,
            "replay_reason": replay_reason,
            "triggering_actor": triggering_actor.model_dump(mode="json"),
            "source": lineage.source.model_dump(mode="json") if lineage.source is not None else None,
            "replay": lineage.replay.model_dump(mode="json") if lineage.replay is not None else None,
        }
        self.events_repository.append(
            child_run_id,
            event_type="replay_lineage_bound",
            payload=payload,
            created_at=occurred_at or utc_now(),
        )
        return payload

    def record_replay_parent_resolution(
        self,
        parent_run_id: str,
        *,
        child_run_id: str,
        approval_id: str | None,
        replay_reason: str | None,
        triggering_actor: ActorContext,
        lineage: ReplayLineageContext,
        occurred_at: datetime | None = None,
    ) -> dict[str, object] | None:
        parent_run = self.runs_repository.get(parent_run_id)
        if parent_run is None:
            return None

        payload = {
            "child_run_id": child_run_id,
            "approval_id": approval_id,
            "replay_reason": replay_reason,
            "triggering_actor": triggering_actor.model_dump(mode="json"),
            "source": lineage.source.model_dump(mode="json") if lineage.source is not None else None,
            "replay": lineage.replay.model_dump(mode="json") if lineage.replay is not None else None,
        }
        self.events_repository.append(
            parent_run_id,
            event_type="replay_child_bound",
            payload=payload,
            created_at=occurred_at or utc_now(),
        )
        return payload

    def record_artifact(
        self, run_id: str, request: ArtifactProducedCallbackRequest
    ) -> RunLifecycleResponse | None:
        run = self.runs_repository.get(run_id)
        if run is None:
            return None

        occurred_at = request.completed_at or utc_now()
        artifact = self.artifacts_repository.append(
            run_id,
            artifact_type=request.artifact_type,
            payload=request.payload,
            created_at=occurred_at,
        )
        if artifact is None:
            return None

        self.events_repository.append(
            run_id,
            event_type=RunLifecycleEvent.ARTIFACT_PRODUCED.value,
            payload=request.model_dump(mode="json"),
            created_at=occurred_at,
        )
        return RunLifecycleResponse(
            run_id=run.id,
            event_type=RunLifecycleEvent.ARTIFACT_PRODUCED.value,
            status=run.status.value,
            trigger_run_id=run.trigger_run_id,
            artifact_id=artifact["id"],
            artifact_type=artifact["artifact_type"],
        )


run_lifecycle_service = RunLifecycleService()
