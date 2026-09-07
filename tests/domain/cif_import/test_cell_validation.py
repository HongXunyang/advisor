"""Pure unit-cell validity checks -- no Qt, no Dans_Diffraction."""

import math

from advisor.domain.cif_import.cell_validation import validate_cell


class TestValidCells:
    def test_cubic_cell_is_valid(self):
        ok, reasons = validate_cell(5.0, 5.0, 5.0, 90.0, 90.0, 90.0)
        assert ok is True
        assert reasons == []

    def test_triclinic_cell_is_valid(self):
        ok, reasons = validate_cell(5.1, 6.2, 7.3, 80.0, 95.0, 110.0)
        assert ok is True
        assert reasons == []


class TestInvalidLengths:
    def test_nonpositive_length_rejected(self):
        ok, reasons = validate_cell(0.0, 5.0, 5.0, 90.0, 90.0, 90.0)
        assert ok is False
        assert any("length a" in r for r in reasons)

    def test_negative_length_rejected(self):
        ok, reasons = validate_cell(-1.0, 5.0, 5.0, 90.0, 90.0, 90.0)
        assert ok is False

    def test_nonfinite_length_rejected(self):
        ok, reasons = validate_cell(math.nan, 5.0, 5.0, 90.0, 90.0, 90.0)
        assert ok is False
        ok, reasons = validate_cell(math.inf, 5.0, 5.0, 90.0, 90.0, 90.0)
        assert ok is False


class TestInvalidAngles:
    def test_zero_angle_rejected(self):
        ok, reasons = validate_cell(5.0, 5.0, 5.0, 0.0, 90.0, 90.0)
        assert ok is False
        assert any("angle alpha" in r for r in reasons)

    def test_angle_at_or_above_180_rejected(self):
        ok, _ = validate_cell(5.0, 5.0, 5.0, 180.0, 90.0, 90.0)
        assert ok is False
        ok, _ = validate_cell(5.0, 5.0, 5.0, 190.0, 90.0, 90.0)
        assert ok is False

    def test_nonfinite_angle_rejected(self):
        ok, _ = validate_cell(5.0, 5.0, 5.0, math.nan, 90.0, 90.0)
        assert ok is False


class TestDegenerateVolume:
    def test_incompatible_angles_rejected(self):
        # alpha=beta=10, gamma=170 cannot describe a real 3D cell.
        ok, reasons = validate_cell(5.0, 5.0, 5.0, 10.0, 10.0, 170.0)
        assert ok is False
        assert any("volume" in r or "degenerate" in r for r in reasons)

    def test_multiple_reasons_can_be_reported_together(self):
        ok, reasons = validate_cell(-1.0, -2.0, 5.0, 0.0, 200.0, 90.0)
        assert ok is False
        assert len(reasons) >= 2
