"""Standalone tests for advisor.domain.orientation_validation, independent
of the fit itself."""
import numpy as np
import pytest

from advisor.domain.orientation_types import DiffractionMeasurement, OrientationFitConfig
from advisor.domain.orientation_validation import (
    compute_measurement_vectors,
    validate_lattice_params,
    validate_measurements,
)
from tests.conftest import LATTICE_CONFIGS, consistent_diffraction_row

_LATTICE = LATTICE_CONFIGS["orthorhombic"]


def _row(H=1.0, K=0.0, L=0.0, energy=20000.0, theta=45.0, phi=0.0, chi=0.0, **overrides):
    """A physically self-consistent measurement (correct tth auto-computed
    for the given HKL/energy/lattice)."""
    base = consistent_diffraction_row(_LATTICE, H, K, L, energy, theta, phi, chi)
    base.update(overrides)
    return DiffractionMeasurement.from_dict(base)


@pytest.fixture
def lattice_params():
    return LATTICE_CONFIGS["orthorhombic"].copy()


class TestComputeMeasurementVectors:
    def test_norms_are_consistent(self, lattice_params):
        m = _row()
        g, q = compute_measurement_vectors(lattice_params, m)
        assert np.isclose(np.linalg.norm(g), np.linalg.norm(q), atol=1e-9)


class TestValidateMeasurements:
    def test_accepts_two_nonparallel(self, lattice_params):
        rows = [_row(H=1.0, K=0.0, L=0.0), _row(H=0.0, K=1.0, L=0.0, theta=30.0)]
        identifiable, reason = validate_measurements(lattice_params, rows)
        assert identifiable is True
        assert reason is None

    def test_rejects_too_few(self, lattice_params):
        identifiable, reason = validate_measurements(lattice_params, [_row()])
        assert identifiable is False
        assert "2" in reason or "least" in reason.lower()

    def test_rejects_empty(self, lattice_params):
        identifiable, reason = validate_measurements(lattice_params, [])
        assert identifiable is False

    def test_rejects_zero_hkl(self, lattice_params):
        rows = [_row(H=0.0, K=0.0, L=0.0), _row(H=0.0, K=1.0, L=0.0, theta=30.0)]
        identifiable, reason = validate_measurements(lattice_params, rows)
        assert identifiable is False
        assert "(0,0,0)" in reason

    def test_rejects_non_positive_energy(self, lattice_params):
        row1_dict = _row(H=1.0, K=0.0, L=0.0).to_dict()
        row1_dict["energy"] = 0.0
        row1 = DiffractionMeasurement.from_dict(row1_dict)
        row2 = _row(H=0.0, K=1.0, L=0.0, theta=30.0)
        identifiable, reason = validate_measurements(lattice_params, [row1, row2])
        assert identifiable is False
        assert "energy" in reason.lower()

    def test_rejects_negative_energy(self, lattice_params):
        row1_dict = _row(H=1.0, K=0.0, L=0.0).to_dict()
        row1_dict["energy"] = -5.0
        row1 = DiffractionMeasurement.from_dict(row1_dict)
        row2 = _row(H=0.0, K=1.0, L=0.0, theta=30.0)
        identifiable, reason = validate_measurements(lattice_params, [row1, row2])
        assert identifiable is False

    def test_rejects_non_finite(self, lattice_params):
        row1 = _row()
        row1_dict = row1.to_dict()
        row1_dict["tth"] = float("inf")
        row1 = DiffractionMeasurement.from_dict(row1_dict)
        row2 = _row(H=0.0, K=1.0, L=0.0, theta=30.0)
        identifiable, reason = validate_measurements(lattice_params, [row1, row2])
        assert identifiable is False

    def test_rejects_tth_out_of_range(self, lattice_params):
        row1 = _row()
        row1_dict = row1.to_dict()
        row1_dict["tth"] = 0.0
        row1 = DiffractionMeasurement.from_dict(row1_dict)
        row2 = _row(H=0.0, K=1.0, L=0.0, theta=30.0)
        identifiable, reason = validate_measurements(lattice_params, [row1, row2])
        assert identifiable is False

        row1_dict["tth"] = 181.0
        row1b = DiffractionMeasurement.from_dict(row1_dict)
        identifiable2, _ = validate_measurements(lattice_params, [row1b, row2])
        assert identifiable2 is False

    def test_rejects_magnitude_mismatch(self, lattice_params):
        """A row whose tth doesn't correspond to its HKL at the given
        energy/lattice for any orientation (rotation preserves vector norm,
        so |g| must equal |q|). The message should be actionable: state
        Bragg's law is violated, give the expected tth, and suggest likely
        data-entry causes."""
        row1_dict = _row(H=1.0, K=0.0, L=0.0).to_dict()
        row1_dict["tth"] = 90.0  # deliberately not the magnitude-consistent value
        row1 = DiffractionMeasurement.from_dict(row1_dict)
        row2 = _row(H=0.0, K=1.0, L=0.0, theta=30.0)
        identifiable, reason = validate_measurements(lattice_params, [row1, row2])
        assert identifiable is False
        assert "bragg" in reason.lower()
        assert "tth ≈" in reason

    def test_magnitude_mismatch_reports_min_energy_when_unreachable_at_any_angle(self, lattice_params):
        """When the required |Q| exceeds what's reachable even at tth=180,
        the message should report the minimum energy needed instead of an
        expected tth (which wouldn't exist)."""
        row1_dict = _row(H=1.0, K=0.0, L=0.0).to_dict()
        row1_dict["energy"] = 50.0  # too low for this HKL to be reachable at any tth
        row1 = DiffractionMeasurement.from_dict(row1_dict)
        row2 = _row(H=0.0, K=1.0, L=0.0, theta=30.0)
        identifiable, reason = validate_measurements(lattice_params, [row1, row2])
        assert identifiable is False
        assert "not reachable at" in reason
        assert "at any angle" in reason

    def test_rejects_parallel_hkl(self, lattice_params):
        rows = [_row(H=1.0, K=0.0, L=0.0), _row(H=2.0, K=0.0, L=0.0)]
        identifiable, reason = validate_measurements(lattice_params, rows)
        assert identifiable is False
        assert "parallel" in reason.lower()

    def test_rejects_duplicates(self, lattice_params):
        rows = [_row(), _row()]
        identifiable, reason = validate_measurements(lattice_params, rows)
        assert identifiable is False
        assert "duplicate" in reason.lower()

    def test_accepts_three_measurements(self, lattice_params):
        rows = [
            _row(H=1.0, K=0.0, L=0.0),
            _row(H=0.0, K=1.0, L=0.0, theta=30.0),
            _row(H=0.0, K=0.0, L=1.0, theta=60.0),
        ]
        identifiable, reason = validate_measurements(lattice_params, rows)
        assert identifiable is True

    def test_custom_config_tolerance(self, lattice_params):
        """Near-duplicate rows (HKL differing only at the 1e-8 level)
        should still be caught by the default duplicate tolerance."""
        rows = [_row(H=1.0, K=0.0, L=0.0), _row(H=1.0 + 1e-8, K=0.0, L=0.0)]
        identifiable, _ = validate_measurements(lattice_params, rows, OrientationFitConfig())
        assert identifiable is False

    @pytest.mark.parametrize("field,value", [("theta", 181.0), ("theta", -181.0), ("phi", 200.0), ("chi", -200.0)])
    def test_rejects_motor_angle_out_of_range(self, lattice_params, field, value):
        row1_dict = _row(H=1.0, K=0.0, L=0.0).to_dict()
        row1_dict[field] = value
        row1 = DiffractionMeasurement.from_dict(row1_dict)
        row2 = _row(H=0.0, K=1.0, L=0.0, theta=30.0)
        identifiable, reason = validate_measurements(lattice_params, [row1, row2])
        assert identifiable is False
        assert field in reason


class TestValidateLatticeParams:
    def test_accepts_valid_lattice(self):
        ok, reason = validate_lattice_params(dict(LATTICE_CONFIGS["orthorhombic"]))
        assert ok is True
        assert reason is None

    @pytest.mark.parametrize("field,value", [("a", 0.0), ("b", -1.0), ("c", float("nan"))])
    def test_rejects_bad_length(self, field, value):
        params = dict(LATTICE_CONFIGS["orthorhombic"])
        params[field] = value
        ok, reason = validate_lattice_params(params)
        assert ok is False
        assert field in reason

    @pytest.mark.parametrize("field,value", [("alpha", 0.0), ("beta", 180.0), ("gamma", float("inf"))])
    def test_rejects_bad_angle(self, field, value):
        params = dict(LATTICE_CONFIGS["orthorhombic"])
        params[field] = value
        ok, reason = validate_lattice_params(params)
        assert ok is False
        assert field in reason
