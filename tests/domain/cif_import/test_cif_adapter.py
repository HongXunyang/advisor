"""CIF parsing/validation matrix: valid full structure, cell-only, malformed,
degenerate cell, multi-block ambiguity, and a high-precision cell.

Uses the shared io.read_cif_bytes/materialize_snapshot helpers, matching how
CifImportService actually drives cif_adapter.parse_cif_candidate.
"""

import os

from advisor.domain.cif_import import io as cif_io
from advisor.domain.cif_import.cif_adapter import parse_cif_candidate

FIXTURES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "cif"))
NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "advisor", "resources", "data", "nacl.cif")
)


def _prepare(path):
    """Mirror CifImportService.prepare_from_path without going through the
    controller layer -- keeps this a pure-domain test."""
    raw = cif_io.read_cif_bytes(path)
    digest = cif_io.content_digest(raw)
    effective_path = cif_io.materialize_snapshot(raw, path)
    result = parse_cif_candidate(raw, digest, path, effective_path)
    return result, effective_path


class TestValidFullStructure:
    def test_nacl_is_ready(self):
        result, effective_path = _prepare(NACL_CIF)
        try:
            assert result.status == "ready"
            assert result.source.capabilities.geometry_ok is True
            assert result.source.capabilities.structure_factor_ok is True
            assert result.message == "Ready for geometry and structure factors."
            assert result.source.formula == "Cl Na"
            assert result.source.a == 2.86
            assert result.source.alpha == 90.0
            assert result.source.data_block == "2104025"
            assert result.source.source_kind == "cif"
        finally:
            cif_io.cleanup_snapshot(effective_path)

    def test_uncertainty_notation_is_stripped_to_value(self):
        # nacl.cif has "_cell_length_a 2.8600(3)"
        result, effective_path = _prepare(NACL_CIF)
        try:
            assert result.source.a == 2.86
        finally:
            cif_io.cleanup_snapshot(effective_path)


class TestValidCellOnly:
    def test_cell_only_cif_is_geometry_only(self):
        path = os.path.join(FIXTURES, "cell_only.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "ready_geometry_only"
            assert result.source.capabilities.geometry_ok is True
            assert result.source.capabilities.structure_factor_ok is False
            assert "prevents structure-factor" in result.message
            assert result.source.a == 5.431
        finally:
            cif_io.cleanup_snapshot(effective_path)


class TestMalformedInput:
    def test_missing_required_cell_keys_is_rejected(self):
        path = os.path.join(FIXTURES, "malformed.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "rejected"
            assert result.source is None
            assert "missing required cell parameters" in result.message
        finally:
            cif_io.cleanup_snapshot(effective_path)

    def test_empty_file_is_rejected(self, tmp_path):
        empty = tmp_path / "empty.cif"
        empty.write_bytes(b"")
        raw = cif_io.read_cif_bytes(str(empty))
        digest = cif_io.content_digest(raw)
        effective_path = cif_io.materialize_snapshot(raw, str(empty))
        try:
            result = parse_cif_candidate(raw, digest, str(empty), effective_path)
            assert result.status == "rejected"
        finally:
            cif_io.cleanup_snapshot(effective_path)


class TestDegenerateCell:
    def test_impossible_angles_rejected_with_previous_state_implied_intact(self):
        path = os.path.join(FIXTURES, "degenerate_cell.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "rejected"
            assert result.source is None
            assert "invalid unit cell" in result.message
        finally:
            cif_io.cleanup_snapshot(effective_path)


class TestMultiBlockAmbiguity:
    def test_multiple_data_blocks_rejected_with_actionable_message(self):
        path = os.path.join(FIXTURES, "multi_block.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "rejected"
            assert result.source is None
            assert "2 structures" in result.message
            assert "data_phase_one" in result.message
            assert "data_phase_two" in result.message
        finally:
            cif_io.cleanup_snapshot(effective_path)


class TestHighPrecisionCell:
    def test_full_precision_is_preserved(self):
        path = os.path.join(FIXTURES, "high_precision.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "ready"
            assert result.source.a == 5.431020511
            assert result.source.capabilities.structure_factor_ok is True
        finally:
            cif_io.cleanup_snapshot(effective_path)


class TestIdentity:
    def test_same_bytes_produce_same_identity_key(self):
        result1, path1 = _prepare(NACL_CIF)
        result2, path2 = _prepare(NACL_CIF)
        try:
            assert result1.source.identity_key() == result2.source.identity_key()
            assert result1.source.content_digest == result2.source.content_digest
        finally:
            cif_io.cleanup_snapshot(path1)
            cif_io.cleanup_snapshot(path2)

    def test_different_bytes_produce_different_identity_key(self):
        result1, path1 = _prepare(NACL_CIF)
        path2_src = os.path.join(FIXTURES, "cell_only.cif")
        result2, path2 = _prepare(path2_src)
        try:
            assert result1.source.identity_key() != result2.source.identity_key()
        finally:
            cif_io.cleanup_snapshot(path1)
            cif_io.cleanup_snapshot(path2)


class TestAtomDataMustBeActuallyUsable:
    """Regression tests for a review finding: fc.cif_check() alone only
    checks required keys are present and that '?' isn't a value -- it does
    not notice CIF's other null marker ('.'), an atom-site loop with zero
    rows, or a genuinely non-numeric coordinate. Dans_Diffraction's own
    readstfm() never raises on such input; it silently returns 0.0, so a
    naive check would advertise structure-factor capability for an
    effectively fabricated atom position.
    """

    def test_missing_coordinate_marker_is_geometry_only_not_ready(self):
        path = os.path.join(FIXTURES, "missing_coordinate.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "ready_geometry_only"
            assert result.source.capabilities.structure_factor_ok is False
            assert "Si2" in result.source.capabilities.reasons[0]
        finally:
            cif_io.cleanup_snapshot(effective_path)

    def test_empty_atom_loop_is_geometry_only_not_ready(self):
        path = os.path.join(FIXTURES, "empty_atom_loop.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "ready_geometry_only"
            assert result.source.capabilities.structure_factor_ok is False
            assert "no rows" in result.source.capabilities.reasons[0]
        finally:
            cif_io.cleanup_snapshot(effective_path)

    def test_valid_atoms_still_ready(self):
        """Confirms the stricter check doesn't create false negatives for
        a real, fully-specified structure."""
        result, effective_path = _prepare(NACL_CIF)
        try:
            assert result.status == "ready"
            assert result.source.capabilities.structure_factor_ok is True
        finally:
            cif_io.cleanup_snapshot(effective_path)


class TestMultiBlockDetectionIsCifAware:
    """Regression tests for a review finding: the original `^data_` regex
    only matched at true column zero (missing an indented second block,
    which then got silently merged by Dans_Diffraction's own block-unaware
    readcif -- exactly the failure this feature exists to prevent) and had
    no concept of semicolon-delimited text fields (falsely flagging a
    single-block file whose prose happens to contain a "data_..."-looking
    line as multi-block).
    """

    def test_indented_second_block_is_still_detected_and_rejected(self):
        path = os.path.join(FIXTURES, "indented_second_block.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "rejected"
            assert result.source is None
            assert "2 structures" in result.message
        finally:
            cif_io.cleanup_snapshot(effective_path)

    def test_data_underscore_inside_text_field_is_not_a_false_positive(self):
        path = os.path.join(FIXTURES, "data_underscore_in_text_field.cif")
        result, effective_path = _prepare(path)
        try:
            assert result.status == "ready"
            assert result.source.data_block == "single_block_test"
        finally:
            cif_io.cleanup_snapshot(effective_path)
