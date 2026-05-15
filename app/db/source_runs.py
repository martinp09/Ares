from __future__ import annotations

import os
import tempfile
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import get_settings
from app.models.commands import utc_now
from app.models.source_runs import MorningBrief, NightlySourcePullResponse, SourceRun, SourceRunArtifact, SourceRunStatus


class SourceRunsPersistenceError(ValueError):
    pass


class _SourceRunsRepositoryState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runs: dict[str, list[SourceRun]] = {}
    briefs: dict[str, list[MorningBrief]] = {}
    nightly_idempotency: dict[str, NightlySourcePullResponse] = {}
    brief_idempotency: dict[str, MorningBrief] = {}


class SourceRunsRepository:
    def __init__(self, *, state_path: str | Path | None = None) -> None:
        self._runs: dict[str, list[SourceRun]] = defaultdict(list)
        self._briefs: dict[str, list[MorningBrief]] = defaultdict(list)
        self._nightly_idempotency: dict[str, NightlySourcePullResponse] = {}
        self._brief_idempotency: dict[str, MorningBrief] = {}
        self._lock = RLock()
        self._state_path = Path(state_path).expanduser() if state_path else None

    def start_run(self, run: SourceRun) -> SourceRun:
        with self._locked_state():
            now = utc_now()
            stored = run.model_copy(update={"status": SourceRunStatus.RUNNING, "started_at": run.started_at or now})
            self._runs[_scope_key(stored.business_id, stored.environment)].append(stored)
            self._persist_state_unlocked()
            return stored.model_copy(deep=True)

    def attach_artifact(self, run_id: str, artifact: SourceRunArtifact) -> SourceRun:
        with self._locked_state():
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
            self._persist_state_unlocked()
            return updated.model_copy(deep=True)

    def complete_run(self, run_id: str, *, record_count: int | None = None, warnings: list[str] | None = None) -> SourceRun:
        with self._locked_state():
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
            self._persist_state_unlocked()
            return updated.model_copy(deep=True)

    def fail_run(self, run_id: str, *, error_message: str, warnings: list[str] | None = None) -> SourceRun:
        with self._locked_state():
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
            self._persist_state_unlocked()
            return updated.model_copy(deep=True)

    def list_runs(
        self,
        *,
        business_id: str,
        environment: str,
        limit: int | None = None,
        source_lane: str | None = None,
    ) -> list[SourceRun]:
        with self._locked_state(read_only=True):
            runs = list(self._runs.get(_scope_key(business_id, environment), []))
            if source_lane:
                runs = [run for run in runs if run.source_lane == source_lane]
            runs = sorted(runs, key=lambda run: run.started_at or run.completed_at or utc_now(), reverse=True)
            if limit is not None:
                runs = runs[:limit]
            return [run.model_copy(deep=True) for run in runs]

    def save_brief(self, brief: MorningBrief) -> MorningBrief:
        with self._locked_state():
            self._briefs[_scope_key(brief.business_id, brief.environment)].append(brief)
            self._persist_state_unlocked()
            return brief.model_copy(deep=True)

    def get_nightly_response_by_idempotency_key(
        self, *, business_id: str, environment: str, idempotency_key: str
    ) -> NightlySourcePullResponse | None:
        with self._locked_state(read_only=True):
            result = self._nightly_idempotency.get(_idempotency_key(business_id, environment, idempotency_key))
            if result is None:
                return None
            return result.model_copy(deep=True)

    def save_nightly_response_for_idempotency_key(
        self, *, idempotency_key: str, response: NightlySourcePullResponse
    ) -> NightlySourcePullResponse:
        with self._locked_state():
            self._nightly_idempotency[
                _idempotency_key(response.morning_brief.business_id, response.morning_brief.environment, idempotency_key)
            ] = response
            self._persist_state_unlocked()
            return response.model_copy(deep=True)

    def get_brief_by_idempotency_key(
        self, *, business_id: str, environment: str, idempotency_key: str
    ) -> MorningBrief | None:
        with self._locked_state(read_only=True):
            result = self._brief_idempotency.get(_idempotency_key(business_id, environment, idempotency_key))
            if result is None:
                return None
            return result.model_copy(deep=True)

    def save_brief_for_idempotency_key(self, *, idempotency_key: str, brief: MorningBrief) -> MorningBrief:
        with self._locked_state():
            self._brief_idempotency[_idempotency_key(brief.business_id, brief.environment, idempotency_key)] = brief
            self._persist_state_unlocked()
            return brief.model_copy(deep=True)

    def latest_brief(self, *, business_id: str, environment: str) -> MorningBrief | None:
        with self._locked_state(read_only=True):
            briefs = self._briefs.get(_scope_key(business_id, environment), [])
            if not briefs:
                return None
            return max(briefs, key=lambda brief: brief.generated_at).model_copy(deep=True)

    def reset(self) -> None:
        with self._locked_state(skip_load=True):
            self._runs.clear()
            self._briefs.clear()
            self._nightly_idempotency.clear()
            self._brief_idempotency.clear()
            self._persist_state_unlocked()

    @contextmanager
    def _locked_state(self, *, read_only: bool = False, skip_load: bool = False) -> Iterator[None]:
        with self._lock:
            with self._file_lock():
                if not skip_load:
                    self._load_state_unlocked()
                yield
                if not read_only:
                    self._persist_state_unlocked()

    @contextmanager
    def _file_lock(self) -> Iterator[None]:
        if self._state_path is None:
            yield
            return

        import fcntl

        lock_path = self._state_path.with_suffix(f"{self._state_path.suffix}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load_state_unlocked(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            return
        try:
            state = _SourceRunsRepositoryState.model_validate_json(self._state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, ValidationError) as exc:
            raise SourceRunsPersistenceError(f"Corrupted source-runs repository state at {self._state_path}") from exc
        self._runs = defaultdict(list, {key: [run.model_copy(deep=True) for run in value] for key, value in state.runs.items()})
        self._briefs = defaultdict(
            list, {key: [brief.model_copy(deep=True) for brief in value] for key, value in state.briefs.items()}
        )
        self._nightly_idempotency = {
            key: response.model_copy(deep=True) for key, response in state.nightly_idempotency.items()
        }
        self._brief_idempotency = {key: brief.model_copy(deep=True) for key, brief in state.brief_idempotency.items()}

    def _persist_state_unlocked(self) -> None:
        if self._state_path is None:
            return
        state = _SourceRunsRepositoryState(
            runs=dict(self._runs),
            briefs=dict(self._briefs),
            nightly_idempotency=dict(self._nightly_idempotency),
            brief_idempotency=dict(self._brief_idempotency),
        )
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = state.model_dump_json(indent=2)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._state_path.parent, delete=False) as handle:
            handle.write(payload)
            handle.write("\n")
            temp_path = Path(handle.name)
        os.replace(temp_path, self._state_path)

    def _find_run(self, run_id: str) -> SourceRun:
        for runs in self._runs.values():
            for run in runs:
                if run.id == run_id:
                    return run
        raise KeyError(run_id)

    def _replace_run(self, updated: SourceRun) -> None:
        key = _scope_key(updated.business_id, updated.environment)
        self._runs[key] = [updated if run.id == updated.id else run for run in self._runs[key]]


def build_source_runs_repository() -> SourceRunsRepository:
    settings = get_settings()
    return SourceRunsRepository(state_path=settings.lead_machine_source_runs_state_path)


source_runs_repository = build_source_runs_repository()


def _scope_key(business_id: str, environment: str) -> str:
    return f"{business_id}\u001f{environment}"


def _idempotency_key(business_id: str, environment: str, idempotency_key: str) -> str:
    return f"{business_id}\u001f{environment}\u001f{idempotency_key}"


def _unique_warnings(warnings: list[object]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in warnings if item))
