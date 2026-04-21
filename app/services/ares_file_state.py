from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar
from uuid import uuid4
import json
import os

import fcntl
from pydantic import BaseModel, ValidationError


class AresPersistenceError(ValueError):
    """Raised when file-backed Ares runtime state is malformed or invalid."""


T = TypeVar("T", bound=BaseModel)


def load_json_model(storage_path: Path, *, model_type: type[T], label: str) -> T:
    if not storage_path.exists():
        return model_type()
    try:
        payload = json.loads(storage_path.read_text(encoding="utf-8"))
        return model_type.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise AresPersistenceError(f"Corrupted {label} at {storage_path}") from exc


def atomic_write_text(storage_path: Path, content: str) -> None:
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = storage_path.with_name(f".{storage_path.name}.{uuid4().hex}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, storage_path)
    finally:
        temp_path.unlink(missing_ok=True)


@contextmanager
def exclusive_file_lock(storage_path: Path):
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = storage_path.with_name(f".{storage_path.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
