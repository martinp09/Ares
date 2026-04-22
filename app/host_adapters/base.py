from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.host_adapters import (
    HostAdapterArtifactReportRequest,
    HostAdapterArtifactReportResult,
    HostAdapterCancellationRequest,
    HostAdapterCancellationResult,
    HostAdapterCapabilityRecord,
    HostAdapterCorrelationRecord,
    HostAdapterDispatchRequest,
    HostAdapterDispatchResult,
    HostAdapterDispatchStatus,
    HostAdapterKind,
    HostAdapterRecord,
    HostAdapterStatusCorrelationRequest,
    HostAdapterStatusCorrelationResult,
)


class HostAdapter(ABC):
    kind: HostAdapterKind
    enabled: bool = False
    display_name: str | None = None
    description: str | None = None
    adapter_details_label: str = "Adapter details"
    disabled_reason: str | None = None

    @property
    def capabilities(self) -> HostAdapterCapabilityRecord:
        return HostAdapterCapabilityRecord(dispatch=self.enabled)

    def describe(self) -> HostAdapterRecord:
        return HostAdapterRecord(
            kind=self.kind,
            enabled=self.enabled,
            display_name=self.display_name or self.kind.value.replace("_", " ").title(),
            description=self.description,
            adapter_details_label=self.adapter_details_label,
            capabilities=self.capabilities,
            disabled_reason=self._resolved_disabled_reason(),
        )

    @abstractmethod
    def dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        raise NotImplementedError

    def correlate_status(self, request: HostAdapterStatusCorrelationRequest) -> HostAdapterStatusCorrelationResult:
        disabled_reason, message = self._unavailable_operation("status correlation")
        return HostAdapterStatusCorrelationResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            supported=False,
            correlation=self._build_correlation(
                dispatch_id=request.dispatch_id,
                run_id=request.run_id,
                session_id=request.session_id,
                external_reference=request.external_reference,
                adapter_reference=request.adapter_reference,
                adapter_details=request.adapter_details,
            ),
            disabled_reason=disabled_reason,
            message=message,
        )

    def report_artifact(self, request: HostAdapterArtifactReportRequest) -> HostAdapterArtifactReportResult:
        disabled_reason, message = self._unavailable_operation("artifact reporting")
        return HostAdapterArtifactReportResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            supported=False,
            accepted=False,
            correlation=request.correlation.model_copy(deep=True),
            artifact=request.artifact.model_copy(deep=True),
            disabled_reason=disabled_reason,
            message=message,
        )

    def cancel(self, request: HostAdapterCancellationRequest) -> HostAdapterCancellationResult:
        disabled_reason, message = self._unavailable_operation("cancellation")
        return HostAdapterCancellationResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            supported=False,
            cancelled=False,
            correlation=request.correlation.model_copy(deep=True),
            disabled_reason=disabled_reason,
            message=message,
        )

    def disabled_dispatch(self, request: HostAdapterDispatchRequest) -> HostAdapterDispatchResult:
        reason = self._resolved_disabled_reason()
        return HostAdapterDispatchResult(
            adapter_kind=self.kind,
            enabled=self.enabled,
            status=HostAdapterDispatchStatus.DISABLED,
            correlation=self.correlation_from_request(request),
            disabled_reason=reason,
            message=reason,
        )

    def correlation_from_request(
        self,
        request: HostAdapterDispatchRequest,
        *,
        dispatch_id: str | None = None,
        external_reference: str | None = None,
        adapter_reference: str | None = None,
        adapter_details: dict[str, Any] | None = None,
    ) -> HostAdapterCorrelationRecord | None:
        return self._build_correlation(
            dispatch_id=dispatch_id,
            run_id=request.run_id,
            session_id=request.session_id,
            external_reference=external_reference if external_reference is not None else request.run_id,
            adapter_reference=adapter_reference,
            adapter_details=adapter_details,
        )

    def _build_correlation(
        self,
        *,
        dispatch_id: str | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
        external_reference: str | None = None,
        adapter_reference: str | None = None,
        adapter_details: dict[str, Any] | None = None,
    ) -> HostAdapterCorrelationRecord | None:
        if all(
            value is None for value in (dispatch_id, run_id, session_id, external_reference, adapter_reference)
        ) and not adapter_details:
            return None
        return HostAdapterCorrelationRecord(
            dispatch_id=dispatch_id,
            run_id=run_id,
            session_id=session_id,
            external_reference=external_reference,
            adapter_reference=adapter_reference,
            adapter_details=dict(adapter_details or {}),
        )

    def _unavailable_operation(self, operation: str) -> tuple[str | None, str]:
        disabled_reason = self._resolved_disabled_reason() if not self.enabled else None
        if disabled_reason is not None:
            return disabled_reason, disabled_reason
        return None, f"{self.kind.value} adapter does not support {operation}"

    def _resolved_disabled_reason(self) -> str | None:
        if self.enabled:
            return None
        return self.disabled_reason or f"{self.kind.value} adapter is disabled in this environment"
