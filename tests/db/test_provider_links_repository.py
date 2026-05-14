from __future__ import annotations

import pytest

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore, reset_control_plane_store
from app.db.provider_links import ProviderLinksRepository
from app.models.provider_links import (
    ProviderLinkStatus,
    ProviderObjectLink,
    ProviderSyncCursor,
    ProviderSyncRun,
    ProviderSyncRunStatus,
)


def build_repository() -> ProviderLinksRepository:
    store = InMemoryControlPlaneStore()
    reset_control_plane_store(store)
    return ProviderLinksRepository(InMemoryControlPlaneClient(store))


def link(**updates: object) -> ProviderObjectLink:
    payload = {
        "business_id": "1",
        "environment": "dev",
        "provider": "hubspot",
        "provider_object_type": "contact",
        "provider_object_id": "123",
        "ares_object_type": "crm_record",
        "ares_object_id": "crmrec_abc",
        "sync_hash": "h1",
        "raw_payload": {"email": "seller@example.com"},
    }
    payload.update(updates)
    return ProviderObjectLink.model_validate(payload)


def test_upsert_link_is_idempotent_and_lookupable_both_directions() -> None:
    repo = build_repository()

    created = repo.upsert_link(link())
    updated = repo.upsert_link(link(sync_hash="h2", raw_payload={"email": "new@example.com"}))

    assert created.id == updated.id
    assert updated.sync_hash == "h2"
    assert updated.raw_payload == {"email": "new@example.com"}
    assert repo.get_by_provider_object(
        business_id="1",
        environment="dev",
        provider="hubspot",
        provider_object_type="contact",
        provider_object_id="123",
    ) == updated
    assert repo.get_by_ares_object(
        business_id="1",
        environment="dev",
        provider="hubspot",
        ares_object_type="crm_record",
        ares_object_id="crmrec_abc",
        provider_object_type="contact",
    ) == updated


def test_upsert_link_rejects_provider_object_repoint_conflict() -> None:
    repo = build_repository()
    repo.upsert_link(link())

    with pytest.raises(ValueError, match="provider object link conflict"):
        repo.upsert_link(link(ares_object_id="crmrec_other"))


def test_upsert_link_rejects_ares_object_repoint_conflict() -> None:
    repo = build_repository()
    repo.upsert_link(link())

    with pytest.raises(ValueError, match="provider object link conflict"):
        repo.upsert_link(link(provider_object_id="456"))


def test_mark_conflict_and_archive_are_explicit_states() -> None:
    repo = build_repository()
    created = repo.upsert_link(link())

    conflicted = repo.mark_conflict(created.id or "", reason="email mismatch")
    assert conflicted is not None
    assert conflicted.link_status == ProviderLinkStatus.CONFLICT
    assert conflicted.conflict_reason == "email mismatch"

    archived = repo.archive_link(created.id or "")
    assert archived is not None
    assert archived.link_status == ProviderLinkStatus.ARCHIVED


def test_cursors_upsert_by_tenant_provider_and_sync_name() -> None:
    repo = build_repository()

    created = repo.upsert_cursor(
        ProviderSyncCursor(
            business_id="1",
            environment="dev",
            provider="hubspot",
            sync_name="contacts_delta",
            cursor_value="before",
            cursor_payload={"after": "1"},
        )
    )
    updated = repo.upsert_cursor(
        ProviderSyncCursor(
            business_id="1",
            environment="dev",
            provider="hubspot",
            sync_name="contacts_delta",
            cursor_value="after",
            cursor_payload={"after": "2"},
        )
    )

    assert created.id == updated.id
    assert updated.cursor_value == "after"
    assert repo.get_cursor(business_id="1", environment="dev", provider="hubspot", sync_name="contacts_delta") == updated


def test_sync_runs_are_idempotent_and_can_complete_or_fail() -> None:
    repo = build_repository()
    first = repo.start_sync_run(
        ProviderSyncRun(
            business_id="1",
            environment="dev",
            provider="hubspot",
            sync_name="contacts_push",
            idempotency_key="run-1",
            cursor_before="a",
        )
    )
    second = repo.start_sync_run(
        ProviderSyncRun(
            business_id="1",
            environment="dev",
            provider="hubspot",
            sync_name="contacts_push",
            idempotency_key="run-1",
            cursor_before="ignored",
        )
    )

    assert first.id == second.id
    assert first.status == ProviderSyncRunStatus.IN_PROGRESS

    completed = repo.complete_sync_run(first.id or "", scanned_count=3, created_count=1, cursor_after="b")
    assert completed is not None
    assert completed.status == ProviderSyncRunStatus.COMPLETED
    assert completed.scanned_count == 3
    assert completed.created_count == 1
    assert completed.cursor_after == "b"
    assert completed.completed_at is not None

    failed = repo.start_sync_run(
        ProviderSyncRun(
            business_id="1",
            environment="dev",
            provider="hubspot",
            sync_name="deals_pull",
            idempotency_key="run-2",
        )
    )
    failed = repo.fail_sync_run(failed.id or "", error_message="rate limited", error_count=1)
    assert failed is not None
    assert failed.status == ProviderSyncRunStatus.FAILED
    assert failed.error_message == "rate limited"
    assert failed.error_count == 1

    runs = repo.list_sync_runs(business_id="1", environment="dev", provider="hubspot")
    assert {run.id for run in runs} == {completed.id, failed.id}
    assert repo.list_sync_runs(status=ProviderSyncRunStatus.COMPLETED) == [completed]


def test_memory_link_identity_is_case_insensitive_and_preserves_created_id() -> None:
    repo = build_repository()

    created = repo.upsert_link(
        link(
            provider="HubSpot",
            provider_object_type="Contact",
            ares_object_type="CRM_Record",
            sync_hash="first",
        )
    )
    assert created.provider == "hubspot"
    assert created.provider_object_type == "contact"
    assert created.ares_object_type == "crm_record"
    assert created.provider_object_id == "123"
    assert created.ares_object_id == "crmrec_abc"
    assert repo.get_by_provider_object(
        business_id="1",
        environment="dev",
        provider="hubspot",
        provider_object_type="contact",
        provider_object_id="123",
    ) == created

    updated = repo.upsert_link(
        link(
            provider="hubspot",
            provider_object_type="contact",
            ares_object_type="crm_record",
            sync_hash="second",
        )
    )

    assert updated.id == created.id
    assert updated.sync_hash == "second"
    assert updated.provider == "hubspot"
    assert updated.provider_object_type == "contact"
    assert updated.ares_object_type == "crm_record"
    assert repo.get_by_provider_object(
        business_id="1",
        environment="dev",
        provider="HUBSPOT",
        provider_object_type="CONTACT",
        provider_object_id="123",
    ) == updated
    assert repo.get_by_ares_object(
        business_id="1",
        environment="dev",
        provider="HUBSPOT",
        ares_object_type="CRM_RECORD",
        ares_object_id="crmrec_abc",
        provider_object_type="CONTACT",
    ) == updated


def test_memory_cursor_initial_create_normalizes_provider_and_lowercase_lookup_works() -> None:
    repo = build_repository()

    created = repo.upsert_cursor(
        ProviderSyncCursor(
            business_id="1",
            environment="dev",
            provider="HubSpot",
            sync_name="contacts_delta",
            cursor_value="after-1",
        )
    )

    assert created.provider == "hubspot"
    assert repo.get_cursor(business_id="1", environment="dev", provider="hubspot", sync_name="contacts_delta") == created


def test_memory_sync_run_initial_create_normalizes_provider_and_lowercase_list_filter_works() -> None:
    repo = build_repository()

    created = repo.start_sync_run(
        ProviderSyncRun(
            business_id="1",
            environment="dev",
            provider="HubSpot",
            sync_name="contacts_pull",
            idempotency_key="run-mixed-case-provider",
        )
    )

    assert created.provider == "hubspot"
    assert repo.list_sync_runs(business_id="1", environment="dev", provider="hubspot") == [created]
