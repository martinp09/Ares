from app.db.agent_installs import AgentInstallsRepository
from app.db.client import reset_control_plane_store


def test_agent_installs_repository_creates_and_lists_by_org() -> None:
    reset_control_plane_store()
    repository = AgentInstallsRepository()

    alpha_install = repository.create(
        org_id="org_alpha",
        catalog_entry_id="cat_alpha",
        source_agent_id="agt_source_alpha",
        source_agent_revision_id="rev_source_alpha",
        installed_agent_id="agt_installed_alpha",
        installed_agent_revision_id="rev_installed_alpha",
        business_id="limitless",
        environment="prod",
    )
    beta_install = repository.create(
        org_id="org_beta",
        catalog_entry_id="cat_beta",
        source_agent_id="agt_source_beta",
        source_agent_revision_id="rev_source_beta",
        installed_agent_id="agt_installed_beta",
        installed_agent_revision_id="rev_installed_beta",
        business_id="acq",
        environment="staging",
    )

    assert repository.get(alpha_install.id) == alpha_install
    assert [install.id for install in repository.list(org_id="org_alpha")] == [alpha_install.id]
    assert [install.id for install in repository.list(org_id="org_beta")] == [beta_install.id]
