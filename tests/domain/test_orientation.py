"""Tests for advisor.domain.orientation and advisor.domain.orientation_calculator.

These tests verify the round-trip accuracy of the orientation fitting:
1. Set up a crystal with known Euler angles
2. Calculate HKL values for various angle combinations
3. Use those HKL values as input to fit_orientation_from_diffraction_tests
4. Verify the fitted Euler angles match the original ones
"""

import numpy as np
import pytest

from advisor.domain.geometry import euler_to_matrix
from advisor.domain.orientation import fit_orientation_from_diffraction_tests
from advisor.domain.orientation_calculator import OrientationCalculator
from tests.conftest import LATTICE_CONFIGS


class TestOrientationCalculator:
    """Tests for the OrientationCalculator class."""

    def test_not_initialized_by_default(self):
        """Calculator should not be initialized before calling initialize()."""
        calc = OrientationCalculator()
        assert not calc.is_initialized()

    def test_initialized_after_init(self):
        """Calculator should be initialized after calling initialize()."""
        calc = OrientationCalculator()
        params = {
            **LATTICE_CONFIGS["orthorhombic"],
            "energy": 3000.0,
        }
        result = calc.initialize(params)
        assert result is True
        assert calc.is_initialized()

    def test_calculate_hkl_returns_dict(self):
        """calculate_hkl should return a dictionary with expected keys."""
        calc = OrientationCalculator()
        params = {
            **LATTICE_CONFIGS["orthorhombic"],
            "energy": 3000.0,
        }
        calc.initialize(params)

        result = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)

        assert "H" in result
        assert "K" in result
        assert "L" in result
        assert "success" in result
        assert result["success"] is True

    def test_change_energy(self):
        """change_energy should update the calculator's energy."""
        calc = OrientationCalculator()
        params = {
            **LATTICE_CONFIGS["orthorhombic"],
            "energy": 3000.0,
        }
        calc.initialize(params)

        # Change to different energy
        calc.change_energy(5000.0)
        assert calc.energy == 5000.0

        # HKL should change with different energy (different k_in)
        result1 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)

        calc.change_energy(3000.0)
        result2 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)

        # Results should differ
        assert result1["H"] != result2["H"] or result1["K"] != result2["K"] or result1["L"] != result2["L"]

    def test_reorient_sample(self):
        """reorient_sample should change the calculated HKL values."""
        calc = OrientationCalculator()
        params = {
            **LATTICE_CONFIGS["orthorhombic"],
            "energy": 3000.0,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
        }
        calc.initialize(params)

        result1 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)

        # Reorient the sample
        calc.reorient_sample(roll=10.0, pitch=5.0, yaw=15.0)
        result2 = calc.calculate_hkl(tth=90.0, theta=45.0, phi=0.0, chi=0.0)

        # Results should differ
        assert not np.allclose(
            [result1["H"], result1["K"], result1["L"]],
            [result2["H"], result2["K"], result2["L"]],
        )

def check_orientation(result, true_roll, true_pitch, true_yaw):
    """check the matrix element of the orientation matrix, not the Euler angles.
    Due to degeneracy of the Euler angles, the same orientation matrix can be represented by
    different set of Euler angles.
    
    Args:
        result: Result dictionary from fit_orientation_from_diffraction_tests, containing roll, pitch, yaw
        true_roll, true_pitch, true_yaw: True Euler angles in degrees
    """
    roll, pitch, yaw = result["roll"], result["pitch"], result["yaw"]
    orientation_matrix = euler_to_matrix(roll, pitch, yaw)
    true_orientation_matrix = euler_to_matrix(true_roll, true_pitch, true_yaw)
    assert np.allclose(orientation_matrix, true_orientation_matrix, atol=1e-3)

class TestOrientationFittingRoundTrip:
    """Round-trip tests for orientation fitting.

    The test logic:
    1. Set known Euler angles (roll, pitch, yaw)
    2. Generate synthetic diffraction test data using OrientationCalculator
    3. Fit orientation from the synthetic data
    4. Verify fitted angles match the original ones
    """

    @pytest.fixture
    def orthorhombic_params(self):
        """Orthorhombic lattice parameters."""
        return LATTICE_CONFIGS["orthorhombic"].copy()

    @pytest.fixture
    def high_energy(self):
        """High energy beam (~3000 eV) for testing."""
        return 3000.0



    def generate_diffraction_tests(
        self,
        lattice_params: dict,
        energy: float,
        roll: float,
        pitch: float,
        yaw: float,
        angle_sets: list,
    ) -> list:
        """Generate synthetic diffraction test data.

        Args:
            lattice_params: Lattice parameters (a, b, c, alpha, beta, gamma)
            energy: X-ray energy in eV
            roll, pitch, yaw: True Euler angles in degrees
            angle_sets: List of (tth, theta, phi, chi) tuples

        Returns:
            List of diffraction test dictionaries with calculated HKL values
        """
        calc = OrientationCalculator()
        params = {
            **lattice_params,
            "energy": energy,
            "roll": roll,
            "pitch": pitch,
            "yaw": yaw,
        }
        calc.initialize(params)

        tests = []
        for tth, theta, phi, chi in angle_sets:
            result = calc.calculate_hkl(tth, theta, phi, chi)
            if result["success"]:
                tests.append({
                    "H": result["H"],
                    "K": result["K"],
                    "L": result["L"],
                    "energy": energy,
                    "tth": tth,
                    "theta": theta,
                    "phi": phi,
                    "chi": chi,
                })

        return tests


    def test_round_trip_no_orientation(self, orthorhombic_params, high_energy):
        """Test round-trip with zero Euler angles."""
        true_roll, true_pitch, true_yaw = 0.0, 0.0, 0.0
        # Generate test data with various angle combinations
        # angle sets are (tth, theta, phi, chi)
        angle_sets = [
            (90.0, 45.0, 0.0, 0.0),
            (60.0, 10.0, 82, 16),
            (120.0, 20.0, -5.0, 10.0),
        ]

        tests = self.generate_diffraction_tests(
            orthorhombic_params, high_energy,
            true_roll, true_pitch, true_yaw,
            angle_sets,
        )

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)
        assert result["success"] is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result["residual_error"] < 1e-5

    def test_round_trip_small_rotation(self, orthorhombic_params, high_energy):
        """Test round-trip with small Euler angles."""
        true_roll, true_pitch, true_yaw = 5.0, 3.0, 7.0

        angle_sets = [
            (90.0, 45.0, 0.0, 0.0),
            (60.0, 30.0, 82, 16),
        ]

        tests = self.generate_diffraction_tests(
            orthorhombic_params, high_energy,
            true_roll, true_pitch, true_yaw,
            angle_sets,
        )

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        assert result["success"] is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result["residual_error"] < 1e-5


    @pytest.mark.parametrize("true_roll, true_pitch, true_yaw",\
            [(0.0, 0.0, 0.0),\
             (90, 0, 0),\
             (0, 90, 0),\
             (0, 0, 90),\
             (0, 90, 90),\
             (90, 0, 90),\
             (90, 90, 0),\
             (1, 2, 3),\
             (4, 5, 6),\
             (7, 8, 9)])
    def test_round_trip_with_orientation(self, orthorhombic_params, high_energy, true_roll, true_pitch, true_yaw):
        """Test round-trip with moderate Euler angles."""
        angle_sets = [
            (90.0, 45.0, 0.0, 0.0),
            (60.0, 30.0, 82, 16),
        ]

        tests = self.generate_diffraction_tests(
            orthorhombic_params, high_energy,
            true_roll, true_pitch, true_yaw,
            angle_sets,
        )

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        assert result["success"] is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result["residual_error"] < 1e-5

    def test_round_trip_with_varying_energy(self, orthorhombic_params):
        """Test round-trip with different energies per test."""
        true_roll, true_pitch, true_yaw = 8.0, -5.0, 12.0

        # Generate tests at different energies
        calc = OrientationCalculator()

        tests = []
        # angle sets are (energy, tth, theta, phi, chi)
        energy_angle_pairs = [
            (3000.0, 90.0, 45.0, 0.0, 0.0),
            (3500.0, 60.0, 30.0, 10.0, 5.0),
        ]

        for energy, tth, theta, phi, chi in energy_angle_pairs:
            params = {
                **orthorhombic_params,
                "energy": energy,
                "roll": true_roll,
                "pitch": true_pitch,
                "yaw": true_yaw,
            }
            calc.initialize(params)
            result = calc.calculate_hkl(tth, theta, phi, chi)
            if result["success"]:
                tests.append({
                    "H": result["H"],
                    "K": result["K"],
                    "L": result["L"],
                    "energy": energy,
                    "tth": tth,
                    "theta": theta,
                    "phi": phi,
                    "chi": chi,
                })

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        assert result["success"] is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        assert result["residual_error"] < 1e-5

    def test_round_trip_single_test(self, orthorhombic_params, high_energy):
        """Test round-trip with only one diffraction test (underdetermined).
        Therefore the Sample orientation does not have to match the True Euler
        angles set by true_roll, true_pitch, true_yaw."""
        true_roll, true_pitch, true_yaw = 5.0, 3.0, 7.0

        # Only one test - system is underdetermined but should still find a solution
        angle_sets = [(90.0, 45.0, 0.0, 0.0)]

        tests = self.generate_diffraction_tests(
            orthorhombic_params, high_energy,
            true_roll, true_pitch, true_yaw,
            angle_sets,
        )

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        # Should succeed, but may not find exact angles with only 1 constraint
        assert result["success"] is True
        # Residual should still be small (the one test should be satisfied)
        assert result["residual_error"] < 1e-4

    def test_round_trip_three_tests(self, orthorhombic_params, high_energy):
        """Test round-trip with three diffraction (UB matrix) data."""
        true_roll, true_pitch, true_yaw = 5.0, 3.0, 7.0

        # angle sets are (tth, theta, phi, chi)
        angle_sets = [
            (90.0, 45.0, 0.0, 0.0),
            (60.0, 30.0, 82, 16),
            (120.0, 60.0, -5.0, 10.0),
        ]

        tests = self.generate_diffraction_tests(
            orthorhombic_params, high_energy,
            true_roll, true_pitch, true_yaw,
            angle_sets,
        )

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        assert result["success"] is True
        assert result["residual_error"] < 1e-5

    def test_round_trip_large_orientation(self, orthorhombic_params, high_energy):
        """Test round-trip with large Euler angles (challenging case)."""
        true_roll, true_pitch, true_yaw = 45.0, -30.0, 60.0

        angle_sets = [
            (90.0, 45.0, 0.0, 0.0),
            (60.0, 30.0, 82, 16),
        ]

        tests = self.generate_diffraction_tests(
            orthorhombic_params, high_energy,
            true_roll, true_pitch, true_yaw,
            angle_sets,
        )

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        assert result["success"] is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
        # Should achieve very low residual error with multiple restarts
        assert result["residual_error"] < 1e-5


class TestOrientationFittingEdgeCases:
    """Edge case tests for orientation fitting."""

    @pytest.fixture
    def orthorhombic_params(self):
        """Orthorhombic lattice parameters."""
        return LATTICE_CONFIGS["orthorhombic"].copy()

    def test_empty_tests_list(self, orthorhombic_params):
        """Should return failure for empty tests list."""
        result = fit_orientation_from_diffraction_tests(orthorhombic_params, [])

        assert result["success"] is False
        assert "No diffraction tests provided" in result["message"]

    def test_missing_required_key(self, orthorhombic_params):
        """Should return failure if a test is missing required keys."""
        tests = [
            {"H": 0.1, "K": 0.2, "L": 0.3},  # Missing energy, tth, theta, phi, chi
        ]

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        assert result["success"] is False

    def test_returns_individual_errors(self, orthorhombic_params):
        """Result should include individual errors for each test."""
        true_roll, true_pitch, true_yaw = 5.0, 3.0, 7.0
        energy = 3000.0

        calc = OrientationCalculator()
        params = {
            **orthorhombic_params,
            "energy": energy,
            "roll": true_roll,
            "pitch": true_pitch,
            "yaw": true_yaw,
        }
        calc.initialize(params)

        tests = []
        for tth, theta, phi, chi in [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 10.0, 5.0)]:
            result = calc.calculate_hkl(tth, theta, phi, chi)
            tests.append({
                "H": result["H"],
                "K": result["K"],
                "L": result["L"],
                "energy": energy,
                "tth": tth,
                "theta": theta,
                "phi": phi,
                "chi": chi,
            })

        result = fit_orientation_from_diffraction_tests(orthorhombic_params, tests)

        assert "individual_errors" in result
        assert len(result["individual_errors"]) == 2

        # Each error should have expected and calculated values
        for error in result["individual_errors"]:
            assert "H_expected" in error
            assert "H_calculated" in error
            assert "H_error" in error


class TestOrientationFittingWithDifferentCrystals:
    """Test orientation fitting with different crystal systems."""

    @pytest.mark.parametrize("crystal_type", ["hexagonal", "monoclinic", "triclinic"])
    def test_round_trip_different_crystals(self, crystal_type):
        """Test round-trip works for different crystal systems."""
        lattice_params = LATTICE_CONFIGS[crystal_type].copy()
        energy = 3000.0
        true_roll, true_pitch, true_yaw = 10.0, -5.0, 15.0

        calc = OrientationCalculator()
        params = {
            **lattice_params,
            "energy": energy,
            "roll": true_roll,
            "pitch": true_pitch,
            "yaw": true_yaw,
        }
        calc.initialize(params)

        tests = []
        for tth, theta, phi, chi in [
            (90.0, 45.0, 0.0, 0.0),
            (60.0, 30.0, 10.0, 5.0),
        ]:
            result = calc.calculate_hkl(tth, theta, phi, chi)
            if result["success"]:
                tests.append({
                    "H": result["H"],
                    "K": result["K"],
                    "L": result["L"],
                    "energy": energy,
                    "tth": tth,
                    "theta": theta,
                    "phi": phi,
                    "chi": chi,
                })

        result = fit_orientation_from_diffraction_tests(lattice_params, tests)

        assert result["success"] is True
        check_orientation(result, true_roll, true_pitch, true_yaw)
