from __future__ import annotations

from app.db.skills import SkillsRepository
from app.models.skills import SkillRecord


class SkillRegistryService:
    def __init__(self, skills_repository: SkillsRepository | None = None) -> None:
        self.skills_repository = skills_repository or SkillsRepository()

    def register_skill(
        self,
        *,
        name: str,
        description: str | None = None,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        required_tools: list[str] | None = None,
        permission_requirements: list[str] | None = None,
    ) -> SkillRecord:
        return self.skills_repository.register(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            required_tools=required_tools,
            permission_requirements=permission_requirements,
        )

    def get_skill(self, skill_id: str) -> SkillRecord | None:
        return self.skills_repository.get(skill_id)

    def list_skills(self) -> list[SkillRecord]:
        return self.skills_repository.list()

    def resolve_skills(self, skill_ids: list[str]) -> list[SkillRecord]:
        skills = self.skills_repository.list_by_ids(skill_ids)
        if len(skills) != len(skill_ids):
            found_ids = {skill.id for skill in skills}
            missing_ids: list[str] = []
            for skill_id in skill_ids:
                if skill_id in found_ids or skill_id in missing_ids:
                    continue
                missing_ids.append(skill_id)
            raise ValueError(f"Unknown skill ids: {', '.join(missing_ids)}")
        return skills


skill_registry_service = SkillRegistryService()
