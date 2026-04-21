from __future__ import annotations

from collections.abc import Iterable, Mapping

from app.domains.ares.agent_registry import AresAgentRevisionSpec, AresVersionedAgentRecord


class AresAgentRegistryService:
    def __init__(self, records: Iterable[AresVersionedAgentRecord] | None = None) -> None:
        self._records_by_name: dict[str, AresVersionedAgentRecord] = {}
        for record in records or ():
            self._records_by_name[record.name] = record

    def register_revision(
        self,
        *,
        name: str,
        purpose: str,
        revision: str,
        allowed_tools: Iterable[str],
        risk_policy: str,
        output_contract: str,
        set_active: bool = True,
    ) -> AresVersionedAgentRecord:
        revision_spec = AresAgentRevisionSpec(
            revision=revision,
            allowed_tools=tuple(allowed_tools),
            risk_policy=risk_policy,
            output_contract=output_contract,
        )
        existing = self._records_by_name.get(name)

        revisions_by_id: dict[str, AresAgentRevisionSpec] = {}
        if existing is not None:
            for existing_revision in existing.revisions:
                revisions_by_id[existing_revision.revision] = existing_revision
            active_revision = existing.active_revision
        else:
            active_revision = revision

        existing_revision = revisions_by_id.get(revision_spec.revision)
        if existing_revision is not None:
            if existing_revision != revision_spec:
                raise ValueError(f"Agent revision {name}:{revision_spec.revision} is immutable")
            if existing is not None and existing.purpose != purpose:
                raise ValueError(f"Agent purpose for {name} is immutable once a revision is registered")

        revisions_by_id[revision_spec.revision] = existing_revision or revision_spec
        ordered_revisions = tuple(revisions_by_id[key] for key in sorted(revisions_by_id))

        if set_active or existing is None:
            active_revision = revision_spec.revision

        record = AresVersionedAgentRecord(
            name=name,
            purpose=purpose,
            revisions=ordered_revisions,
            active_revision=active_revision,
        )
        self._records_by_name[name] = record
        return record

    def get_agent(self, name: str) -> AresVersionedAgentRecord | None:
        return self._records_by_name.get(name)

    def list_agents(self) -> list[AresVersionedAgentRecord]:
        return [self._records_by_name[name] for name in sorted(self._records_by_name)]

    def export_snapshot(self) -> list[dict[str, object]]:
        return [record.model_dump(mode="json") for record in self.list_agents()]

    @classmethod
    def from_snapshot(cls, snapshot: Iterable[Mapping[str, object]]) -> "AresAgentRegistryService":
        records = [AresVersionedAgentRecord.model_validate(item) for item in snapshot]
        return cls(records=records)
