from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from typing import Callable, TypeVar

from app.core.config import get_settings
from app.db.client import ControlPlaneClient, InMemoryControlPlaneStore, STORE, get_control_plane_client

RepositoryT = TypeVar("RepositoryT")


def resolve_repository_for_active_backend(
    repository: RepositoryT,
    *,
    factory: Callable[[ControlPlaneClient], RepositoryT],
) -> RepositoryT:
    settings = get_settings()
    expected_backend = settings.control_plane_backend
    client = getattr(repository, "client", None)
    client_store = getattr(client, "store", getattr(client, "_store", STORE))
    if client is not None and getattr(client, "backend", None) == "memory" and client_store is not STORE:
        return repository
    if client is not None and getattr(client, "backend", None) == expected_backend:
        return repository
    return factory(get_control_plane_client(settings))


class StoreBoundControlPlaneClient:
    def __init__(self, store: InMemoryControlPlaneStore, *, backend: str = "memory") -> None:
        self._store = store
        self.backend = backend

    @contextmanager
    def transaction(self):
        yield self._store


def restore_store_from_snapshot(store: InMemoryControlPlaneStore, snapshot: InMemoryControlPlaneStore) -> None:
    store.__dict__.clear()
    store.__dict__.update(deepcopy(snapshot.__dict__))
