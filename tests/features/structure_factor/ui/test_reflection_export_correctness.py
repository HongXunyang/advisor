"""Regression tests for the C1 finding: exported/plotted reflection values
must never silently disagree because the shared, mutable
StructureFactorCalculator was reinitialized (by either subtab) at a
different energy after a plane was drawn.

These directly reproduce the review's repro steps against the real widgets,
a real StructureFactorCalculator, and the bundled nacl.cif.
"""
import os

import pytest

import advisor
from advisor.features.structure_factor.controllers.structure_factor_controller import (
    StructureFactorController,
)
from tests.conftest import LATTICE_CONFIGS

NACL_CIF = os.path.join(
    os.path.dirname(advisor.__file__), "resources", "data", "nacl.cif"
)


class _FakeAppController:
    main_window = None

    def get_parameters(self):
        return {"cif_file": NACL_CIF}


@pytest.fixture
def controller(qapp):
    c = StructureFactorController(app_controller=_FakeAppController())
    # Global lattice params, so the Customized-plane subtab's accessibility
    # check (triggered automatically by initialize_calculator_customized)
    # succeeds instead of hitting a blocking QMessageBox.warning().
    c.set_parameters({**LATTICE_CONFIGS["cubic"], "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0})
    return c


class TestHklPlaneSnapshotIsImmuneToLaterReinitialization:
    def test_snapshot_values_unchanged_after_calculator_reinitialized_at_new_energy(self, controller):
        tab = controller.view
        tab.hkl_controls.energy_input.energy_ev = 2000.0
        tab.initialize_calculator_hkl()

        snapshot_at_2kev = tab.hkl_plane_2d.get_current_snapshot()
        assert snapshot_at_2kev is not None
        original_values = {(r.h, r.k, r.l): r.f_magnitude for r in snapshot_at_2kev.reflections}
        assert len(original_values) > 0

        # Simulate the OTHER subtab reinitializing the shared calculator at a
        # different energy, without redrawing the HK plot.
        controller.calculator.initialize(NACL_CIF, 15000.0)

        snapshot_again = tab.hkl_plane_2d.get_current_snapshot()
        assert snapshot_again is snapshot_at_2kev  # same frozen object, not recomputed
        replayed_values = {(r.h, r.k, r.l): r.f_magnitude for r in snapshot_again.reflections}
        assert replayed_values == original_values
        assert snapshot_again.energy_kev == 2.0  # not 15.0

    def test_exported_table_matches_snapshot_energy_not_live_calculator_energy(self, controller):
        tab = controller.view
        tab.hkl_controls.energy_input.energy_ev = 2000.0
        tab.initialize_calculator_hkl()

        controller.open_reflection_popup(default_snapshot=tab.hkl_plane_2d.get_current_snapshot())
        popup = controller._reflection_popup

        # Reinitialize elsewhere at a different energy while the popup is open.
        controller.calculator.initialize(NACL_CIF, 15000.0)

        assert popup._current_context.energy_kev == 2.0


class TestCustomizedPlaneSnapshotIsImmuneToLaterReinitialization:
    def test_snapshot_values_unchanged_after_calculator_reinitialized_at_new_energy(self, controller):
        tab = controller.view
        controls = tab.customized_plane_widget.get_controls()
        controls.energy_input.energy_ev = 2000.0
        tab.initialize_calculator_customized()

        snapshot_at_2kev = tab.customized_plane_widget.get_current_snapshot()
        assert snapshot_at_2kev is not None
        original_values = {(r.h, r.k, r.l): r.f_magnitude for r in snapshot_at_2kev.reflections}

        controller.calculator.initialize(NACL_CIF, 15000.0)

        snapshot_again = tab.customized_plane_widget.get_current_snapshot()
        assert snapshot_again is snapshot_at_2kev
        replayed_values = {(r.h, r.k, r.l): r.f_magnitude for r in snapshot_again.reflections}
        assert replayed_values == original_values
        assert snapshot_again.energy_kev == 2.0


class TestCrossSubtabInitializationOrder:
    def test_hkl_snapshot_unaffected_by_later_customized_plane_initialization(self, controller):
        tab = controller.view
        tab.hkl_controls.energy_input.energy_ev = 2000.0
        tab.initialize_calculator_hkl()
        hkl_snapshot = tab.hkl_plane_2d.get_current_snapshot()
        hkl_values = {(r.h, r.k, r.l): r.f_magnitude for r in hkl_snapshot.reflections}

        controls = tab.customized_plane_widget.get_controls()
        controls.energy_input.energy_ev = 15000.0
        tab.initialize_calculator_customized()

        replayed = tab.hkl_plane_2d.get_current_snapshot()
        assert {(r.h, r.k, r.l): r.f_magnitude for r in replayed.reflections} == hkl_values
        assert replayed.energy_kev == 2.0

    def test_customized_snapshot_unaffected_by_later_hkl_plane_initialization(self, controller):
        tab = controller.view
        controls = tab.customized_plane_widget.get_controls()
        controls.energy_input.energy_ev = 2000.0
        tab.initialize_calculator_customized()
        custom_snapshot = tab.customized_plane_widget.get_current_snapshot()
        custom_values = {(r.h, r.k, r.l): r.f_magnitude for r in custom_snapshot.reflections}

        tab.hkl_controls.energy_input.energy_ev = 15000.0
        tab.initialize_calculator_hkl()

        replayed = tab.customized_plane_widget.get_current_snapshot()
        assert {(r.h, r.k, r.l): r.f_magnitude for r in replayed.reflections} == custom_values
        assert replayed.energy_kev == 2.0


class TestExportFromUncalculatedSubtab:
    def test_customized_plane_snapshot_is_none_when_only_hkl_plane_initialized(self, controller):
        tab = controller.view
        tab.initialize_calculator_hkl()

        assert tab.customized_plane_widget.get_current_snapshot() is None

    def test_popup_shows_nothing_calculated_state_for_a_none_snapshot(self, controller):
        tab = controller.view
        tab.initialize_calculator_hkl()

        controller.open_reflection_popup(
            default_snapshot=tab.customized_plane_widget.get_current_snapshot()
        )
        popup = controller._reflection_popup

        assert popup.results_table.rowCount() == 0
        assert popup.export_csv_btn.isEnabled() is False
        assert "Nothing calculated" in popup.count_label.text()


class TestGlobalParameterChangeInvalidatesSnapshots:
    def test_clear_plots_invalidates_snapshot(self, controller):
        tab = controller.view
        tab.initialize_calculator_hkl()
        assert tab.hkl_plane_2d.get_current_snapshot() is not None

        tab.clear()

        assert tab.hkl_plane_2d.get_current_snapshot() is None
        assert tab.customized_plane_widget.get_current_snapshot() is None
