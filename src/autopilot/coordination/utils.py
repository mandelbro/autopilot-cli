"""Shared utilities for coordination modules."""

from __future__ import annotations

import contextlib
import fcntl
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@contextlib.contextmanager
def file_lock(path: Path) -> Iterator[None]:
    """Acquire an exclusive file lock using a .lock sentinel file.

    Keeps the lock held for the duration of the context, ensuring
    atomic read-modify-write cycles.
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.touch()
    with open(lock_path) as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def write_atomic(path: Path, content: str) -> None:
    """Write content to a file atomically via a temp file rename.

    Must be called while holding file_lock(path) to prevent races.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)
