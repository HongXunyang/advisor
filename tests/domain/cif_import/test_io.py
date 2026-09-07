"""CIF I/O boundary: reading bytes and materializing an immutable snapshot."""

import os

import pytest

from advisor.domain.cif_import import io as cif_io

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "cif")
NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "advisor", "resources", "data", "nacl.cif")
)


class TestReadCifBytes:
    def test_reads_existing_cif(self):
        raw = cif_io.read_cif_bytes(NACL_CIF)
        assert raw.startswith(b"#") or b"data_" in raw

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(cif_io.CifReadError, match="not found"):
            cif_io.read_cif_bytes(str(tmp_path / "does_not_exist.cif"))

    def test_folder_raises(self, tmp_path):
        with pytest.raises(cif_io.CifReadError, match="folder"):
            cif_io.read_cif_bytes(str(tmp_path))

    def test_wrong_extension_raises(self, tmp_path):
        bogus = tmp_path / "not_a_cif.txt"
        bogus.write_text("hello")
        with pytest.raises(cif_io.CifReadError, match="not a .cif file"):
            cif_io.read_cif_bytes(str(bogus))

    def test_uppercase_extension_is_accepted(self, tmp_path):
        upper = tmp_path / "STRUCTURE.CIF"
        upper.write_bytes(b"data_x\n")
        raw = cif_io.read_cif_bytes(str(upper))
        assert raw == b"data_x\n"

    def test_unicode_and_space_path_is_accepted(self, tmp_path):
        weird = tmp_path / "na cl étude.cif"
        weird.write_bytes(b"data_x\n")
        raw = cif_io.read_cif_bytes(str(weird))
        assert raw == b"data_x\n"

    def test_empty_path_raises(self):
        with pytest.raises(cif_io.CifReadError, match="No file selected"):
            cif_io.read_cif_bytes("")


class TestContentDigest:
    def test_identical_bytes_same_digest(self):
        assert cif_io.content_digest(b"abc") == cif_io.content_digest(b"abc")

    def test_different_bytes_different_digest(self):
        assert cif_io.content_digest(b"abc") != cif_io.content_digest(b"abd")


class TestMaterializeSnapshot:
    def test_snapshot_contains_exact_bytes(self):
        raw = b"data_snapshot_test\n_cell_length_a 5.0\n"
        path = cif_io.materialize_snapshot(raw, "/somewhere/original.cif")
        try:
            with open(path, "rb") as fh:
                assert fh.read() == raw
        finally:
            cif_io.cleanup_snapshot(path)

    def test_snapshot_is_independent_of_original_path_removal(self, tmp_path):
        original = tmp_path / "will_be_deleted.cif"
        raw = b"data_x\n_cell_length_a 5.0\n"
        original.write_bytes(raw)
        snapshot_path = cif_io.materialize_snapshot(raw, str(original))
        original.unlink()
        try:
            assert os.path.exists(snapshot_path)
            with open(snapshot_path, "rb") as fh:
                assert fh.read() == raw
        finally:
            cif_io.cleanup_snapshot(snapshot_path)

    def test_cleanup_removes_snapshot(self):
        raw = b"data_x\n"
        path = cif_io.materialize_snapshot(raw, "structure.cif")
        cif_io.cleanup_snapshot(path)
        assert not os.path.exists(path)
