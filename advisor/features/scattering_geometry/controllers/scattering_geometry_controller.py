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
