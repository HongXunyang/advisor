"""Controller for the Structure Factor feature."""

from advisor.controllers.feature_controller import FeatureController
from advisor.features.scattering_geometry.domain.brillouin_calculator import (
    BrillouinCalculator,
)
from advisor.features.structure_factor.domain import (
    StructureFactorCalculator,
    check_accessibility,
    generate_hkl_points_on_plane,
    generate_hkl_range,
    count_hkl_range,
    build_reflections,
    filter_extinct,
    filter_min_intensity,
    serialize_to_csv,
    serialize_to_json,
    MAX_BULK_REFLECTIONS,
    DEFAULT_EXTINCTION_REL_TOL,
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
        self._reflection_popup = None

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

    def open_reflection_popup(self, default_snapshot=None):
        """Open the shared Reflection List popup.

        Reuses the existing popup instance on repeat calls (refreshing its
        displayed context) rather than creating a duplicate window.

        Args:
            default_snapshot: optional ``ReflectionSnapshot`` to pre-populate
                the table with -- normally captured from the caller's active
                2D plane at the moment it was last drawn (see
                ``HKLPlane2DWidget.get_current_snapshot()`` /
                ``CustomizedPlaneWidget.get_current_snapshot()``), so the
                popup opens already showing "what's on screen" without
                recomputing anything through the (possibly since-mutated)
                shared calculator. Pass None if that view has never been
                successfully calculated.
        """
        if self._reflection_popup is None:
            from advisor.features.structure_factor.ui.reflection_popup import (
                ReflectionPopup,
            )

            self._reflection_popup = ReflectionPopup(controller=self, parent=self.view)

        self._reflection_popup.refresh_from_calculator()
        self._reflection_popup.load_snapshot(default_snapshot)
        self._reflection_popup.show()
        self._reflection_popup.raise_()
        self._reflection_popup.activateWindow()

    def run_bulk_reflection_calculation(
        self,
        h_range,
        k_range,
        l_range,
        exclude_extinct: bool = True,
        rel_tol: float = DEFAULT_EXTINCTION_REL_TOL,
        min_intensity: float = None,
    ) -> dict:
        """Generate and calculate structure factors for a bounded HKL range,
        using the calculator's current (live) state.

        Independent of any displayed 2D plane -- this is a deliberate, new
        calculation the user explicitly requested via Generate, unlike
        ``apply_filters_to_snapshot`` which never touches the live
        calculator. Rejects oversized ranges *before* materializing the
        HKL list (a naive generate-then-check would let e.g. a full
        -100..100 cube on all three axes build an 8-million-tuple list
        before ever checking the limit). Excludes (0, 0, 0) -- this is an
        explicit "give me a Bragg-peak list" action, distinct from
        mirroring a plotted plane.

        Returns:
            dict with ``success`` (bool) and, on success, ``reflections``
            (list of ``Reflection``), ``generated_count``, and
            ``filtered_count``.
        """
        if not self.calculator.is_initialized:
            return {
                "success": False,
                "error": "The structure factor calculator is not yet initialized.\n"
                         "Please initialize it from either subtab first.",
            }

        try:
            count = count_hkl_range(h_range, k_range, l_range, exclude_origin=True)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        if count > MAX_BULK_REFLECTIONS:
            return {
                "success": False,
                "error": (
                    f"Requested range would generate {count} reflections, "
                    f"which exceeds the limit of {MAX_BULK_REFLECTIONS}. "
                    "Narrow the H/K/L bounds and try again."
                ),
            }

        if count == 0:
            return {"success": True, "reflections": [], "generated_count": 0, "filtered_count": 0}

        hkl_list = generate_hkl_range(h_range, k_range, l_range, exclude_origin=True)

        try:
            f_values = self.calculator.calculate_structure_factors(hkl_list)
        except Exception as e:
            return {"success": False, "error": f"Structure factor calculation failed: {e}"}

        reflections = build_reflections(hkl_list, f_values)
        return self._filter(reflections, count, exclude_extinct, rel_tol, min_intensity, f_000_magnitude=None)

    def apply_filters_to_snapshot(
        self,
        snapshot,
        exclude_extinct: bool = True,
        rel_tol: float = DEFAULT_EXTINCTION_REL_TOL,
        min_intensity: float = None,
    ) -> dict:
        """Filter a previously captured ``ReflectionSnapshot``.

        Never touches the live calculator -- operates purely on the frozen
        data the snapshot already holds, which is what makes it safe to use
        for "export what's currently plotted": the shared calculator may
        have since been reinitialized (by either subtab) at a different
        energy, and recomputing here would silently disagree with the plot.

        Returns:
            dict with ``success`` (bool) and, on success, ``reflections``
            (list of ``Reflection``), ``generated_count``, and
            ``filtered_count``.
        """
        reflections = list(snapshot.reflections)
        return self._filter(
            reflections, len(reflections), exclude_extinct, rel_tol, min_intensity,
            f_000_magnitude=snapshot.f_000_magnitude,
        )

    def _filter(self, reflections, generated_count, exclude_extinct, rel_tol, min_intensity, f_000_magnitude):
        """Shared extinction/min-intensity filtering for both calculation paths."""
        if exclude_extinct:
            if f_000_magnitude is None:
                try:
                    f_000 = self.calculator.calculate_structure_factors([[0, 0, 0]])[0]
                except Exception as e:
                    return {"success": False, "error": f"Structure factor calculation failed: {e}"}
                f_000_magnitude = abs(f_000)
            reflections = filter_extinct(reflections, f_000_magnitude, rel_tol=rel_tol)

        if min_intensity is not None:
            reflections = filter_min_intensity(reflections, min_intensity)

        return {
            "success": True,
            "reflections": reflections,
            "generated_count": generated_count,
            "filtered_count": len(reflections),
        }

    def export_reflections(self, reflections, metadata: dict, fmt: str, file_path: str) -> dict:
        """Serialize reflections to CSV or JSON and write them to ``file_path``.

        The only place actual file I/O happens for this feature -- the UI
        layer only owns the ``QFileDialog`` call and hands the chosen path
        here.
        """
        if fmt == "csv":
            content = serialize_to_csv(reflections, metadata)
        elif fmt == "json":
            content = serialize_to_json(reflections, metadata)
        else:
            return {"success": False, "error": f"Unknown export format: {fmt!r}"}

        try:
            with open(file_path, "w", newline="") as f:
                f.write(content)
        except OSError as e:
            return {"success": False, "error": str(e)}

        return {"success": True}
