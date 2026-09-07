"""ScatteringGeometryController.invalidate_structure() / ScatteringGeometryTab
.clear(): a structure change must discard results, accumulated history,
unit-cell previews, and the HKL-scan plot -- and re-sync funtional_objects[0]
(used by set_parameters()'s initialize loop) to the freshly-rebound
calculator, not leave it pointing at the discarded one.
"""

import os

import pytest

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io

from tests.conftest import LATTICE_CONFIGS

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "advisor", "resources", "data", "nacl.cif")
)


@pytest.fixture
def controller(qapp):
    ctrl = AppController(qt_app=qapp)
    yield ctrl
    if ctrl.structure_source and ctrl.structure_source.effective_path:
        cif_io.cleanup_snapshot(ctrl.structure_source.effective_path)


@pytest.fixture
def cubic_params():
    return {**LATTICE_CONFIGS["cubic"], "roll": 0.0, "pitch": 0.0, "yaw": 0.0, "energy": 930.0}


def _make_hkl_to_angles_result():
    return {
        "success": True,
        "number_of_solutions": 1,
        "tth": [90.0], "theta": [45.0], "chi": [0.0], "phi": [0.0],
        "feasible": [True],
    }


class TestFunctionalObjectsResync:
    def test_funtional_objects_points_at_the_new_calculator_after_invalidate(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)
        sg = controller.features[0]
        tab = sg.view

        sg.invalidate_structure()

        assert tab.funtional_objects[0] is sg.calculator
        assert tab.calculator is sg.calculator


class TestHistoryClearedOnStructureChange:
    def test_hkl_to_angles_history_cleared(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)
        tab = controller.features[0].view
        tab.hkl_to_angles_results.display_results(_make_hkl_to_angles_result())
        assert len(tab.hkl_to_angles_results.history) == 1

        controller.features[0].invalidate_structure()

        assert tab.hkl_to_angles_results.history == []

    def test_hk_angles_history_cleared(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)
        tab = controller.features[0].view
        tab.hk_angles_results.history.append({"dummy": True})
        assert len(tab.hk_angles_results.history) == 1

        controller.features[0].invalidate_structure()

        assert tab.hk_angles_results.history == []

    def test_history_survives_ordinary_clear_results(self, controller, cubic_params):
        """clear_results() (an ordinary 'clear the displayed table' action,
        not a structure change) must still keep history -- only the new
        clear_history() discards it."""
        controller.apply_parameters(cubic_params)
        tab = controller.features[0].view
        tab.hkl_to_angles_results.display_results(_make_hkl_to_angles_result())

        tab.hkl_to_angles_results.clear_results()

        assert len(tab.hkl_to_angles_results.history) == 1


class TestUnitcellVisualizersReset:
    def test_all_three_unitcell_previews_reset(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        params_with_cif = {**cubic_params, "cif_file": controller.structure_source.effective_path}
        controller.apply_parameters(params_with_cif)
        tab = controller.features[0].view
        assert tab.angles_to_hkl_unitcell_viz.is_initialized is True

        controller.features[0].invalidate_structure()

        assert tab.angles_to_hkl_unitcell_viz.is_initialized is False
        assert tab.hkl_to_angles_unitcell_viz.is_initialized is False
        assert tab.hk_fixed_tth_unitcell_viz.is_initialized is False
        assert tab.angles_to_hkl_unitcell_viz.crystal is None


class TestCalculationsInactiveAfterInvalidate:
    def test_calculator_is_not_initialized_after_invalidate(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)
        sg = controller.features[0]
        assert sg.calculator.is_initialized() is True

        sg.invalidate_structure()

        assert sg.calculator.is_initialized() is False
