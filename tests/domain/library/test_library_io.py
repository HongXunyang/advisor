import os

import pytest

from advisor.domain.library import io as library_io
from advisor.domain.library.types import LibraryError


def test_write_managed_file_atomic_creates_sharded_content_addressed_path(tmp_path):
    content_hash = "deadbeef" * 8
    relative_path = library_io.write_managed_file_atomic(str(tmp_path), content_hash, b"cif bytes")
    assert relative_path == os.path.join("cif_files", content_hash[:2], f"{content_hash}.cif")
    absolute_path = library_io.managed_absolute_path(str(tmp_path), relative_path)
    assert os.path.exists(absolute_path)
    with open(absolute_path, "rb") as handle:
        assert handle.read() == b"cif bytes"


def test_write_managed_file_atomic_is_idempotent_for_identical_content(tmp_path):
    content_hash = "abc123" * 10 + "abcd"
    relative_path_1 = library_io.write_managed_file_atomic(str(tmp_path), content_hash, b"same bytes")
    relative_path_2 = library_io.write_managed_file_atomic(str(tmp_path), content_hash, b"same bytes")
    assert relative_path_1 == relative_path_2
    # no leftover temp files
    shard_dir = os.path.dirname(library_io.managed_absolute_path(str(tmp_path), relative_path_1))
    assert os.listdir(shard_dir) == [f"{content_hash}.cif"]


def test_read_and_verify_detects_missing_file(tmp_path):
    with pytest.raises(LibraryError):
        library_io.read_and_verify(str(tmp_path), "cif_files/xx/xx.cif", "xx")


def test_read_and_verify_detects_hash_mismatch(tmp_path):
    import hashlib

    original = b"original"
    content_hash = hashlib.sha256(original).hexdigest()
    relative_path = library_io.write_managed_file_atomic(str(tmp_path), content_hash, original)
    absolute_path = library_io.managed_absolute_path(str(tmp_path), relative_path)
    with open(absolute_path, "wb") as handle:
        handle.write(b"tampered content")

    with pytest.raises(LibraryError):
        library_io.read_and_verify(str(tmp_path), relative_path, content_hash)


def test_read_and_verify_returns_bytes_on_match(tmp_path):
    import hashlib

    payload = b"payload"
    content_hash = hashlib.sha256(payload).hexdigest()
    relative_path = library_io.write_managed_file_atomic(str(tmp_path), content_hash, payload)
    raw = library_io.read_and_verify(str(tmp_path), relative_path, content_hash)
    assert raw == payload


def test_interrupted_write_leaves_no_managed_file(tmp_path, monkeypatch):
    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", _boom)
    content_hash = "bb" * 32
    with pytest.raises(OSError):
        library_io.write_managed_file_atomic(str(tmp_path), content_hash, b"data")

    absolute_path = library_io.managed_absolute_path(
        str(tmp_path), library_io.managed_relative_path_for(content_hash)
    )
    assert not os.path.exists(absolute_path)
    shard_dir = os.path.dirname(absolute_path)
    # no dangling temp file left behind either
    assert os.listdir(shard_dir) == []
