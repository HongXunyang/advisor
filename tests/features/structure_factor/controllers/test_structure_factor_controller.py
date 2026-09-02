"""Tests for StructureFactorController wiring and orchestration."""
import os

import pytest

import advisor
from advisor.features.structure_factor.controllers.structure_factor_controller import (
    StructureFactorController,
    MAX_BULK_REFLECTIONS,
)
from advisor.features.structure_factor.domain import (
    StructureFactorCalculator, Reflection, ReflectionSnapshot,
)
from advisor.features.structure_factor.ui.structure_factor_tab import StructureFactorTab
from advisor.features.scattering_geometry.domain import BrillouinCalculator

from tests.conftest import LATTICE_CONFIGS

NACL_CIF = os.path.join(
    os.path.dirname(advisor.__file__), "resources", "data", "nacl.cif"
)


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


@pytest.fixture
def initialized_controller(controller):
    controller.calculator.initialize(cif_file_path=NACL_CIF, energy=10000.0)
    return controller


class TestRunBulkReflectionCalculation:
    def test_uninitialized_calculator_fails(self, controller):
        result = controller.run_bulk_reflection_calculation((0, 1), (0, 1), (0, 1))
        assert result["success"] is False
        assert "not yet initialized" in result["error"]

    def test_generates_and_filters(self, initialized_controller):
        result = initialized_controller.run_bulk_reflection_calculation(
            (-1, 1), (-1, 1), (-1, 1), exclude_extinct=False,
        )
        assert result["success"] is True
        # 3^3 - 1 (origin excluded by default)
        assert result["generated_count"] == 26
        assert result["filtered_count"] == 26
        assert all(isinstance(r, Reflection) for r in result["reflections"])
        assert all((r.h, r.k, r.l) != (0, 0, 0) for r in result["reflections"])

    def test_exclude_extinct_reduces_or_equals_generated_count(self, initialized_controller):
        result = initialized_controller.run_bulk_reflection_calculation(
            (-2, 2), (-2, 2), (-2, 2), exclude_extinct=True,
        )
        assert result["success"] is True
        assert result["filtered_count"] <= result["generated_count"]

    def test_min_intensity_filter_applied_independently(self, initialized_controller):
        without_filter = initialized_controller.run_bulk_reflection_calculation(
            (-2, 2), (-2, 2), (-2, 2), exclude_extinct=False, min_intensity=None,
        )
        with_filter = initialized_controller.run_bulk_reflection_calculation(
            (-2, 2), (-2, 2), (-2, 2), exclude_extinct=False, min_intensity=1e12,
        )
        assert with_filter["filtered_count"] <= without_filter["filtered_count"]
        assert with_filter["reflections"] == []

    def test_invalid_bounds_rejected_without_calling_calculator(self, initialized_controller, monkeypatch):
        calls = []
        monkeypatch.setattr(
            initialized_controller.calculator, "calculate_structure_factors",
            lambda *a, **k: calls.append(1) or [],
        )
        result = initialized_controller.run_bulk_reflection_calculation((5, 0), (0, 0), (0, 0))
        assert result["success"] is False
        assert calls == []

    def test_cap_exceeded_rejected_without_calling_calculator(self, initialized_controller, monkeypatch):
        calls = []
        monkeypatch.setattr(
            initialized_controller.calculator, "calculate_structure_factors",
            lambda *a, **k: calls.append(1) or [],
        )
        big = MAX_BULK_REFLECTIONS  # any range whose volume exceeds this triggers rejection
        result = initialized_controller.run_bulk_reflection_calculation((0, big), (0, 1), (0, 1))
        assert result["success"] is False
        assert str(MAX_BULK_REFLECTIONS) in result["error"]
        assert calls == []

    def test_max_legal_widget_range_rejected_instantly_without_materializing_the_list(
        self, initialized_controller, monkeypatch
    ):
        """The reflection popup's H/K/L spin boxes allow -100..100 on each
        axis (201^3 = 8,120,601 points) -- the cap must be checked from pure
        arithmetic, never by first building that list."""
        import time
        from advisor.features.structure_factor.controllers import (
            structure_factor_controller as controller_module,
        )

        calculator_calls = []
        monkeypatch.setattr(
            initialized_controller.calculator, "calculate_structure_factors",
            lambda *a, **k: calculator_calls.append(1) or [],
        )
        generate_calls = []
        original_generate = controller_module.generate_hkl_range
        def spy_generate(*a, **k):
            generate_calls.append(1)
            return original_generate(*a, **k)
        monkeypatch.setattr(controller_module, "generate_hkl_range", spy_generate)

        start = time.monotonic()
        result = initialized_controller.run_bulk_reflection_calculation(
            (-100, 100), (-100, 100), (-100, 100)
        )
        elapsed = time.monotonic() - start

        assert result["success"] is False
        assert calculator_calls == []
        assert generate_calls == []  # rejected before ever materializing the list
        assert elapsed < 0.5

    def test_does_not_mutate_calculator_energy(self, initialized_controller):
        original_energy = initialized_controller.calculator.energy
        initialized_controller.run_bulk_reflection_calculation((-1, 1), (0, 0), (0, 0))
        assert initialized_controller.calculator.energy == original_energy

    def test_calculator_exception_returns_error_instead_of_propagating(self, initialized_controller, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("Dans_Diffraction blew up")
        monkeypatch.setattr(initialized_controller.calculator, "calculate_structure_factors", boom)

        result = initialized_controller.run_bulk_reflection_calculation((0, 1), (0, 0), (0, 0))

        assert result["success"] is False
        assert "error" in result


class TestApplyFiltersToSnapshot:
    """apply_filters_to_snapshot must never touch the live calculator -- this
    is the fix for the C1 finding (export silently recomputing at whatever
    energy the shared calculator now happens to have)."""

    def _snapshot(self, reflections, f_000_magnitude=100.0):
        return ReflectionSnapshot(
            reflections=tuple(reflections),
            f_000_magnitude=f_000_magnitude,
            cif_filename="nacl.cif",
            energy_kev=10.0,
            scattering_type="xray dispersion",
        )

    def test_never_calls_the_live_calculator(self, initialized_controller, monkeypatch):
        calls = []
        monkeypatch.setattr(
            initialized_controller.calculator, "calculate_structure_factors",
            lambda *a, **k: calls.append(1) or [],
        )
        snapshot = self._snapshot([Reflection(1, 0, 0, f_real=5.0, f_imag=0.0)])

        result = initialized_controller.apply_filters_to_snapshot(snapshot, exclude_extinct=True)

        assert result["success"] is True
        assert calls == []

    def test_filters_using_snapshots_own_f_000_not_a_fresh_calculation(self, initialized_controller):
        snapshot = self._snapshot(
            [
                Reflection(1, 0, 0, f_real=1e-10, f_imag=0.0),  # ~extinct relative to f_000=100
                Reflection(1, 1, 1, f_real=50.0, f_imag=0.0),
            ],
            f_000_magnitude=100.0,
        )

        result = initialized_controller.apply_filters_to_snapshot(snapshot, exclude_extinct=True)

        assert result["success"] is True
        hkls = {(r.h, r.k, r.l) for r in result["reflections"]}
        assert hkls == {(1, 1, 1)}

    def test_min_intensity_filter_applied_independently_of_extinction(self, initialized_controller):
        snapshot = self._snapshot([
            Reflection(1, 0, 0, f_real=1.0, f_imag=0.0),
            Reflection(1, 1, 1, f_real=10.0, f_imag=0.0),
        ])

        result = initialized_controller.apply_filters_to_snapshot(
            snapshot, exclude_extinct=False, min_intensity=50.0
        )

        assert result["success"] is True
        assert {(r.h, r.k, r.l) for r in result["reflections"]} == {(1, 1, 1)}

    def test_generated_and_filtered_counts_reflect_snapshot_size(self, initialized_controller):
        snapshot = self._snapshot([
            Reflection(1, 0, 0, f_real=5.0, f_imag=0.0),
            Reflection(1, 1, 1, f_real=6.0, f_imag=0.0),
        ])

        result = initialized_controller.apply_filters_to_snapshot(snapshot, exclude_extinct=False)

        assert result["generated_count"] == 2
        assert result["filtered_count"] == 2


class TestExportReflections:
    def test_export_csv_writes_file(self, initialized_controller, tmp_path):
        reflections = [Reflection(1, 0, 0, f_real=1.0, f_imag=2.0)]
        file_path = str(tmp_path / "out.csv")
        result = initialized_controller.export_reflections(
            reflections, {"energy_kev": 10.0}, "csv", file_path
        )
        assert result["success"] is True
        content = open(file_path).read()
        assert "h,k,l,f_real,f_imag,f_magnitude,intensity,energy_kev" in content
        assert "1,0,0,1.0,2.0" in content

    def test_export_json_writes_file(self, initialized_controller, tmp_path):
        reflections = [Reflection(1, 0, 0, f_real=1.0, f_imag=2.0)]
        file_path = str(tmp_path / "out.json")
        result = initialized_controller.export_reflections(
            reflections, {"cif_filename": "nacl.cif"}, "json", file_path
        )
        assert result["success"] is True
        import json
        payload = json.loads(open(file_path).read())
        assert payload["metadata"]["cif_filename"] == "nacl.cif"
        assert payload["reflections"][0]["h"] == 1

    def test_unknown_format_fails(self, initialized_controller, tmp_path):
        result = initialized_controller.export_reflections(
            [], {}, "xml", str(tmp_path / "out.xml")
        )
        assert result["success"] is False

    def test_unwritable_path_fails_gracefully(self, initialized_controller, tmp_path):
        # A directory is not a writable file path.
        result = initialized_controller.export_reflections(
            [], {}, "csv", str(tmp_path)
        )
        assert result["success"] is False
        assert "error" in result
