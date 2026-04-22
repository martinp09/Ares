import pytest

from app.host_adapters.registry import DEFAULT_HOST_ADAPTER_KIND, HostAdapterRegistry
from app.host_adapters.trigger_dev import TriggerDevHostAdapter
from app.models.host_adapters import HostAdapterKind


def test_registry_exposes_trigger_dev_as_default_enabled_adapter() -> None:
    registry = HostAdapterRegistry()

    default_adapter = registry.get_adapter()
    descriptions = {record.kind: record for record in registry.list_adapters()}

    assert DEFAULT_HOST_ADAPTER_KIND == HostAdapterKind.TRIGGER_DEV
    assert default_adapter.kind == HostAdapterKind.TRIGGER_DEV
    assert default_adapter.enabled is True
    assert descriptions[HostAdapterKind.TRIGGER_DEV].display_name == "Trigger.dev"
    assert descriptions[HostAdapterKind.TRIGGER_DEV].adapter_details_label == "Adapter details"
    assert descriptions[HostAdapterKind.TRIGGER_DEV].capabilities.dispatch is True
    assert descriptions[HostAdapterKind.TRIGGER_DEV].capabilities.status_correlation is True
    assert descriptions[HostAdapterKind.TRIGGER_DEV].capabilities.artifact_reporting is True
    assert descriptions[HostAdapterKind.TRIGGER_DEV].capabilities.cancellation is False
    assert descriptions[HostAdapterKind.CODEX].enabled is False
    assert descriptions[HostAdapterKind.CODEX].disabled_reason == "codex adapter is disabled in this environment"
    assert descriptions[HostAdapterKind.CODEX].capabilities.dispatch is False
    assert descriptions[HostAdapterKind.ANTHROPIC].enabled is False
    assert descriptions[HostAdapterKind.ANTHROPIC].disabled_reason == "anthropic adapter is disabled in this environment"


def test_registry_can_describe_registered_adapter_by_kind() -> None:
    registry = HostAdapterRegistry()

    description = registry.describe_adapter(HostAdapterKind.TRIGGER_DEV)

    assert description.kind == HostAdapterKind.TRIGGER_DEV
    assert description.display_name == "Trigger.dev"
    assert description.disabled_reason is None


def test_registry_rejects_duplicate_adapter_kinds() -> None:
    with pytest.raises(ValueError, match="Host adapter 'trigger_dev' is already registered"):
        HostAdapterRegistry([TriggerDevHostAdapter(), TriggerDevHostAdapter()])
