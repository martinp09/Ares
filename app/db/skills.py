from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.skills import SkillRecord


class SkillsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def register(
        self,
        *,
        name: str,
        description: str | None = None,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        required_tools: list[str] | None = None,
        permission_requirements: list[str] | None = None,
    ) -> SkillRecord:
        now = utc_now()
        lookup_key = self._normalize_name(name)
        with self.client.transaction() as store:
            existing_id = store.skill_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.skills[existing_id]
                updated = SkillRecord.model_validate(
                    {
                        **existing.model_dump(mode="python"),
                        "name": name,
                        "description": description,
                        "input_schema": deepcopy(input_schema or {}),
                        "output_schema": deepcopy(output_schema or {}),
                        "required_tools": deepcopy(required_tools or []),
                        "permission_requirements": deepcopy(permission_requirements or []),
                        "updated_at": now,
                    }
                )
                store.skills[existing_id] = updated
                return updated.model_copy(deep=True)

            record = SkillRecord(
                id=generate_id("skl"),
                name=name,
                description=description,
                input_schema=deepcopy(input_schema or {}),
                output_schema=deepcopy(output_schema or {}),
                required_tools=deepcopy(required_tools or []),
                permission_requirements=deepcopy(permission_requirements or []),
                created_at=now,
                updated_at=now,
            )
            store.skills[record.id] = record
            store.skill_keys[lookup_key] = record.id
            return record.model_copy(deep=True)

    def get(self, skill_id: str) -> SkillRecord | None:
        with self.client.transaction() as store:
            record = store.skills.get(skill_id)
        return None if record is None else record.model_copy(deep=True)

    def get_by_name(self, name: str) -> SkillRecord | None:
        with self.client.transaction() as store:
            skill_id = store.skill_keys.get(self._normalize_name(name))
            if skill_id is None:
                return None
            record = store.skills.get(skill_id)
        return None if record is None else record.model_copy(deep=True)

    def list(self) -> list[SkillRecord]:
        with self.client.transaction() as store:
            records = [record.model_copy(deep=True) for record in store.skills.values()]
        records.sort(key=lambda record: record.name)
        return records

    def list_by_ids(self, skill_ids: list[str]) -> list[SkillRecord]:
        with self.client.transaction() as store:
            return [store.skills[skill_id].model_copy(deep=True) for skill_id in skill_ids if skill_id in store.skills]

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip().lower()
