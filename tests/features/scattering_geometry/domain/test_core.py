"""Tests for core calculation functions."""
import pytest
import numpy as np

from advisor.features.scattering_geometry.domain.core import (
    _calculate_angles_chi_fixed,
    _calculate_angles_phi_fixed,
    _calculate_angles_tth_fixed,
    _calculate_hkl,
    calculate_k_magnitude,
    calculate_tth_from_k_magnitude,
    process_angle,
)


class TestProcessAngle:
    """Tests for angle normalization."""
    
    def test_angle_in_range(self):
        """Angles already in (-180, 180] should be unchanged."""
        assert process_angle(45.0) == 45.0
        assert process_angle(-90.0) == -90.0
        assert process_angle(180.0) == 180.0
    
    def test_angle_above_180(self):
        """Angles > 180 should wrap to negative."""
        assert process_angle(270.0) == -90.0
        assert process_angle(360.0) == 0.0
        assert process_angle(450.0) == 90.0
    
    def test_angle_below_minus_180(self):
        """Angles < -180 should wrap to positive."""
        assert process_angle(-270.0) == 90.0
        assert process_angle(-360.0) == 0.0


class TestKMagnitude:
    """Tests for momentum transfer magnitude calculations."""
    
    def test_k_magnitude_zero_angle(self):
        """k magnitude should be 0 at tth=0."""
        k_in = 1.0
        assert calculate_k_magnitude(k_in, tth=0.0) == pytest.approx(0.0, abs=1e-10)
    
    def test_k_magnitude_180_degrees(self):
        """k magnitude should be 2*k_in at tth=180°."""
        k_in = 1.0
        assert calculate_k_magnitude(k_in, tth=180.0) == pytest.approx(2.0, abs=1e-10)
    
    @pytest.mark.parametrize("k_in", [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0])
    @pytest.mark.parametrize("tth_original", [10.0, 30.0, 60.0, 90.0, 120.0, 150.0, 170.0])
    def test_k_magnitude_round_trip(self, k_in, tth_original):
        """k_magnitude -> tth -> k_magnitude should be consistent."""
        k_mag = calculate_k_magnitude(k_in, tth_original)
        tth_recovered = calculate_tth_from_k_magnitude(k_in, k_mag)
        assert tth_recovered == pytest.approx(tth_original, abs=1e-6)
    
    @pytest.mark.parametrize("k_in", [0.1, 0.5, 1.0, 2.0])
    def test_k_magnitude_90_degrees(self, k_in):
        """k magnitude should be sqrt(2)*k_in at tth=90°."""
        expected = np.sqrt(2) * k_in
        assert calculate_k_magnitude(k_in, tth=90.0) == pytest.approx(expected, abs=1e-10)
    
    @pytest.mark.parametrize("k_in", [0.1, 0.5, 1.0, 2.0])
    def test_k_magnitude_60_degrees(self, k_in):
        """k magnitude should be k_in at tth=60°."""
        assert calculate_k_magnitude(k_in, tth=60.0) == pytest.approx(k_in, abs=1e-10)


class TestCalculateAnglesChiFixed:
    """Tests for HKL -> angles calculation with chi fixed."""
    
    def test_returns_dict_with_required_keys(self, tetragonal_lattice_params, no_rotation_euler):
        """Result should be a dict with all required keys."""
        params = {**tetragonal_lattice_params, **no_rotation_euler}
        k_in = 0.47  # Approximate for 930 eV
        
        result = _calculate_angles_chi_fixed(
            k_in=k_in,
            H=0.1, K=0.1, L=-0.5,
            a=params["a"], b=params["b"], c=params["c"],
            alpha=params["alpha"], beta=params["beta"], gamma=params["gamma"],
            roll=params["roll"], pitch=params["pitch"], yaw=params["yaw"],
            chi_fixed=0.0,
        )
        
        assert isinstance(result, dict)
        assert "tth" in result
        assert "theta" in result
        assert "phi" in result
        assert "chi" in result
        assert "number_of_solutions" in result
        
        # Values should be lists
        assert isinstance(result["tth"], list)
        assert isinstance(result["theta"], list)
    
    def test_finds_at_least_one_solution(self, tetragonal_lattice_params, no_rotation_euler):
        """Should find at least one solution for a reachable HKL point."""
        params = {**tetragonal_lattice_params, **no_rotation_euler}
        k_in = 0.47
        
        result = _calculate_angles_chi_fixed(
            k_in=k_in,
            H=0.1, K=0.1, L=-0.5,
            a=params["a"], b=params["b"], c=params["c"],
            alpha=params["alpha"], beta=params["beta"], gamma=params["gamma"],
            roll=params["roll"], pitch=params["pitch"], yaw=params["yaw"],
            chi_fixed=0.0,
        )
        
        assert result["number_of_solutions"] >= 1
    
    def test_chi_is_fixed_value(self, tetragonal_lattice_params, no_rotation_euler):
        """All chi values in result should equal the fixed chi."""
        params = {**tetragonal_lattice_params, **no_rotation_euler}
        k_in = 0.47
        chi_fixed = 15.0
        
        result = _calculate_angles_chi_fixed(
            k_in=k_in,
            H=0.1, K=0.1, L=-0.5,
            a=params["a"], b=params["b"], c=params["c"],
            alpha=params["alpha"], beta=params["beta"], gamma=params["gamma"],
            roll=params["roll"], pitch=params["pitch"], yaw=params["yaw"],
            chi_fixed=chi_fixed,
        )
        
        for chi_val in result["chi"]:
            assert chi_val == pytest.approx(chi_fixed, abs=1e-6)


class TestCalculateAnglesPhiFixed:
    """Tests for HKL -> angles calculation with phi fixed."""
    
    def test_phi_is_fixed_value(self, tetragonal_lattice_params, no_rotation_euler):
        """All phi values in result should equal the fixed phi."""
        params = {**tetragonal_lattice_params, **no_rotation_euler}
        k_in = 0.47
        phi_fixed = 10.0
        
        result = _calculate_angles_phi_fixed(
            k_in=k_in,
            H=0.1, K=0.1, L=-0.5,
            a=params["a"], b=params["b"], c=params["c"],
            alpha=params["alpha"], beta=params["beta"], gamma=params["gamma"],
            roll=params["roll"], pitch=params["pitch"], yaw=params["yaw"],
            phi_fixed=phi_fixed,
        )
        
        for phi_val in result["phi"]:
            assert phi_val == pytest.approx(phi_fixed, abs=1e-6)


class TestMultipleSolutions:
    """Tests for finding multiple solutions."""
    
    def test_two_solutions_are_distinct(self, tetragonal_lattice_params, no_rotation_euler):
        """When 2 solutions are found, they should differ by more than 1 degree."""
        params = {**tetragonal_lattice_params, **no_rotation_euler}
        k_in = 0.47
        
        result = _calculate_angles_chi_fixed(
            k_in=k_in,
            H=0.1, K=0.1, L=-0.5,
            a=params["a"], b=params["b"], c=params["c"],
            alpha=params["alpha"], beta=params["beta"], gamma=params["gamma"],
            roll=params["roll"], pitch=params["pitch"], yaw=params["yaw"],
            chi_fixed=0.0,
        )
        
        if result["number_of_solutions"] == 2:
            theta_diff = abs(result["theta"][0] - result["theta"][1])
            phi_diff = abs(result["phi"][0] - result["phi"][1])
            # At least one angle should differ by more than 1 degree
            assert theta_diff > 1.0 or phi_diff > 1.0
