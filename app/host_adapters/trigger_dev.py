from __future__ import annotations

from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.host_adapters.base import HostAdapter
from app.models.host_adapters import (
    HostAdapterArtifactReportRequest,
    HostAdapterArtifactReportResult,
    HostAdapterCapabilityRecord,
    HostAdapterDispatchRequest,
    HostAdapterDispatchResult,
    HostAdapterDispatchStatus,
    HostAdapterKind,
    HostAdapterStatusCorrelationRequest,
    HostAdapterStatusCorrelationResult,
)


class TriggerDevHostAdapter(HostAdapter):
    kind = HostAdapterKind.TRIGGER_DEV
    enabled = True
    display_name = "Trigger.dev"
    description = "Current in-memory host adapter seam backed by Trigger.dev-style dispatch callbacks"

    def __init__(self, dispatches_repository: HostAdapterDispatchesRepository | None = None):
        self.dispatches_repository = dispatches_repository or HostAdapterDispatchesRepository()

    @property
    def capabilities(self) -> HostAdapterCapabilityRecord:
        return HostAdapterCapabilityRecord(
            dispatch=True,
            status_correlation=True,
            artifact_reporting=True,
            cancellation=False,
        )

    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        external_reference = request.run_id
        record = self.dispatches_repository.create(
            adapter_kind=self.kind,
            agent_id=request.agent_id,
            agent_revision_id=request.agent_revision_id,
            business_id=request.business_id,
            environment=request.environment,
            skill_ids=[skill.id for skill in request.skills],
            host_adapter_config=request.host_adapter_config,
            payload=request.payload,
            status=HostAdapterDispatchStatus.ACCEPTED,
            run_id=request.run_id,
            session_id=request.session_id,
            external_reference=external_reference,
        )
        return HostAdapterDispatchResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            status=HostAdapterDispatchStatus.ACCEPTED,
            dispatch_id=record.id,
            external_reference=external_reference,
            correlation=self.correlation_from_request(
                request,
                dispatch_id=record.id,
                external_reference=external_reference,
            ),
        )

    def correlate_status(self, request: HostAdapterStatusCorrelationRequest) -> HostAdapterStatusCorrelationResult:
        if request.dispatch_id is None and request.run_id is None and request.external_reference is None:
            return HostAdapterStatusCorrelationResult(
                adapter_kind=self.kind,
                enabled=self.enabled,
                supported=False,
                message="trigger_dev adapter correlation requires dispatch_id, run_id, or external_reference",
            )
        correlation = self._build_correlation(
            dispatch_id=request.dispatch_id,
            run_id=request.run_id,
            session_id=request.session_id,
            external_reference=request.external_reference if request.external_reference is not None else request.run_id,
            adapter_reference=request.adapter_reference,
            adapter_details=request.adapter_details,
        )
        return HostAdapterStatusCorrelationResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            supported=True,
            correlation=correlation,
        )

    def report_artifact(self, request: HostAdapterArtifactReportRequest) -> HostAdapterArtifactReportResult:
        return HostAdapterArtifactReportResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            supported=True,
            accepted=True,
            correlation=request.correlation.model_copy(deep=True),
            artifact=request.artifact.model_copy(deep=True),
        )
