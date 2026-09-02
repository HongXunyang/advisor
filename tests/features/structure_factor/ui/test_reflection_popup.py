"""Tests for the Reflection List popup UI."""
import os

import pytest

from PyQt5.QtWidgets import QFileDialog

import advisor
from advisor.features.structure_factor.controllers.structure_factor_controller import (
    StructureFactorController,
)
from advisor.features.structure_factor.domain import Reflection, ReflectionSnapshot
from advisor.features.structure_factor.ui.reflection_popup import (
    ReflectionPopup,
    _RESULTS_TABLE_MAX_HEIGHT,
)

NACL_CIF = os.path.join(
    os.path.dirname(advisor.__file__), "resources", "data", "nacl.cif"
)


class _FakeAppController:
    main_window = None

    def get_parameters(self):
        return {}


@pytest.fixture
def controller(qapp):
    return StructureFactorController(app_controller=_FakeAppController())


@pytest.fixture
def popup(controller):
    p = ReflectionPopup(controller=controller, parent=None)
    # isVisible() reflects on-screen visibility, which requires the
    # top-level window itself to be shown (as it always is via
    # controller.open_reflection_popup() in real usage).
    p.show()
    return p


@pytest.fixture
def initialized_controller(controller):
    controller.calculator.initialize(cif_file_path=NACL_CIF, energy=10000.0)
    return controller


def make_snapshot(reflections, f_000_magnitude=100.0, cif_filename="nacl.cif", energy_kev=10.0):
    return ReflectionSnapshot(
        reflections=tuple(reflections),
        f_000_magnitude=f_000_magnitude,
        cif_filename=cif_filename,
        energy_kev=energy_kev,
        scattering_type="xray dispersion",
    )


class TestUninitializedState:
    def test_bounds_and_generate_disabled(self, popup):
        assert popup.generate_btn.isEnabled() is False
        assert popup.h_min.isEnabled() is False


class TestRefreshAfterInitialize:
    def test_inputs_enabled_after_initialize(self, initialized_controller, popup):
        popup.controller = initialized_controller
        popup.refresh_from_calculator()

        assert popup.not_initialized_label.isVisible() is False
        assert popup.generate_btn.isEnabled() is True


class TestLoadSnapshot:
    def test_none_snapshot_shows_nothing_calculated_state(self, popup):
        popup.load_snapshot(None)

        assert popup.results_table.rowCount() == 0
        assert popup.export_csv_btn.isEnabled() is False
        assert "Nothing calculated" in popup.count_label.text()
        assert popup._current_context is None

    def test_populates_table_from_snapshot(self, popup):
        snapshot = make_snapshot([
            Reflection(1, 0, 0, f_real=5.0, f_imag=0.0),
            Reflection(1, 1, 1, f_real=6.0, f_imag=0.0),
        ])

        popup.load_snapshot(snapshot)

        assert popup.results_table.rowCount() == 2
        assert "current plane view" in popup.count_label.text()

    def test_keeps_origin_if_present_in_the_snapshot(self, popup):
        popup.exclude_extinct_checkbox.setChecked(False)
        snapshot = make_snapshot([
            Reflection(0, 0, 0, f_real=100.0, f_imag=0.0),
            Reflection(1, 0, 0, f_real=5.0, f_imag=0.0),
        ])

        popup.load_snapshot(snapshot)

        hkls = {(r.h, r.k, r.l) for r in popup.results_table.reflections()}
        assert (0, 0, 0) in hkls

    def test_never_touches_the_live_calculator(self, popup, monkeypatch):
        calls = []
        monkeypatch.setattr(
            popup.controller.calculator, "calculate_structure_factors",
            lambda *a, **k: calls.append(1) or [],
        )
        snapshot = make_snapshot([Reflection(1, 0, 0, f_real=5.0, f_imag=0.0)])

        popup.load_snapshot(snapshot)

        assert calls == []


class TestBulkGeneration:
    @pytest.fixture
    def initialized_popup(self, initialized_controller, popup):
        popup.controller = initialized_controller
        popup.refresh_from_calculator()
        return popup

    def test_generate_populates_table_and_enables_export(self, initialized_popup):
        for spin, value in (
            (initialized_popup.h_min, -2), (initialized_popup.h_max, 2),
            (initialized_popup.k_min, -2), (initialized_popup.k_max, 2),
            (initialized_popup.l_min, -2), (initialized_popup.l_max, 2),
        ):
            spin.setValue(value)

        initialized_popup._on_generate_bulk()

        assert initialized_popup.results_table.rowCount() > 0
        assert initialized_popup.export_csv_btn.isEnabled() is True
        assert initialized_popup.export_json_btn.isEnabled() is True
        assert "requested range" in initialized_popup.count_label.text()

    def test_table_default_sorted_by_intensity_descending(self, initialized_popup):
        for spin, value in (
            (initialized_popup.h_min, -2), (initialized_popup.h_max, 2),
            (initialized_popup.k_min, -2), (initialized_popup.k_max, 2),
            (initialized_popup.l_min, -2), (initialized_popup.l_max, 2),
        ):
            spin.setValue(value)

        initialized_popup._on_generate_bulk()

        reflections = initialized_popup.results_table.reflections()
        intensities = [r.intensity for r in reflections]
        assert intensities == sorted(intensities, reverse=True)

    def test_invalid_bounds_shows_warning_not_crash(self, initialized_popup, message_box_calls):
        initialized_popup.h_min.setValue(5)
        initialized_popup.h_max.setValue(0)

        initialized_popup._on_generate_bulk()

        assert len(message_box_calls.warnings) == 1


class TestExportMetadataMatchesDisplayedRows:
    """Regression tests for I1: export metadata must describe what actually
    produced the currently-displayed rows, never live widget state that may
    have changed since generation."""

    def test_metadata_reflects_filters_active_at_generation_time_not_current_checkbox_state(
        self, popup, tmp_path, monkeypatch, message_box_calls
    ):
        snapshot = make_snapshot(
            [Reflection(1, 0, 0, f_real=1e-10, f_imag=0.0), Reflection(1, 1, 1, f_real=50.0, f_imag=0.0)],
            f_000_magnitude=100.0,
        )
        popup.controller.calculator.initialize(NACL_CIF, 10000.0)
        popup.exclude_extinct_checkbox.setChecked(True)
        popup.load_snapshot(snapshot)
        assert popup.results_table.rowCount() == 1  # the extinct one was filtered out

        # Now flip the checkbox WITHOUT regenerating.
        popup.exclude_extinct_checkbox.setChecked(False)

        captured = {}
        def fake_export(reflections, metadata, fmt, file_path):
            captured["metadata"] = metadata
            captured["reflections"] = reflections
            return {"success": True}
        monkeypatch.setattr(popup.controller, "export_reflections", fake_export)
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (str(tmp_path / "out.csv"), None)),
        )

        popup._on_export("csv")

        # Metadata must say extinction filtering WAS applied (matches the
        # actual rows), even though the checkbox is now unchecked.
        assert captured["metadata"]["extinction_rel_tol"] is not None
        assert len(captured["reflections"]) == 1

    def test_generated_count_is_populated_not_hardcoded_none(
        self, popup, tmp_path, monkeypatch, message_box_calls
    ):
        snapshot = make_snapshot([Reflection(1, 0, 0, f_real=5.0, f_imag=0.0)])
        popup.controller.calculator.initialize(NACL_CIF, 10000.0)
        popup.load_snapshot(snapshot)

        captured = {}
        monkeypatch.setattr(
            popup.controller, "export_reflections",
            lambda reflections, metadata, fmt, file_path: captured.update(metadata=metadata) or {"success": True},
        )
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (str(tmp_path / "out.csv"), None)),
        )

        popup._on_export("csv")

        assert captured["metadata"]["generated_count"] == 1

    def test_bulk_range_recorded_in_metadata(self, popup, tmp_path, monkeypatch, message_box_calls):
        popup.controller.calculator.initialize(NACL_CIF, 10000.0)
        popup.refresh_from_calculator()
        for spin, value in (
            (popup.h_min, -1), (popup.h_max, 1),
            (popup.k_min, 0), (popup.k_max, 0),
            (popup.l_min, 0), (popup.l_max, 0),
        ):
            spin.setValue(value)
        popup._on_generate_bulk()

        captured = {}
        monkeypatch.setattr(
            popup.controller, "export_reflections",
            lambda reflections, metadata, fmt, file_path: captured.update(metadata=metadata) or {"success": True},
        )
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (str(tmp_path / "out.csv"), None)),
        )

        popup._on_export("csv")

        assert captured["metadata"]["h_range"] == [-1, 1]
        assert captured["metadata"]["source"] == "the requested range"


class TestExportExtensionCaseInsensitive:
    def test_uppercase_extension_not_doubled(self, popup, tmp_path, monkeypatch, message_box_calls):
        snapshot = make_snapshot([Reflection(1, 0, 0, f_real=5.0, f_imag=0.0)])
        popup.controller.calculator.initialize(NACL_CIF, 10000.0)
        popup.load_snapshot(snapshot)

        captured = {}
        def fake_export(reflections, metadata, fmt, file_path):
            captured["file_path"] = file_path
            return {"success": True}
        monkeypatch.setattr(popup.controller, "export_reflections", fake_export)
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *a, **k: (str(tmp_path / "results.CSV"), None)),
        )

        popup._on_export("csv")

        assert not captured["file_path"].endswith(".CSV.csv")


class TestResultsTableCompactness:
    def test_table_has_bounded_height_so_it_scrolls_instead_of_growing(self, popup):
        assert popup.results_table.maximumHeight() == _RESULTS_TABLE_MAX_HEIGHT

    def test_many_rows_still_fit_within_bounded_height(self, popup):
        snapshot = make_snapshot([Reflection(h, 0, 0, f_real=5.0, f_imag=0.0) for h in range(-20, 21)])

        popup.load_snapshot(snapshot)

        assert popup.results_table.rowCount() > 0
        assert popup.results_table.height() <= _RESULTS_TABLE_MAX_HEIGHT


class TestPopupReuse:
    def test_open_reflection_popup_reuses_instance(self, controller, qapp):
        controller.open_reflection_popup()
        first = controller._reflection_popup
        controller.open_reflection_popup()
        second = controller._reflection_popup
        assert first is second

    def test_closing_popup_does_not_destroy_it(self, controller, qapp):
        controller.open_reflection_popup()
        popup_instance = controller._reflection_popup
        popup_instance.close()
        # Default Qt behavior (no WA_DeleteOnClose) is to hide, not destroy --
        # the Python object and its state must still be usable afterwards.
        assert popup_instance.isVisible() is False
        controller.open_reflection_popup()
        assert controller._reflection_popup is popup_instance

    def test_open_with_default_snapshot_populates_table(self, initialized_controller, qapp):
        snapshot = make_snapshot([Reflection(1, 0, 0, f_real=5.0, f_imag=0.0)])
        initialized_controller.open_reflection_popup(default_snapshot=snapshot)
        assert initialized_controller._reflection_popup.results_table.rowCount() > 0
