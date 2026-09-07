"""CifImportService: the stateless prepare_from_path orchestration."""

import os

from advisor.controllers.cif_import_service import CifImportService
from advisor.domain.cif_import import io as cif_io

FIXTURES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif")
)
NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "advisor", "resources", "data", "nacl.cif")
)


class TestPrepareFromPath:
    def test_valid_cif_is_ready(self):
        service = CifImportService()
        result = service.prepare_from_path(NACL_CIF)
        try:
            assert result.status == "ready"
            assert result.source.effective_path != NACL_CIF
            assert os.path.exists(result.source.effective_path)
        finally:
            if result.source:
                cif_io.cleanup_snapshot(result.source.effective_path)

    def test_missing_file_is_rejected_without_raising(self, tmp_path):
        service = CifImportService()
        result = service.prepare_from_path(str(tmp_path / "nope.cif"))
        assert result.status == "rejected"
        assert result.source is None

    def test_effective_path_snapshot_survives_original_removal(self, tmp_path):
        original = tmp_path / "will_vanish.cif"
        original.write_bytes(
            (
                "data_x\n_cell_length_a 5.0\n_cell_length_b 5.0\n"
                "_cell_length_c 5.0\n_cell_angle_alpha 90.0\n"
                "_cell_angle_beta 90.0\n_cell_angle_gamma 90.0\n"
            ).encode()
        )
        service = CifImportService()
        result = service.prepare_from_path(str(original))
        try:
            assert result.status == "ready_geometry_only"
            original.unlink()
            with open(result.source.effective_path, "rb") as fh:
                assert b"_cell_length_a 5.0" in fh.read()
        finally:
            if result.source:
                cif_io.cleanup_snapshot(result.source.effective_path)
