"""Controller for the Structure Factor feature."""

from advisor.controllers.feature_controller import FeatureController
from advisor.features.structure_factor.domain import StructureFactorCalculator
from advisor.features.structure_factor.ui.structure_factor_tab import StructureFactorTab


class StructureFactorController(FeatureController):
    """Manages structure factor calculations."""

    title = "Structure Factor"
    description = "Calculate structure factors from CIF files using Dans_Diffraction."
    icon = "sf_calculator.png"

    def __init__(self, app_controller):
        super().__init__(app_controller)
        self.calculator = StructureFactorCalculator()
        self.view = self.build_view()

    def build_view(self):
        return StructureFactorTab(controller=self, calculator=self.calculator)

    def set_parameters(self, params: dict):
        if self.view and hasattr(self.view, "set_parameters"):
            self.view.set_parameters(params)
