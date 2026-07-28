"""Tests for core calculation functions."""
import pytest
import numpy as np

from advisor.domain.core import Sample
from advisor.features.scattering_geometry.domain.core import (
    _calculate_angles_chi_fixed,
    _calculate_angles_phi_fixed,
    _calculate_angles_tth_fixed,
    _calculate_hkl,
    _solve_sinusoidal_equation,
    calculate_k_magnitude,
    calculate_tth_from_k_magnitude,
    process_angle,
)

CUBIC = dict(a=4.0, b=4.0, c=4.0, alpha=90.0, beta=90.0, gamma=90.0)
TETRAGONAL = dict(a=4.0, b=4.0, c=12.0, alpha=90.0, beta=90.0, gamma=90.0)
NO_ROTATION = dict(roll=0.0, pitch=0.0, yaw=0.0)
K_IN = 2 * np.pi / (12398.42 / 930.0)  # 930 eV


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


class TestSolveSinusoidalEquation:
    """Tests for the closed-form A*cos(x) + B*sin(x) = D solver."""

    def test_two_distinct_roots(self):
        """cos(x) = 0 should give x = +-90 degrees."""
        roots = _solve_sinusoidal_equation(A=1.0, B=0.0, D=0.0)
        assert roots is not None and len(roots) == 2
        degrees = sorted(np.degrees(r) for r in roots)
        assert degrees == pytest.approx([-90.0, 90.0], abs=1e-8)

    def test_no_real_roots(self):
        """|D| > R means the target is out of reach."""
        assert _solve_sinusoidal_equation(A=1.0, B=0.0, D=2.0) == []

    def test_tangent_single_root(self):
        """|D| == R exactly should collapse to one root."""
        roots = _solve_sinusoidal_equation(A=1.0, B=0.0, D=1.0)
        assert roots is not None and len(roots) == 1
        assert roots[0] == pytest.approx(0.0, abs=1e-8)

    def test_degenerate_compatible_continuum(self):
        """R~=0 and D~=0: every x satisfies the equation."""
        assert _solve_sinusoidal_equation(A=0.0, B=0.0, D=0.0) is None

    def test_degenerate_incompatible(self):
        """R~=0 but D far from 0: no x can satisfy the equation."""
        assert _solve_sinusoidal_equation(A=0.0, B=0.0, D=5.0) == []

    @pytest.mark.parametrize("A,B,D", [
        (1.0, 0.5, 0.3),
        (-0.7, 1.2, 0.9),
        (2.0, -1.5, 1.0),
        (0.1, 0.1, 0.05),
        (-3.0, -2.0, 3.5),
    ])
    def test_roots_satisfy_equation(self, A, B, D):
        """Every returned root should exactly satisfy the original equation."""
        roots = _solve_sinusoidal_equation(A, B, D)
        assert roots  # all cases chosen so |D| <= hypot(A, B)
        for x in roots:
            assert A * np.cos(x) + B * np.sin(x) == pytest.approx(D, abs=1e-8)


class TestCalculateAnglesChiFixedAnalytic:
    """Tests for the closed-form chi-fixed solver's numerical behavior."""

    def test_matches_golden_reference_value(self):
        """Frozen regression value, independently verified against the old
        fsolve-based implementation (see plan / derivation doc)."""
        result = _calculate_angles_chi_fixed(
            K_IN, H=0.1, K=0.1, L=-0.5, **TETRAGONAL, **NO_ROTATION, chi_fixed=0.0,
        )
        assert result["number_of_solutions"] == 1
        assert result["tth"][0] == pytest.approx(42.723571380567314, abs=1e-6)
        assert result["theta"][0] == pytest.approx(138.5874136888476, abs=1e-6)
        assert result["phi"][0] == pytest.approx(59.03624346792648, abs=1e-6)

    def test_zero_solutions_incompatible_with_fixed_chi(self):
        """A point that is reachable in tth but not with this chi fixed."""
        result = _calculate_angles_chi_fixed(
            K_IN, H=-0.5, K=-0.3, L=-0.1, **CUBIC, **NO_ROTATION, chi_fixed=70.0,
        )
        assert result["number_of_solutions"] == 0
        assert result == {"tth": [], "theta": [], "phi": [], "chi": [], "number_of_solutions": 0}

    def test_zero_solutions_unreachable_hkl(self):
        """|Q| exceeding 2*k_in makes tth itself undefined."""
        result = _calculate_angles_chi_fixed(
            K_IN, H=5.0, K=5.0, L=5.0, **CUBIC, **NO_ROTATION, chi_fixed=0.0,
        )
        assert result == {"tth": [], "theta": [], "phi": [], "chi": [], "number_of_solutions": 0}

    def test_degenerate_axis_aligned_continuum(self):
        """H along the sample x-axis with chi_fixed=0: phi is undetermined
        (any phi works), so exactly one representative solution is returned
        and it must still round-trip correctly."""
        result = _calculate_angles_chi_fixed(
            K_IN, H=0.3, K=0.0, L=0.0, **CUBIC, **NO_ROTATION, chi_fixed=0.0,
        )
        assert result["number_of_solutions"] == 1

        sample = Sample()
        sample.initialize(**CUBIC, **NO_ROTATION)
        a_vec, b_vec, c_vec = sample.get_real_space_vectors()
        hkl = _calculate_hkl(
            K_IN, result["tth"][0], result["theta"][0], result["phi"][0], result["chi"][0],
            a_vec, b_vec, c_vec,
        )
        assert hkl["H"] == pytest.approx(0.3, abs=1e-6)
        assert hkl["K"] == pytest.approx(0.0, abs=1e-6)
        assert hkl["L"] == pytest.approx(0.0, abs=1e-6)

    def test_degenerate_axis_aligned_incompatible(self):
        """Same axis-aligned H, but chi_fixed != 0: since phi cannot move
        this vector at all, the fixed chi tilt can never be compensated."""
        result = _calculate_angles_chi_fixed(
            K_IN, H=0.3, K=0.0, L=0.0, **CUBIC, **NO_ROTATION, chi_fixed=45.0,
        )
        assert result["number_of_solutions"] == 0


class TestCalculateAnglesPhiFixedAnalytic:
    """Tests for the closed-form phi-fixed solver's numerical behavior."""

    def test_matches_reference_value(self):
        """Cross-checked against the old fsolve-based implementation."""
        result = _calculate_angles_phi_fixed(
            K_IN, H=0.1, K=0.1, L=-0.5, **TETRAGONAL, **NO_ROTATION, phi_fixed=10.0,
        )
        assert result["number_of_solutions"] == 1
        assert result["theta"][0] == pytest.approx(165.70342950679495, abs=1e-6)
        assert result["chi"][0] == pytest.approx(-55.731867877889215, abs=1e-6)

    def test_zero_solutions_unreachable_hkl(self):
        result = _calculate_angles_phi_fixed(
            K_IN, H=5.0, K=5.0, L=5.0, **CUBIC, **NO_ROTATION, phi_fixed=0.0,
        )
        assert result == {"tth": [], "theta": [], "phi": [], "chi": [], "number_of_solutions": 0}

    @pytest.mark.parametrize("phi_fixed", [0.0, 15.0, -30.0, 60.0, -75.0])
    def test_at_most_one_solution_is_structurally_typical(self, phi_fixed):
        """Because calculate_k_vector_in_lab's target always has zero
        z-component, the phi-fixed sub-problem's two chi roots are always
        exactly 180 degrees apart, so (except at the razor-edge chi=+-90
        boundary) at most one of them can lie in the physical [-90, 90]
        range. This differs from the chi-fixed case, where an extra offset
        term generally allows 0, 1, or 2 solutions. See the derivation doc
        for the full argument."""
        result = _calculate_angles_phi_fixed(
            K_IN, H=-0.1, K=-0.1, L=-0.5, **TETRAGONAL, **NO_ROTATION, phi_fixed=phi_fixed,
        )
        assert result["number_of_solutions"] in (0, 1)


class TestCalculateAnglesTthFixedMomentum:
    """Tests for the closed-form quadratic momentum solve."""

    def test_two_momentum_roots(self):
        result = _calculate_angles_tth_fixed(
            K_IN, tth=150.0, **TETRAGONAL, **NO_ROTATION,
            H=-0.1, K=-0.1, L=None, fixed_angle_name="chi", fixed_angle=0.0,
        )
        assert result["number_of_solutions"] == 2
        assert sorted(result["momentum"]) == pytest.approx(
            [-1.6863367602336528, 1.6863367602336528], abs=1e-6
        )

        sample = Sample()
        sample.initialize(**TETRAGONAL, **NO_ROTATION)
        a_vec, b_vec, c_vec = sample.get_real_space_vectors()
        for i in range(result["number_of_solutions"]):
            hkl = _calculate_hkl(
                K_IN, result["tth"][i], result["theta"][i], result["phi"][i], result["chi"][i],
                a_vec, b_vec, c_vec,
            )
            assert hkl["H"] == pytest.approx(-0.1, abs=0.01)
            assert hkl["K"] == pytest.approx(-0.1, abs=0.01)
            assert hkl["L"] == pytest.approx(result["momentum"][i], abs=0.01)

    def test_zero_momentum_roots(self):
        """A tth too small for these two fixed HKL indices to ever reach."""
        result = _calculate_angles_tth_fixed(
            K_IN, tth=10.0, **TETRAGONAL, **NO_ROTATION,
            H=-0.1, K=-0.1, L=None, fixed_angle_name="chi", fixed_angle=0.0,
        )
        assert result == {
            "tth": [], "theta": [], "phi": [], "chi": [], "momentum": [],
            "number_of_solutions": 0,
        }
