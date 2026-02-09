"""Controller for the Structure Factor feature."""

from advisor.controllers.feature_controller import FeatureController
from advisor.features.scattering_geometry.domain.brillouin_calculator import (
    BrillouinCalculator,
)
from advisor.features.structure_factor.domain import (
    StructureFactorCalculator,
    check_accessibility,
    generate_hkl_points_on_plane,
)
from advisor.features.structure_factor.ui.structure_factor_tab import (
    StructureFactorTab,
)


class StructureFactorController(FeatureController):
    """Manages structure factor calculations."""

    title = "Structure Factor"
    description = "Calculate structure factors from CIF files using Dans_Diffraction."
    icon = "sf_calculator.png"

    def __init__(self, app_controller):
        super().__init__(app_controller)
        self.calculator = StructureFactorCalculator()
        self.brillouin_calculator = BrillouinCalculator()
        self.view = self.build_view()
        self.parameters = None

    def build_view(self):
        return StructureFactorTab(controller=self, calculator=self.calculator)

    def set_parameters(self, params: dict):
        self.parameters = params
        # Initialize the BrillouinCalculator with the global lattice params
        if params:
            self.brillouin_calculator.initialize(params)
        if self.view and hasattr(self.view, "set_parameters"):
            self.view.set_parameters(params)

    def run_check_accessibility(self, plane_params, constraints, energy_ev):
        """Check accessibility of diffraction points on a customized plane.

        This method orchestrates the domain-level calculation.

        Args:
            plane_params: dict with keys ``U``, ``V``, ``C``, ``u_range``,
                ``v_range`` describing the HKL plane.
            constraints: dict from ``AccessibleRegionControls.get_parameters()``.
            energy_ev: float, X-ray energy in eV (from the configuration panel).

        Returns:
            dict with ``success`` (bool), ``inaccessible`` (list of uv_point
            dicts), ``uv_points``, ``hkl_points``, and optionally ``error``.
        """
        if not self.brillouin_calculator.is_initialized():
            return {
                "success": False,
                "error": "The scattering geometry calculator is not yet initialized.\n"
                         "Please make sure the global parameters have been set.",
            }

        # Make a copy so the main calculator state isn't mutated
        calc = self.brillouin_calculator.copy_itself()
        calc.set_energy(energy_ev)

        U = plane_params["U"]
        V = plane_params["V"]
        C = plane_params["C"]
        u_range = plane_params["u_range"]
        v_range = plane_params["v_range"]

        uv_points, hkl_points = generate_hkl_points_on_plane(
            U, V, C, u_range, v_range
        )

        inaccessible = check_accessibility(
            uv_points, hkl_points, calc, constraints
        )

        return {
            "success": True,
            "inaccessible": inaccessible,
            "uv_points": uv_points,
            "hkl_points": hkl_points,
        }
