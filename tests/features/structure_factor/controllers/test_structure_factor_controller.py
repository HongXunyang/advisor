"""Tests for StructureFactorController wiring and orchestration."""
import pytest

from advisor.features.structure_factor.controllers.structure_factor_controller import (
    StructureFactorController,
)
from advisor.features.structure_factor.domain import StructureFactorCalculator
from advisor.features.structure_factor.ui.structure_factor_tab import StructureFactorTab
from advisor.features.scattering_geometry.domain import BrillouinCalculator

from tests.conftest import LATTICE_CONFIGS


class _FakeAppController:
    """Minimal stand-in for AppController, matching the duck-typed contract
    StructureFactorTab relies on (.main_window, .get_parameters())."""

    main_window = None

    def get_parameters(self):
        return {}


@pytest.fixture
def controller(qapp):
    return StructureFactorController(app_controller=_FakeAppController())


@pytest.fixture
def cubic_params():
    return {**LATTICE_CONFIGS["cubic"], "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0}


class TestStructureFactorController:
    def test_build_view_creates_calculators_and_tab(self, controller):
        assert isinstance(controller.calculator, StructureFactorCalculator)
        assert isinstance(controller.brillouin_calculator, BrillouinCalculator)
        assert isinstance(controller.view, StructureFactorTab)
        assert controller.brillouin_calculator.is_initialized() is False

    def test_metadata(self):
        assert StructureFactorController.title == "Structure Factor"
        assert StructureFactorController.icon == "sf_calculator.png"

    def test_set_parameters_initializes_brillouin_calculator(self, controller, cubic_params):
        controller.set_parameters(cubic_params)
        assert controller.parameters == cubic_params
        assert controller.brillouin_calculator.is_initialized() is True

    def test_set_parameters_with_none_does_not_initialize(self, controller):
        controller.set_parameters(None)
        assert controller.parameters is None
        assert controller.brillouin_calculator.is_initialized() is False

    def test_run_check_accessibility_before_initialize_fails(self, controller):
        result = controller.run_check_accessibility(
            plane_params={"U": (1, 0, 0), "V": (0, 1, 0), "C": (0, 0, 0), "u_range": 2, "v_range": 2},
            constraints={},
            energy_ev=10000.0,
        )
        assert result["success"] is False
        assert "not yet initialized" in result["error"]

    def test_run_check_accessibility_after_initialize_succeeds(self, controller, cubic_params):
        controller.set_parameters(cubic_params)
        constraints = {
            "tth_min": 0.0, "tth_max": 180.0,
            "theta_min": -180.0, "theta_max": 180.0,
            "chi_min": -180.0, "chi_max": 180.0,
            "phi_min": -180.0, "phi_max": 180.0,
            "fixed_angle_name": "chi",
            "fixed_angle_value": 0.0,
        }
        result = controller.run_check_accessibility(
            plane_params={"U": (1, 0, 0), "V": (0, 1, 0), "C": (0, 0, 0), "u_range": 2, "v_range": 2},
            constraints=constraints,
            energy_ev=10000.0,
        )
        assert result["success"] is True
        assert len(result["uv_points"]) == len(result["hkl_points"]) == 9

    def test_run_check_accessibility_does_not_mutate_main_calculator_energy(self, controller, cubic_params):
        """run_check_accessibility copies the calculator before changing energy,
        so the controller's own brillouin_calculator.energy must stay untouched."""
        controller.set_parameters(cubic_params)
        original_energy = controller.brillouin_calculator.energy

        controller.run_check_accessibility(
            plane_params={"U": (1, 0, 0), "V": (0, 1, 0), "C": (0, 0, 0), "u_range": 1, "v_range": 1},
            constraints={
                "tth_min": 0.0, "tth_max": 180.0,
                "theta_min": -180.0, "theta_max": 180.0,
                "chi_min": -180.0, "chi_max": 180.0,
                "phi_min": -180.0, "phi_max": 180.0,
                "fixed_angle_name": "chi",
                "fixed_angle_value": 0.0,
            },
            energy_ev=99999.0,
        )
        assert controller.brillouin_calculator.energy == original_energy
