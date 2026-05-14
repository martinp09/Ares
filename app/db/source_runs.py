from __future__ import annotations

from collections import defaultdict
from threading import RLock

from app.models.commands import utc_now
from app.models.source_runs import MorningBrief, NightlySourcePullResponse, SourceRun, SourceRunArtifact, SourceRunStatus


class SourceRunsRepository:
    def __init__(self) -> None:
        self._runs: dict[tuple[str, str], list[SourceRun]] = defaultdict(list)
        self._briefs: dict[tuple[str, str], list[MorningBrief]] = defaultdict(list)
        self._nightly_idempotency: dict[tuple[str, str, str], NightlySourcePullResponse] = {}
        self._brief_idempotency: dict[tuple[str, str, str], MorningBrief] = {}
        self._lock = RLock()

    def start_run(self, run: SourceRun) -> SourceRun:
        with self._lock:
            now = utc_now()
            stored = run.model_copy(update={"status": SourceRunStatus.RUNNING, "started_at": run.started_at or now})
            self._runs[(stored.business_id, stored.environment)].append(stored)
            return stored.model_copy(deep=True)

    def attach_artifact(self, run_id: str, artifact: SourceRunArtifact) -> SourceRun:
        with self._lock:
            run = self._find_run(run_id)
            artifacts = [*run.artifacts, artifact]
            warning_count = sum(len(item.warnings) for item in artifacts) + len(_unique_warnings(run.metadata.get("warnings", [])))
            updated = run.model_copy(
                update={
                    "artifacts": artifacts,
                    "artifact_count": len(artifacts),
                    "record_count": sum(item.record_count for item in artifacts),
                    "warning_count": warning_count,
                }
            )
            self._replace_run(updated)
            return updated.model_copy(deep=True)

    def complete_run(self, run_id: str, *, record_count: int | None = None, warnings: list[str] | None = None) -> SourceRun:
        with self._lock:
            run = self._find_run(run_id)
            run_warnings = _unique_warnings([*run.metadata.get("warnings", []), *(warnings or [])])
            artifacts_warning_count = sum(len(item.warnings) for item in run.artifacts)
            update = {
                "status": SourceRunStatus.COMPLETED,
                "completed_at": utc_now(),
                "record_count": run.record_count if record_count is None else record_count,
                "warning_count": artifacts_warning_count + len(run_warnings),
                "metadata": {**run.metadata, "warnings": run_warnings},
            }
            updated = run.model_copy(update=update)
            self._replace_run(updated)
            return updated.model_copy(deep=True)

    def fail_run(self, run_id: str, *, error_message: str, warnings: list[str] | None = None) -> SourceRun:
        with self._lock:
            run = self._find_run(run_id)
            run_warnings = _unique_warnings([*run.metadata.get("warnings", []), *(warnings or [])])
            updated = run.model_copy(
                update={
                    "status": SourceRunStatus.FAILED,
                    "completed_at": utc_now(),
                    "warning_count": sum(len(item.warnings) for item in run.artifacts) + len(run_warnings),
                    "error_message": error_message,
                    "metadata": {**run.metadata, "warnings": run_warnings},
                }
            )
            self._replace_run(updated)
            return updated.model_copy(deep=True)

    def list_runs(
        self,
        *,
        business_id: str,
        environment: str,
        limit: int | None = None,
        source_lane: str | None = None,
    ) -> list[SourceRun]:
        with self._lock:
            runs = list(self._runs.get((business_id, environment), []))
            if source_lane:
                runs = [run for run in runs if run.source_lane == source_lane]
            runs = sorted(runs, key=lambda run: run.started_at or run.completed_at or utc_now(), reverse=True)
            if limit is not None:
                runs = runs[:limit]
            return [run.model_copy(deep=True) for run in runs]

    def save_brief(self, brief: MorningBrief) -> MorningBrief:
        with self._lock:
            self._briefs[(brief.business_id, brief.environment)].append(brief)
            return brief.model_copy(deep=True)

    def get_nightly_response_by_idempotency_key(
        self, *, business_id: str, environment: str, idempotency_key: str
    ) -> NightlySourcePullResponse | None:
        with self._lock:
            result = self._nightly_idempotency.get((business_id, environment, idempotency_key))
            if result is None:
                return None
            return result.model_copy(deep=True)

    def save_nightly_response_for_idempotency_key(
        self, *, idempotency_key: str, response: NightlySourcePullResponse
    ) -> NightlySourcePullResponse:
        with self._lock:
            self._nightly_idempotency[
                (response.morning_brief.business_id, response.morning_brief.environment, idempotency_key)
            ] = response
            return response.model_copy(deep=True)

    def get_brief_by_idempotency_key(
        self, *, business_id: str, environment: str, idempotency_key: str
    ) -> MorningBrief | None:
        with self._lock:
            result = self._brief_idempotency.get((business_id, environment, idempotency_key))
            if result is None:
                return None
            return result.model_copy(deep=True)

    def save_brief_for_idempotency_key(self, *, idempotency_key: str, brief: MorningBrief) -> MorningBrief:
        with self._lock:
            self._brief_idempotency[(brief.business_id, brief.environment, idempotency_key)] = brief
            return brief.model_copy(deep=True)

    def latest_brief(self, *, business_id: str, environment: str) -> MorningBrief | None:
        with self._lock:
            briefs = self._briefs.get((business_id, environment), [])
            if not briefs:
                return None
            return max(briefs, key=lambda brief: brief.generated_at).model_copy(deep=True)

    def reset(self) -> None:
        with self._lock:
            self._runs.clear()
            self._briefs.clear()
            self._nightly_idempotency.clear()
            self._brief_idempotency.clear()

    def _find_run(self, run_id: str) -> SourceRun:
        for runs in self._runs.values():
            for run in runs:
                if run.id == run_id:
                    return run
        raise KeyError(run_id)

    def _replace_run(self, updated: SourceRun) -> None:
        key = (updated.business_id, updated.environment)
        self._runs[key] = [updated if run.id == updated.id else run for run in self._runs[key]]


source_runs_repository = SourceRunsRepository()


def _unique_warnings(warnings: list[object]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in warnings if item))
