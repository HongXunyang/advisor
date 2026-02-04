"""Tests for BrillouinCalculator class."""
import numpy as np
import pytest

from advisor.features.scattering_geometry.domain import BrillouinCalculator
from tests.conftest import ALL_CRYSTAL_TYPES


class TestBrillouinCalculatorInitialization:
    """Tests for calculator initialization."""
    
    def test_not_initialized_by_default(self):
        """Calculator should not be initialized before calling initialize()."""
        calc = BrillouinCalculator()
        assert not calc.is_initialized()
    
    def test_initialized_after_init(self, calculator_params):
        """Calculator should be initialized after calling initialize()."""
        calc = BrillouinCalculator()
        result = calc.initialize(calculator_params)
        assert result is True
        assert calc.is_initialized()
    
    def test_calculate_raises_if_not_initialized(self):
        """Calculations should raise error if not initialized."""
        calc = BrillouinCalculator()
        with pytest.raises(ValueError, match="not initialized"):
            calc.calculate_angles(H=0.1, K=0.1, L=-0.5, fixed_angle=0.0)





class TestCalculateAngles:
    """Tests for calculate_angles method."""
    
    def test_returns_success_for_valid_input(self, initialized_calculator):
        """Should return success=True for reachable HKL point."""
        result = initialized_calculator.calculate_angles(
            H=0.1, K=0.1, L=-0.5,
            fixed_angle=0.0,
            fixed_angle_name="chi",
        )
        
        assert result["success"] is True
        assert result["error"] is None
    
    def test_returns_lists(self, initialized_calculator):
        """Angle values should be returned as lists."""
        result = initialized_calculator.calculate_angles(
            H=0.1, K=0.1, L=-0.5,
            fixed_angle=0.0,
            fixed_angle_name="chi",
        )
        
        assert isinstance(result["tth"], list)
        assert isinstance(result["theta"], list)
        assert isinstance(result["phi"], list)
        assert isinstance(result["chi"], list)
        assert isinstance(result["feasible"], list)
    
    def test_includes_hkl_in_result(self, initialized_calculator):
        """Result should include the input HKL values."""
        H, K, L = 0.15, 0.1, -0.3
        result = initialized_calculator.calculate_angles(
            H=H, K=K, L=L,
            fixed_angle=0.0,
            fixed_angle_name="chi",
        )
        
        assert result["H"] == H
        assert result["K"] == K
        assert result["L"] == L
    
    def test_includes_number_of_solutions(self, initialized_calculator):
        """Result should include number_of_solutions field."""
        result = initialized_calculator.calculate_angles(
            H=0.1, K=0.1, L=-0.5,
            fixed_angle=0.0,
            fixed_angle_name="chi",
        )
        
        assert "number_of_solutions" in result
        assert result["number_of_solutions"] >= 1
        assert result["number_of_solutions"] <= 2


class TestRoundTrip:
    """Round-trip tests: HKL -> Angles -> HKL for all crystal types."""
    
    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_hkl_to_angles_to_hkl_all_solutions(self, make_calculator, crystal_type):
        """Converting HKL to angles and back should give original HKL for ALL solutions."""
        calc = make_calculator(crystal_type)
        
        # Original HKL
        H_orig, K_orig, L_orig = -0.1, -0.1, -0.5
        
        # HKL -> Angles
        angles_result = calc.calculate_angles(
            H=H_orig, K=K_orig, L=L_orig,
            fixed_angle=0.0,
            fixed_angle_name="chi",
        )
        
        assert angles_result["success"], f"Failed for {crystal_type}"
        
        num_solutions = angles_result["number_of_solutions"]
        assert num_solutions >= 1, f"Should find at least one solution for {crystal_type}"
        
        # Test ALL solutions, not just the first
        for sol_idx in range(num_solutions):
            tth = angles_result["tth"][sol_idx]
            theta = angles_result["theta"][sol_idx]
            phi = angles_result["phi"][sol_idx]
            chi = angles_result["chi"][sol_idx]
            
            # Angles -> HKL
            hkl_result = calc.calculate_hkl(
                tth=tth, theta=theta, phi=phi, chi=chi
            )
            
            assert hkl_result["success"], \
                f"[{crystal_type}] Solution {sol_idx + 1} failed to convert back"
            
            # Should recover original HKL
            assert hkl_result["H"] == pytest.approx(H_orig, abs=0.01), \
                f"[{crystal_type}] H mismatch for solution {sol_idx + 1}: got {hkl_result['H']}, expected {H_orig}"
            assert hkl_result["K"] == pytest.approx(K_orig, abs=0.01), \
                f"[{crystal_type}] K mismatch for solution {sol_idx + 1}: got {hkl_result['K']}, expected {K_orig}"
            assert hkl_result["L"] == pytest.approx(L_orig, abs=0.01), \
                f"[{crystal_type}] L mismatch for solution {sol_idx + 1}: got {hkl_result['L']}, expected {L_orig}"
    
    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_round_trip_multiple_hkl_points_all_solutions(self, make_calculator, crystal_type):
        """Round-trip test for multiple HKL points, testing ALL solutions."""
        calc = make_calculator(crystal_type)
        
        test_points = [
            (-0.1, -0.1, -0.3),
            (-0.15, -0.05, -0.4),
            (-0.05, -0.15, -0.2),
        ]
        
        for H_orig, K_orig, L_orig in test_points:
            # HKL -> Angles
            angles_result = calc.calculate_angles(
                H=H_orig, K=K_orig, L=L_orig,
                fixed_angle=0.0,
                fixed_angle_name="chi",
            )
            
            if not angles_result["success"]:
                continue  # Skip unreachable points
            
            num_solutions = angles_result["number_of_solutions"]
            
            # Test ALL solutions for this HKL point
            for sol_idx in range(num_solutions):
                hkl_result = calc.calculate_hkl(
                    tth=angles_result["tth"][sol_idx],
                    theta=angles_result["theta"][sol_idx],
                    phi=angles_result["phi"][sol_idx],
                    chi=angles_result["chi"][sol_idx],
                )
                
                # Verify round-trip for this solution
                assert hkl_result["H"] == pytest.approx(H_orig, abs=0.01), \
                    f"[{crystal_type}] H mismatch for {(H_orig, K_orig, L_orig)} solution {sol_idx + 1}"
                assert hkl_result["K"] == pytest.approx(K_orig, abs=0.01), \
                    f"[{crystal_type}] K mismatch for {(H_orig, K_orig, L_orig)} solution {sol_idx + 1}"
                assert hkl_result["L"] == pytest.approx(L_orig, abs=0.01), \
                    f"[{crystal_type}] L mismatch for {(H_orig, K_orig, L_orig)} solution {sol_idx + 1}"
    

class TestCalculateAnglesTthFixed:
    """Tests for calculate_angles_tth_fixed method."""
    
    def test_solves_for_missing_hkl_component(self, initialized_calculator):
        """Should solve for the None HKL component."""
        result = initialized_calculator.calculate_angles_tth_fixed(
            tth=150.0,
            H=0.1,
            K=0.1,
            L=None,  # Solve for L
            fixed_angle_name="chi",
            fixed_angle=0.0,
        )
        
        assert result["success"]
        # L should now be a float (solved value)
        assert isinstance(result["L"], float)
        assert result["L"] != 0.0  # Should have computed a value
    
    def test_returns_multiple_solutions(self, initialized_calculator):
        """Should return up to 2 solutions."""
        result = initialized_calculator.calculate_angles_tth_fixed(
            tth=150.0,
            H=-0.1,
            K=-0.1,
            L=None,
            fixed_angle_name="chi",
            fixed_angle=0.0,
        )
        
        assert result["success"]
        assert "number_of_solutions" in result
        assert len(result["tth"]) == result["number_of_solutions"]


class TestFeasibility:
    """Tests for feasibility checking."""
    
    def test_feasible_when_theta_between_zero_and_tth(self, initialized_calculator):
        """Solution should be feasible when 0 < theta < tth."""
        result = initialized_calculator.calculate_angles(
            H=-0.1, K=-0.1, L=-0.5,
            fixed_angle=0.0,
            fixed_angle_name="chi",
        )
        
        if result["success"]:
            for i in range(result["number_of_solutions"]):
                tth = result["tth"][i]
                theta = result["theta"][i]
                expected_feasible = (theta > 0) and (theta < tth)
                assert result["feasible"][i] == expected_feasible


class TestCalculateHKL:
    """Tests for calculate_hkl method (angles -> HKL) for all crystal types."""
    
    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_returns_success_for_valid_angles(self, make_calculator, crystal_type):
        """Should return success=True for valid angle inputs."""
        calc = make_calculator(crystal_type)
        
        result = calc.calculate_hkl(
            tth=120.0,
            theta=60.0,
            phi=0.0,
            chi=0.0,
        )
        
        assert result["success"] is True, f"Failed for {crystal_type}"
        assert result["error"] is None
    
    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_returns_hkl_values(self, make_calculator, crystal_type):
        """Result should contain H, K, L float values."""
        calc = make_calculator(crystal_type)
        
        result = calc.calculate_hkl(
            tth=120.0,
            theta=60.0,
            phi=0.0,
            chi=0.0,
        )
        
        assert "H" in result
        assert "K" in result
        assert "L" in result
        assert isinstance(result["H"], float), f"[{crystal_type}] H is not float"
        assert isinstance(result["K"], float), f"[{crystal_type}] K is not float"
        assert isinstance(result["L"], float), f"[{crystal_type}] L is not float"
    
    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_returns_input_angles(self, make_calculator, crystal_type):
        """Result should echo back the input angles."""
        calc = make_calculator(crystal_type)
        tth, theta, phi, chi = 120.0, 60.0, 15.0, 5.0
        
        result = calc.calculate_hkl(
            tth=tth, theta=theta, phi=phi, chi=chi
        )
        
        assert result["tth"] == tth, f"[{crystal_type}] tth mismatch"
        assert result["theta"] == theta, f"[{crystal_type}] theta mismatch"
        assert result["phi"] == phi, f"[{crystal_type}] phi mismatch"
        assert result["chi"] == chi, f"[{crystal_type}] chi mismatch"
    
    def test_raises_if_not_initialized(self):
        """Should raise error if calculator not initialized."""
        calc = BrillouinCalculator()
        
        with pytest.raises(ValueError, match="not initialized"):
            calc.calculate_hkl(tth=120.0, theta=60.0, phi=0.0, chi=0.0)
    
    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    @pytest.mark.parametrize("angles", [
        (90.0, 45.0, 0.0, 0.0),
        (120.0, 60.0, 0.0, 0.0),
        (150.0, 75.0, 10.0, 5.0),
        (60.0, 30.0, -15.0, 0.0),
    ])
    def test_various_angle_combinations(self, make_calculator, crystal_type, angles):
        """Test that various angle combinations work for all crystal types."""
        calc = make_calculator(crystal_type)
        tth, theta, phi, chi = angles
        
        result = calc.calculate_hkl(tth=tth, theta=theta, phi=phi, chi=chi)
        
        assert result["success"], f"[{crystal_type}] Failed for angles {angles}"
        assert isinstance(result["H"], float)
        assert isinstance(result["K"], float)
        assert isinstance(result["L"], float)
    
    # =========================================================================
    # Known angle-HKL pairs (PLACEHOLDERS - fill in with verified values)
    # =========================================================================
    # TODO: Fill in the expected H, K, L values for these known angle combinations
    #       These should be verified experimentally or calculated independently
    #       Note: Each crystal type may need its own set of verified pairs
    
    @pytest.mark.parametrize("angles,expected_hkl", [
        # Format: (tth, theta, phi, chi), (H, K, L)
        # Example placeholder for TETRAGONAL - replace with actual verified values:
        ((120.0, 60.0, 0.0, 0.0), (0.0, 0.0, -0.5)),  # TODO: verify
        ((150.0, 75.0, 0.0, 0.0), (0.0, 0.0, -0.6)),  # TODO: verify
        # Add more known pairs here...
    ])
    def test_known_angle_hkl_pairs_tetragonal(self, make_calculator, angles, expected_hkl):
        """Test known angle-HKL pairs for TETRAGONAL crystal."""
        """
        calc = make_calculator("tetragonal")
        tth, theta, phi, chi = angles
        expected_H, expected_K, expected_L = expected_hkl
        
        result = calc.calculate_hkl(tth=tth, theta=theta, phi=phi, chi=chi)
        
        assert result["success"]
        assert result["H"] == pytest.approx(expected_H, abs=0.01), \
            f"H mismatch: got {result['H']}, expected {expected_H}"
        assert result["K"] == pytest.approx(expected_K, abs=0.01), \
            f"K mismatch: got {result['K']}, expected {expected_K}"
        assert result["L"] == pytest.approx(expected_L, abs=0.01), \
            f"L mismatch: got {result['L']}, expected {expected_L}"
        """
    # TODO: Add similar test_known_angle_hkl_pairs_cubic, _hexagonal, etc.
    # when you have verified angle-HKL pairs for those crystal types
    
