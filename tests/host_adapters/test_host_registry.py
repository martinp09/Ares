from app.host_adapters.registry import DEFAULT_HOST_ADAPTER_KIND, HostAdapterRegistry
from app.models.host_adapters import HostAdapterKind


def test_registry_exposes_trigger_dev_as_default_enabled_adapter() -> None:
    registry = HostAdapterRegistry()

    default_adapter = registry.get_adapter()
    descriptions = {record.kind: record for record in registry.list_adapters()}

    assert DEFAULT_HOST_ADAPTER_KIND == HostAdapterKind.TRIGGER_DEV
    assert default_adapter.kind == HostAdapterKind.TRIGGER_DEV
    assert default_adapter.enabled is True
    assert descriptions[HostAdapterKind.CODEX].enabled is False
    assert descriptions[HostAdapterKind.ANTHROPIC].enabled is False
