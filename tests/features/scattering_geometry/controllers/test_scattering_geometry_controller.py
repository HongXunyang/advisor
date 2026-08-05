"""Tests for ScatteringGeometryController wiring."""
import pytest

from advisor.features.scattering_geometry.controllers.scattering_geometry_controller import (
    ScatteringGeometryController,
)
from advisor.features.scattering_geometry.domain import BrillouinCalculator
from advisor.features.scattering_geometry.ui.scattering_geometry_tab import (
    ScatteringGeometryTab,
)

from tests.conftest import LATTICE_CONFIGS


class _FakeAppController:
    """Minimal stand-in for AppController, matching the duck-typed contract
    ScatteringGeometryTab relies on (.main_window, .get_parameters())."""

    main_window = None

    def get_parameters(self):
        return {}


@pytest.fixture
def controller(qapp):
    return ScatteringGeometryController(app_controller=_FakeAppController())


class TestScatteringGeometryController:
    def test_build_view_creates_calculator_and_tab(self, controller):
        assert isinstance(controller.calculator, BrillouinCalculator)
        assert isinstance(controller.view, ScatteringGeometryTab)
        assert controller.calculator.is_initialized() is False

    def test_metadata(self):
        assert ScatteringGeometryController.title == "Scattering Geometry"
        assert ScatteringGeometryController.icon == "bz_calculator.png"

    def test_set_parameters_initializes_calculator(self, controller):
        params = {**LATTICE_CONFIGS["cubic"], "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0}
        controller.set_parameters(params)
        assert controller.calculator.is_initialized() is True
        a, b, c, alpha, beta, gamma = controller.calculator.lab.get_lattice_parameters()
        assert (a, b, c) == (params["a"], params["b"], params["c"])

    def test_set_parameters_propagates_to_view(self, controller):
        params = {**LATTICE_CONFIGS["tetragonal"], "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0}
        # Should not raise even though the view is a real headless widget.
        controller.set_parameters(params)
        assert controller.view.calculator is controller.calculator
