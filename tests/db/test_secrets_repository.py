import pytest

from app.db.agents import AgentsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.secrets import SecretsRepository


def build_repositories() -> tuple[SecretsRepository, AgentsRepository]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return SecretsRepository(client), AgentsRepository(client)


def create_revision(
    agents_repository: AgentsRepository,
    *,
    org_id: str,
    requires_secrets: list[str],
) -> str:
    _, revision = agents_repository.create_agent(
        org_id=org_id,
        business_id="limitless",
        environment="dev",
        name=f"{org_id} secret agent",
        description=None,
        config={"prompt": "Handle secrets"},
        compatibility_metadata={"requires_secrets": requires_secrets},
    )
    return revision.id


def test_secret_values_are_upserted_and_bindings_are_deduped() -> None:
    repository, agents_repository = build_repositories()
    revision_id = create_revision(
        agents_repository,
        org_id="org_limitless",
        requires_secrets=["resend_api_key"],
    )

    secret = repository.create_secret(
        org_id="org_limitless",
        name="resend_api_key",
        secret_value="secret-value-1",
        description="Outbound email key",
    )
    duplicate_secret = repository.create_secret(
        org_id="org_limitless",
        name="resend_api_key",
        secret_value="secret-value-2",
        description="Updated description",
    )
    binding = repository.bind_secret(
        secret_id=secret.id,
        agent_revision_id=revision_id,
        binding_name="resend_api_key",
    )
    duplicate_binding = repository.bind_secret(
        secret_id=secret.id,
        agent_revision_id=revision_id,
        binding_name="resend_api_key",
    )

    assert secret.id == duplicate_secret.id
    assert duplicate_secret.secret_value == "secret-value-2"
    assert binding.id == duplicate_binding.id

    secrets = repository.list_secrets(org_id="org_limitless")
    bindings = repository.list_bindings(agent_revision_id=revision_id)

    assert len(secrets) == 1
    assert secrets[0].name == "resend_api_key"
    assert secrets[0].secret_value == "secret-value-2"
    assert len(bindings) == 1
    assert bindings[0].binding_name == "resend_api_key"


def test_bind_secret_rejects_missing_revision() -> None:
    repository, _ = build_repositories()
    secret = repository.create_secret(
        org_id="org_limitless",
        name="resend_api_key",
        secret_value="secret-value-1",
    )

    with pytest.raises(ValueError, match="Agent revision not found"):
        repository.bind_secret(
            secret_id=secret.id,
            agent_revision_id="rev_missing",
            binding_name="resend_api_key",
        )



def test_bind_secret_rejects_foreign_org_revision() -> None:
    repository, agents_repository = build_repositories()
    revision_id = create_revision(
        agents_repository,
        org_id="org_other",
        requires_secrets=["resend_api_key"],
    )
    secret = repository.create_secret(
        org_id="org_limitless",
        name="resend_api_key",
        secret_value="secret-value-1",
    )

    with pytest.raises(ValueError, match="Agent revision not found"):
        repository.bind_secret(
            secret_id=secret.id,
            agent_revision_id=revision_id,
            binding_name="resend_api_key",
        )



def test_bind_secret_rejects_undeclared_binding_name() -> None:
    repository, agents_repository = build_repositories()
    revision_id = create_revision(
        agents_repository,
        org_id="org_limitless",
        requires_secrets=["postmark_api_key"],
    )
    secret = repository.create_secret(
        org_id="org_limitless",
        name="resend_api_key",
        secret_value="secret-value-1",
    )

    with pytest.raises(ValueError, match="not declared"):
        repository.bind_secret(
            secret_id=secret.id,
            agent_revision_id=revision_id,
            binding_name="resend_api_key",
        )
