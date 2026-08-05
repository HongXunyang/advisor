"""Tests for AppController: top-level wiring, parameter propagation, config loading."""
import pytest

from advisor.controllers.app_controller import AppController
from advisor.features.scattering_geometry.controllers import ScatteringGeometryController
from advisor.features.structure_factor.controllers import StructureFactorController

from tests.conftest import LATTICE_CONFIGS


@pytest.fixture
def controller(qapp):
    return AppController(qt_app=qapp)


@pytest.fixture
def cubic_params():
    return {**LATTICE_CONFIGS["cubic"], "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0}


class TestAppControllerConstruction:
    def test_builds_both_feature_controllers(self, controller):
        assert len(controller.features) == 2
        assert isinstance(controller.features[0], ScatteringGeometryController)
        assert isinstance(controller.features[1], StructureFactorController)

    def test_feature_tabs_added_to_main_window(self, controller):
        assert controller.main_window.tab_widget.count() == len(controller.features)

    def test_parameters_start_unset(self, controller):
        assert controller.parameters is None
        assert controller.get_parameters() == {}

    def test_loads_real_app_config(self, controller):
        assert controller.config["app_name"] == "Advisor-Scattering"
        assert "window_size" in controller.config


class TestApplyParameters:
    def test_propagates_to_all_feature_controllers(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)

        assert controller.parameters == cubic_params
        scattering_geometry, structure_factor = controller.features
        assert scattering_geometry.calculator.is_initialized() is True
        assert structure_factor.brillouin_calculator.is_initialized() is True

    def test_get_parameters_reflects_applied_params(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)
        assert controller.get_parameters() == cubic_params


class TestResetParameters:
    def test_clears_parameters_and_shows_init(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)
        assert controller.parameters is not None

        controller.reset_parameters()

        assert controller.parameters is None
        assert controller.get_parameters() == {}
