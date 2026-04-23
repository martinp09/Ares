from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.agent_installs import AgentInstallRecord
from app.models.commands import generate_id


class AgentInstallsRepository:
    def __init__(self, client: ControlPlaneClient | None = None) -> None:
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        org_id: str,
        catalog_entry_id: str,
        source_agent_id: str,
        source_agent_revision_id: str,
        installed_agent_id: str,
        installed_agent_revision_id: str,
        business_id: str,
        environment: str,
    ) -> AgentInstallRecord:
        now = utc_now()
        with self.client.transaction() as store:
            record = AgentInstallRecord(
                id=generate_id("ins"),
                org_id=org_id,
                catalog_entry_id=catalog_entry_id,
                source_agent_id=source_agent_id,
                source_agent_revision_id=source_agent_revision_id,
                installed_agent_id=installed_agent_id,
                installed_agent_revision_id=installed_agent_revision_id,
                business_id=business_id,
                environment=environment,
                created_at=now,
                updated_at=now,
            )
            store.agent_installs[record.id] = record
            store.agent_install_ids_by_org.setdefault(org_id, []).append(record.id)
            return record

    def get(self, install_id: str) -> AgentInstallRecord | None:
        with self.client.transaction() as store:
            install = store.agent_installs.get(install_id)
            return install if install is None else AgentInstallRecord.model_validate(install)

    def list(self, *, org_id: str | None = None) -> list[AgentInstallRecord]:
        with self.client.transaction() as store:
            if org_id is None:
                installs = list(store.agent_installs.values())
            else:
                install_ids = store.agent_install_ids_by_org.get(org_id, [])
                installs = [store.agent_installs[install_id] for install_id in install_ids]
        return sorted(installs, key=lambda install: (install.created_at, install.id))
