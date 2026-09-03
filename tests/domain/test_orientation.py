"""Tests for advisor.domain.orientation and advisor.domain.orientation_calculator.

Covers:
- OrientationCalculator forward calculation (unchanged behavior).
- Round-trip recovery of U/(roll,pitch,yaw) via the Kabsch solver, for
  exactly-two-measurement and overdetermined/noisy cases.
- Rejection of unidentifiable input (too few measurements, parallel
  reflections, duplicates, (0,0,0), invalid energy, non-finite values).
- The completed/identifiable/valid three-way status split.
- UB matrix consistency.
"""

import numpy as np
import pytest

from advisor.domain.geometry import euler_to_matrix, get_reciprocal_space_vectors
from advisor.domain.orientation import fit_orientation_from_diffraction_tests
from advisor.domain.orientation_calculator import OrientationCalculator
from tests.conftest import LATTICE_CONFIGS, consistent_diffraction_row


class TestOrientationCalculator:
    """Tests for the OrientationCalculator class (unaffected by the Kabsch change)."""

    def test_not_initialized_by_default(self):
        calc = OrientationCalculator()
        assert not calc.is_initialized()

    def test_initialized_after_init(self):
        calc = OrientationCalculator()
        params = {**LATTICE_CONFIGS["orthorhombic"], "energy": 3000.0}
        assert calc.initialize(params) is True
        assert calc.is_initialized()

    def test_calculate_hkl_returns_dict(self):
        calc = OrientationCalculator()
        params = {**LATTICE_CONFIGS["orthorhombic"], "energy": 3000.0}
        calc.initialize(params)
        result = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)
        assert "H" in result and "K" in result and "L" in result
        assert result["success"] is True

    def test_change_energy(self):
        calc = OrientationCalculator()
        params = {**LATTICE_CONFIGS["orthorhombic"], "energy": 3000.0}
        calc.initialize(params)
        calc.change_energy(5000.0)
        assert calc.energy == 5000.0
        result1 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)
        calc.change_energy(3000.0)
        result2 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)
        assert result1["H"] != result2["H"] or result1["K"] != result2["K"] or result1["L"] != result2["L"]

    def test_reorient_sample(self):
        calc = OrientationCalculator()
        params = {**LATTICE_CONFIGS["orthorhombic"], "energy": 3000.0, "roll": 0.0, "pitch": 0.0, "yaw": 0.0}
        calc.initialize(params)
        result1 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)
        calc.reorient_sample(roll=10.0, pitch=5.0, yaw=15.0)
        result2 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)
        assert not np.allclose(
            [result1["H"], result1["K"], result1["L"]],
            [result2["H"], result2["K"], result2["L"]],
        )


def check_orientation(result, true_roll, true_pitch, true_yaw, atol=1e-3):
    """Compare orientation matrices, not raw Euler angles, since the same
    rotation can be represented by different Euler-angle triples."""
    orientation_matrix = euler_to_matrix(result.roll, result.pitch, result.yaw)
    true_orientation_matrix = euler_to_matrix(true_roll, true_pitch, true_yaw)
    assert np.allclose(orientation_matrix, true_orientation_matrix, atol=atol)


def generate_diffraction_tests(lattice_params, energy, roll, pitch, yaw, angle_sets):
    calc = OrientationCalculator()
    calc.initialize({**lattice_params, "energy": energy, "roll": roll, "pitch": pitch, "yaw": yaw})
    tests = []
    for tth, theta, phi, chi in angle_sets:
        result = calc.calculate_hkl(tth, theta, phi, chi)
        assert result["success"]
        tests.append({
            "H": result["H"], "K": result["K"], "L": result["L"],
            "energy": energy, "tth": tth, "theta": theta, "phi": phi, "chi": chi,
        })
    return tests


class TestOrientationFittingRoundTrip:
    """Round-trip recovery of orientation from synthetic exact diffraction data."""

    @pytest.fixture
    def orthorhombic_params(self):
        return LATTICE_CONFIGS["orthorhombic"].copy()

    @pytest.fixture
    def high_energy(self):
        return 3000.0

    def test_round_trip_no_orientation(self, orthorhombic_params, high_energy):
        true_roll, true_pitch, true_yaw = 0.0, 0.0, 0.0
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 10.0, 82, 16), (120.0, 20.0, -5.0, 10.0)]
        tests = generate_diffraction_tests(orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.completed and result.identifiable and result.valid
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result.residual_rms < 1e-6

    def test_round_trip_small_rotation(self, orthorhombic_params, high_energy):
        true_roll, true_pitch, true_yaw = 5.0, 3.0, 7.0
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82, 16)]
        tests = generate_diffraction_tests(orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result.residual_rms < 1e-6

    @pytest.mark.parametrize("true_roll, true_pitch, true_yaw", [
        (0.0, 0.0, 0.0), (90, 0, 0), (0, 90, 0), (0, 0, 90), (0, 90, 90),
        (90, 0, 90), (90, 90, 0), (1, 2, 3), (4, 5, 6), (7, 8, 9),
    ])
    def test_round_trip_with_orientation(self, orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw):
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82, 16)]
        tests = generate_diffraction_tests(orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result.residual_rms < 1e-6

    def test_round_trip_exactly_two_measurements(self, orthorhombic_params, high_energy):
        """Two non-parallel reflections are the minimum that determine an orientation."""
        true_roll, true_pitch, true_yaw = 12.0, -8.0, 20.0
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82.0, 16.0)]
        tests = generate_diffraction_tests(orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        assert result.n_measurements_used == 2
        check_orientation(result, true_roll, true_pitch, true_yaw)

    def test_round_trip_with_varying_energy(self, orthorhombic_params):
        true_roll, true_pitch, true_yaw = 8.0, -5.0, 12.0
        calc = OrientationCalculator()
        tests = []
        for energy, tth, theta, phi, chi in [(3000.0, 90.0, 45.0, 0.0, 0.0), (3500.0, 60.0, 30.0, 10.0, 5.0)]:
            calc.initialize({**orthorhombic_params, "energy": energy, "roll": true_roll, "pitch": true_pitch, "yaw": true_yaw})
            r = calc.calculate_hkl(tth, theta, phi, chi)
            tests.append({"H": r["H"], "K": r["K"], "L": r["L"], "energy": energy,
                          "tth": tth, "theta": theta, "phi": phi, "chi": chi})

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result.residual_rms < 1e-6

    def test_round_trip_three_tests(self, orthorhombic_params, high_energy):
        true_roll, true_pitch, true_yaw = 5.0, 3.0, 7.0
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82, 16), (120.0, 60.0, -5.0, 10.0)]
        tests = generate_diffraction_tests(orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        assert result.residual_rms < 1e-6

    def test_round_trip_large_orientation(self, orthorhombic_params, high_energy):
        true_roll, true_pitch, true_yaw = 45.0, -30.0, 60.0
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82, 16)]
        tests = generate_diffraction_tests(orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result.residual_rms < 1e-6

    def test_round_trip_realistic_angle_rounding(self):
        """Motor angles rounded to 0.01 degrees (typical instrument/display
        precision) for exact integer HKL reflections must still be accepted
        under the *default* OrientationFitConfig -- calibrates
        residual_rms_threshold against realistic, not synthetic-exact, input.
        Regression test for the default threshold being too strict for any
        real, rounded experimental data (see OrientationFitConfig docstring).
        """
        from advisor.features.scattering_geometry.domain import BrillouinCalculator

        lattice_params = {"a": 4.0, "b": 4.0, "c": 4.0, "alpha": 90.0, "beta": 90.0, "gamma": 90.0}
        energy = 8000.0
        true_roll, true_pitch, true_yaw = 12.3, -7.1, 33.5

        calc = BrillouinCalculator()
        calc.initialize({**lattice_params, "energy": energy, "roll": true_roll, "pitch": true_pitch, "yaw": true_yaw})

        tests = []
        for H, K, L in [(1, 1, 1), (2, 0, 0), (1, -1, 2)]:
            angles = calc.calculate_angles(H, K, L, fixed_angle=0.0, fixed_angle_name="chi")
            idx = next((i for i, feasible in enumerate(angles["feasible"]) if feasible), 0)
            tests.append({
                "H": H, "K": K, "L": L, "energy": energy,
                "tth": round(angles["tth"][idx], 2), "theta": round(angles["theta"][idx], 2),
                "phi": round(angles["phi"][idx], 2), "chi": round(angles["chi"][idx], 2),
            })

        result = fit_orientation_from_diffraction_tests(lattice_params, tests)
        assert result.identifiable, result.message
        assert result.valid, f"residual_rms={result.residual_rms}: {result.message}"
        check_orientation(result, true_roll, true_pitch, true_yaw, atol=1e-2)

    def test_round_trip_overdetermined_noisy(self, orthorhombic_params, high_energy):
        """Six measurements with small H/K/L noise: fit should still land
        close to the true orientation, with a residual reflecting the noise
        level rather than being exactly zero."""
        true_roll, true_pitch, true_yaw = 9.0, -4.0, 17.0
        angle_sets = [
            (90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82, 16), (120.0, 60.0, -5.0, 10.0),
            (75.0, 20.0, 40.0, -20.0), (100.0, 70.0, -10.0, 30.0), (55.0, 15.0, 5.0, 5.0),
        ]
        tests = generate_diffraction_tests(orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw, angle_sets)

        rng = np.random.default_rng(7)
        noisy_tests = []
        for t in tests:
            noisy = dict(t)
            for key in ("H", "K", "L"):
                noisy[key] = noisy[key] + rng.normal(scale=1e-3)
            noisy_tests.append(noisy)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, noisy_tests)
        assert result.valid is True
        assert result.quality == "good"  # 1e-3-scale noise is comfortably under the 0.02 warning threshold
        check_orientation(result, true_roll, true_pitch, true_yaw, atol=1e-2)
        assert 0 < result.residual_rms < 1e-2


class TestUBMatrixConsistency:
    @pytest.fixture
    def orthorhombic_params(self):
        return LATTICE_CONFIGS["orthorhombic"].copy()

    def test_ub_matrix_matches_u_and_b(self, orthorhombic_params):
        true_roll, true_pitch, true_yaw = 6.0, -11.0, 24.0
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82.0, 16.0)]
        tests = generate_diffraction_tests(orthorhombic_params, 3000.0, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True

        lattice_keys = ("a", "b", "c", "alpha", "beta", "gamma")
        a_star, b_star, c_star = get_reciprocal_space_vectors(
            *(orthorhombic_params[k] for k in lattice_keys)
        )
        b_matrix = np.column_stack([a_star, b_star, c_star])
        assert np.allclose(result.UB, result.U @ b_matrix, atol=1e-9)

        true_u = euler_to_matrix(true_roll, true_pitch, true_yaw)
        assert np.allclose(result.U, true_u, atol=1e-6)

        # U must be a proper rotation (orthogonal, det=+1)
        assert np.allclose(result.U @ result.U.T, np.eye(3), atol=1e-9)
        assert np.isclose(np.linalg.det(result.U), 1.0, atol=1e-9)

    def test_predicted_g_matches_target_g(self, orthorhombic_params):
        """Direct check of the Kabsch-input derivation: at the fitted U,
        U @ g_i should match q_i (equivalently, the forward-predicted HKL
        should match the measured HKL) for exact synthetic data."""
        from advisor.domain.orientation_validation import compute_measurement_vectors
        from advisor.domain.orientation_types import DiffractionMeasurement

        true_roll, true_pitch, true_yaw = 3.0, 14.0, -22.0
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (70.0, 25.0, 12.0, -8.0), (110.0, 55.0, -30.0, 20.0)]
        tests = generate_diffraction_tests(orthorhombic_params, 3000.0, true_roll, true_pitch, true_yaw, angle_sets)

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True

        for raw in tests:
            m = DiffractionMeasurement.from_dict(raw)
            g, q = compute_measurement_vectors(orthorhombic_params, m)
            assert np.allclose(result.U @ g, q, atol=1e-6)


class TestFitQuality:
    """A completed, identifiable fit is never hard-rejected on residual --
    it's always the least-squares-best rotation available. residual_rms is
    only graded into quality="good"/"warning"/"poor" against
    OrientationFitConfig's two thresholds (0.02 / 0.1 r.l.u. by default),
    purely advisory; `valid` stays True at every tier."""

    def _tests_with_perturbation(self, perturb):
        lattice = {"a": 3.0, "b": 4.0, "c": 5.0, "alpha": 90.0, "beta": 90.0, "gamma": 90.0}
        energy = 3000.0
        calc = OrientationCalculator()
        calc.initialize({**lattice, "energy": energy, "roll": 5.0, "pitch": 3.0, "yaw": 7.0})
        angle_sets = [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82, 16), (120.0, 60.0, -5.0, 10.0)]
        tests = []
        for i, (tth, theta, phi, chi) in enumerate(angle_sets):
            r = calc.calculate_hkl(tth, theta, phi, chi)
            tests.append({
                "H": r["H"], "K": r["K"] + perturb * (1 if i % 2 == 0 else -1), "L": r["L"],
                "energy": energy, "tth": tth, "theta": theta, "phi": phi, "chi": chi,
            })
        return lattice, tests

    def test_near_exact_data_is_good_quality(self):
        lattice, tests = self._tests_with_perturbation(0.0)
        result = fit_orientation_from_diffraction_tests(lattice, tests)
        assert result.valid is True
        assert result.quality == "good"

    def test_moderate_residual_is_warning_quality_but_still_valid(self):
        lattice, tests = self._tests_with_perturbation(0.1)
        result = fit_orientation_from_diffraction_tests(lattice, tests)
        assert result.valid is True
        assert result.quality == "warning"
        assert result.roll is not None  # Apply-able, per the caveat text only

    def test_large_residual_is_poor_quality_but_still_valid(self):
        lattice, tests = self._tests_with_perturbation(0.15)
        result = fit_orientation_from_diffraction_tests(lattice, tests)
        assert result.valid is True
        assert result.quality == "poor"
        assert result.roll is not None  # Apply-able, per the caveat text only


class TestConditionNumber:
    @pytest.fixture
    def orthorhombic_params(self):
        return LATTICE_CONFIGS["orthorhombic"].copy()

    def test_none_for_two_measurements(self, orthorhombic_params):
        """The 3x3 cross-covariance is structurally rank <= 2 with only two
        measurements, so condition_number is not an informative diagnostic
        there -- it must be None, not a numerically-meaningless inf."""
        tests = generate_diffraction_tests(
            orthorhombic_params, 3000.0, 4.0, -3.0, 9.0,
            [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82.0, 16.0)],
        )
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        assert result.condition_number is None

    def test_finite_for_three_or_more_measurements(self, orthorhombic_params):
        tests = generate_diffraction_tests(
            orthorhombic_params, 3000.0, 4.0, -3.0, 9.0,
            [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 82.0, 16.0), (120.0, 60.0, -5.0, 10.0)],
        )
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.valid is True
        assert result.condition_number is not None
        assert result.condition_number >= 1.0


class TestOrientationFittingRejections:
    """Identifiability rejections: completed=True (the check ran), but
    identifiable=False and valid=False."""

    @pytest.fixture
    def orthorhombic_params(self):
        return LATTICE_CONFIGS["orthorhombic"].copy()

    def _base_test_row(self, H=1.0, K=0.0, L=0.0, energy=20000.0, theta=45.0, phi=0.0, chi=0.0, **overrides):
        """A physically self-consistent row (correct tth for the given
        HKL/energy) unless `tth` is explicitly overridden."""
        row = consistent_diffraction_row(LATTICE_CONFIGS["orthorhombic"], H, K, L, energy, theta, phi, chi)
        row.update(overrides)
        return row

    def test_empty_tests_list(self, orthorhombic_params):
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [])
        assert result.completed and not result.identifiable and not result.valid
        assert "at least" in result.message.lower() or "2" in result.message

    def test_single_reflection_rejected(self, orthorhombic_params, ):
        true_roll, true_pitch, true_yaw = 5.0, 3.0, 7.0
        tests = generate_diffraction_tests(orthorhombic_params, 3000.0, true_roll, true_pitch, true_yaw, [(90.0, 45.0, 0.0, 0.0)])
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert not result.identifiable
        assert not result.valid

    def test_parallel_reflections_rejected(self, orthorhombic_params):
        """Two measurements of the same HKL at the same angles (or HKL that
        are scalar multiples of each other) don't constrain the orientation
        independently."""
        row1 = self._base_test_row(H=1.0, K=0.0, L=0.0, theta=45.0)
        row2 = self._base_test_row(H=2.0, K=0.0, L=0.0, theta=45.0)
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [row1, row2])
        assert not result.identifiable
        assert "parallel" in result.message.lower()

    def test_duplicate_measurements_rejected(self, orthorhombic_params):
        row = self._base_test_row(H=1.0, K=0.0, L=0.0)
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [row, dict(row)])
        assert not result.identifiable
        assert "duplicate" in result.message.lower()

    def test_zero_hkl_rejected(self, orthorhombic_params):
        row1 = self._base_test_row(H=0.0, K=0.0, L=0.0)
        row2 = self._base_test_row(H=0.0, K=1.0, L=0.0, theta=30.0)
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [row1, row2])
        assert not result.identifiable
        assert "(0,0,0)" in result.message

    def test_invalid_energy_rejected(self, orthorhombic_params):
        row1 = self._base_test_row(H=1.0, K=0.0, L=0.0)
        row1["energy"] = -10.0
        row2 = self._base_test_row(H=0.0, K=1.0, L=0.0, theta=30.0)
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [row1, row2])
        assert not result.identifiable
        assert "energy" in result.message.lower()

    def test_non_finite_value_rejected(self, orthorhombic_params):
        row1 = self._base_test_row(H=float("nan"), K=0.0, L=0.0)
        row2 = self._base_test_row(H=0.0, K=1.0, L=0.0, theta=30.0)
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [row1, row2])
        assert not result.identifiable

    def test_out_of_range_tth_rejected(self, orthorhombic_params):
        row1 = self._base_test_row(H=1.0, K=0.0, L=0.0, tth=250.0)
        row2 = self._base_test_row(H=0.0, K=1.0, L=0.0, theta=30.0)
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [row1, row2])
        assert not result.identifiable

    def test_degenerate_lattice_rejected(self, orthorhombic_params):
        bad_lattice = {**orthorhombic_params, "a": 0.0}
        tests = [self._base_test_row(H=1.0, K=0.0, L=0.0), self._base_test_row(H=0.0, K=1.0, L=0.0, theta=30.0)]
        result = fit_orientation_from_diffraction_tests(bad_lattice, tests)
        assert result.completed is False
        assert "lattice" in result.message.lower()

    def test_missing_required_key(self, orthorhombic_params):
        tests = [{"H": 0.1, "K": 0.2, "L": 0.3}]  # missing energy, tth, theta, phi, chi
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result.completed is False
        assert not result.valid

    def test_poor_fit_marked_as_poor_quality(self, orthorhombic_params):
        """Two non-parallel but internally-inconsistent measurements (the
        HKL values don't actually correspond to any single rigid rotation
        of these particular angle geometries) should still fit -- Kabsch
        always returns the least-squares-best rotation -- but with a large
        residual, graded quality="poor" rather than being rejected outright.
        """
        row1 = self._base_test_row(H=1.0, K=0.0, L=0.0, theta=45.0, phi=0.0, chi=0.0)
        row2 = self._base_test_row(H=0.0, K=5.0, L=3.0, theta=10.0, phi=70.0, chi=-40.0)
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [row1, row2])
        assert result.completed and result.identifiable
        assert result.valid is True
        assert result.quality == "poor"
        assert result.residual_rms >= 0.1
        assert result.roll is not None  # still usable, just flagged


class TestOrientationFittingWithDifferentCrystals:
    @pytest.mark.parametrize("crystal_type", ["hexagonal", "monoclinic", "triclinic"])
    def test_round_trip_different_crystals(self, crystal_type):
        lattice_params = LATTICE_CONFIGS[crystal_type].copy()
        energy = 3000.0
        true_roll, true_pitch, true_yaw = 10.0, -5.0, 15.0
        tests = generate_diffraction_tests(
            lattice_params, energy, true_roll, true_pitch, true_yaw,
            [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 10.0, 5.0)],
        )
        result = fit_orientation_from_diffraction_tests(lattice_params, tests)
        assert result.valid is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
