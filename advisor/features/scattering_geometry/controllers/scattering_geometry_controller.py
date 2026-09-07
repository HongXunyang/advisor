"""Controller for the scattering geometry (Brillouin) feature."""

from advisor.controllers.feature_controller import FeatureController
from advisor.features.scattering_geometry.domain import BrillouinCalculator
from advisor.features.scattering_geometry.ui.scattering_geometry_tab import ScatteringGeometryTab


class ScatteringGeometryController(FeatureController):
    """Manages the Brillouin/scattering geometry feature."""

    title = "Scattering Geometry"
    description = "Convert angles ↔ HKL, scan HKL trajectories, and visualize scattering geometry."
    icon = "bz_calculator.png"

    def __init__(self, app_controller):
        super().__init__(app_controller)
        self.calculator = BrillouinCalculator()
        self.view = self.build_view()

    def build_view(self):
        return ScatteringGeometryTab(controller=self, calculator=self.calculator)

    def set_parameters(self, params: dict):
        self.calculator.initialize(params=params)
        if self.view and hasattr(self.view, "set_parameters"):
            self.view.set_parameters(params)

    def invalidate_structure(self):
        """Discard the live calculator and all structure-dependent view state.

        A fresh ``BrillouinCalculator`` (rather than adding reset semantics
        to the calculator class) is the simplest way to guarantee
        ``is_initialized()`` is False until the next ``set_parameters()``.
        """
        self.calculator = BrillouinCalculator()
        if self.view and hasattr(self.view, "calculator"):
            self.view.calculator = self.calculator
        if self.view and hasattr(self.view, "clear"):
            self.view.clear()
