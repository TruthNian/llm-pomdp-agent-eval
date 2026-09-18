"""Atomic evidence files and a process-lifetime collection lock; standard library only."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from .agents import strict_json


def read_json(path: Path):
    return strict_json(path.read_text(encoding="utf-8"))


def write_json(path: Path, value, *, replace=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not replace and path.exists():
        raise ValueError(f"Evidence already exists: {path.name}")
    # The collection lock serializes writers. Flush before publishing the new file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def collection_lock(directory: Path):
    """OS releases this advisory lock after a crash; never guess that a PID is stale."""
    if not directory.is_dir():
        raise ValueError("Run directory does not exist")
    lock = directory / "private" / ".collection.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError("Run is locked by another collector; stop it before resuming") from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)
