"""Managed-file I/O boundary for the local structure library.

Durable CIF bytes are content-addressed and sharded by the first two hex
digits of their SHA-256 digest (`cif_files/<hash[:2]>/<hash>.cif`), one file
per distinct content. Writes are atomic (temp file in the same directory,
`fsync`, then `os.replace`) so a record's row is only ever created *after*
its file exists on disk -- never the reverse.
"""

import os
import tempfile

from .types import LibraryError


def managed_relative_path_for(content_hash: str) -> str:
    return os.path.join("cif_files", content_hash[:2], f"{content_hash}.cif")


def managed_absolute_path(root_dir: str, managed_relative_path: str) -> str:
    return os.path.join(root_dir, managed_relative_path)


def write_managed_file_atomic(root_dir: str, content_hash: str, raw_bytes: bytes) -> str:
    """Write `raw_bytes` under its content-addressed managed path, atomically.

    Returns the relative path (to store in the DB row). If a file already
    exists at that path (identical content, already saved), this is a no-op
    -- content-addressing makes the write itself idempotent.
    """
    relative_path = managed_relative_path_for(content_hash)
    absolute_path = managed_absolute_path(root_dir, relative_path)
    shard_dir = os.path.dirname(absolute_path)
    os.makedirs(shard_dir, exist_ok=True)

    if os.path.exists(absolute_path):
        return relative_path

    fd, tmp_path = tempfile.mkstemp(dir=shard_dir, prefix=".tmp-", suffix=".cif")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, absolute_path)
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
    return relative_path


def read_and_verify(root_dir: str, managed_relative_path: str, expected_content_hash: str) -> bytes:
    """Read a managed CIF file and confirm it still matches its recorded
    hash. Raises `LibraryError` (never a bare OSError) on anything wrong --
    missing file or a hash mismatch (corruption/external tampering) -- so
    callers get an actionable message instead of a confusing downstream
    parse failure.
    """
    import hashlib

    absolute_path = managed_absolute_path(root_dir, managed_relative_path)
    if not os.path.exists(absolute_path):
        raise LibraryError(
            "This saved structure's file is missing from local storage. "
            "It may have been moved or deleted outside ADVISOR."
        )
    try:
        with open(absolute_path, "rb") as handle:
            raw_bytes = handle.read()
    except OSError as exc:
        raise LibraryError(f"Could not read the saved structure file: {exc}") from exc

    if hashlib.sha256(raw_bytes).hexdigest() != expected_content_hash:
        raise LibraryError(
            "This saved structure's file has changed unexpectedly and no "
            "longer matches what was originally saved."
        )
    return raw_bytes
