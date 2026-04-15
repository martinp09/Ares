from __future__ import annotations

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
    ) -> SkillRecord:
        now = utc_now()
        lookup_key = self._normalize_name(name)
        with self.client.transaction() as store:
            existing_id = store.skill_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.skills[existing_id]
                updated = existing.model_copy(
                    update={
                        "name": name,
                        "description": description,
                        "input_schema": dict(input_schema or {}),
                        "output_schema": dict(output_schema or {}),
                        "required_tools": list(required_tools or []),
                        "updated_at": now,
                    }
                )
                store.skills[existing_id] = updated
                return updated

            record = SkillRecord(
                id=generate_id("skl"),
                name=name,
                description=description,
                input_schema=dict(input_schema or {}),
                output_schema=dict(output_schema or {}),
                required_tools=list(required_tools or []),
                created_at=now,
                updated_at=now,
            )
            store.skills[record.id] = record
            store.skill_keys[lookup_key] = record.id
            return record

    def get(self, skill_id: str) -> SkillRecord | None:
        with self.client.transaction() as store:
            return store.skills.get(skill_id)

    def get_by_name(self, name: str) -> SkillRecord | None:
        with self.client.transaction() as store:
            skill_id = store.skill_keys.get(self._normalize_name(name))
            if skill_id is None:
                return None
            return store.skills.get(skill_id)

    def list(self) -> list[SkillRecord]:
        with self.client.transaction() as store:
            records = list(store.skills.values())
        records.sort(key=lambda record: record.name)
        return records

    def list_by_ids(self, skill_ids: list[str]) -> list[SkillRecord]:
        with self.client.transaction() as store:
            return [store.skills[skill_id] for skill_id in skill_ids if skill_id in store.skills]

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.strip().lower()
