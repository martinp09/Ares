from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.secrets import SecretsRepository


def build_repository() -> SecretsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return SecretsRepository(client)


def test_secret_values_are_upserted_and_bindings_are_deduped() -> None:
    repository = build_repository()

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
        agent_revision_id="rev_123",
        binding_name="resend_api_key",
    )
    duplicate_binding = repository.bind_secret(
        secret_id=secret.id,
        agent_revision_id="rev_123",
        binding_name="resend_api_key",
    )

    assert secret.id == duplicate_secret.id
    assert duplicate_secret.secret_value == "secret-value-2"
    assert binding.id == duplicate_binding.id

    secrets = repository.list_secrets(org_id="org_limitless")
    bindings = repository.list_bindings(agent_revision_id="rev_123")

    assert len(secrets) == 1
    assert secrets[0].name == "resend_api_key"
    assert secrets[0].secret_value == "secret-value-2"
    assert len(bindings) == 1
    assert bindings[0].binding_name == "resend_api_key"
