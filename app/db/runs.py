from __future__ import annotations

from datetime import datetime

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import CommandPolicy, generate_id
from app.models.runs import RunRecord, RunStatus


class RunsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        command_id: str,
        business_id: str,
        environment: str,
        command_type: str,
        command_policy: CommandPolicy,
        status: RunStatus = RunStatus.QUEUED,
        parent_run_id: str | None = None,
        replay_reason: str | None = None,
        trigger_run_id: str | None = None,
        created_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_classification: str | None = None,
        error_message: str | None = None,
    ) -> RunRecord:
        now = created_at or utc_now()
        run = RunRecord(
            id=generate_id("run"),
            command_id=command_id,
            business_id=business_id,
            environment=environment,
            command_type=command_type,
            command_policy=command_policy,
            status=status,
            created_at=now,
            updated_at=now,
            trigger_run_id=trigger_run_id,
            parent_run_id=parent_run_id,
            replay_reason=replay_reason,
            started_at=started_at,
            completed_at=completed_at,
            error_classification=error_classification,
            error_message=error_message,
            artifacts=[],
            events=[],
        )
        with self.client.transaction() as store:
            store.runs[run.id] = run
        return run

    def get(self, run_id: str) -> RunRecord | None:
        with self.client.transaction() as store:
            return store.runs.get(run_id)
