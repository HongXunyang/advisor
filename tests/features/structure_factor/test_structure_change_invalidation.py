"""StructureFactorController.invalidate_structure() / ReflectionPopup.reset()
/ the capability-gated Initialize short-circuit: a structure change must
discard the live calculators, hide and clear any open reflection popup
(previously never torn down by anything -- AppController.reset_parameters()
didn't even know feature controllers existed), and a geometry-only structure
must fail Initialize with the *specific* reason rather than attempting a
doomed calculation against a silently-defaulted crystal.
"""

import os

import pytest

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io

from tests.conftest import LATTICE_CONFIGS

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "advisor", "resources", "data", "nacl.cif")
)
CELL_ONLY_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "cif", "cell_only.cif")
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


class TestCustomizedPlaneCalculatorRebinding:
    """Regression test: invalidate_structure() previously only rebound
    StructureFactorTab.calculator (`self.view.calculator = self.calculator`),
    not CustomizedPlaneWidget's own independently-held reference (received
    once via set_calculator() at tab-construction time) -- so the
    Customized Plane subtab silently kept referencing a discarded,
    never-initialized calculator after ANY invalidate_structure() call,
    including the very first CIF import (AppController.import_cif() already
    invalidates every feature before Initialize, even in a brand-new
    session).
    """

    def test_customized_plane_widget_calculator_matches_controller_after_first_import(self, controller):
        controller.import_cif(NACL_CIF)
        sf = controller.features[1]
        tab = sf.view

        assert tab.customized_plane_widget.calculator is sf.calculator
        assert tab.calculator is sf.calculator

    def test_customized_plane_initialize_actually_populates_a_snapshot(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        params = {**cubic_params, "cif_file": controller.structure_source.effective_path}
        controller.apply_parameters(params)
        tab = controller.features[1].view

        tab.initialize_calculator_customized()

        assert tab.customized_plane_widget.calculator.is_initialized is True
        assert tab.customized_plane_widget.get_current_snapshot() is not None

    def test_rebinding_still_correct_after_a_replacement(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        params = {**cubic_params, "cif_file": controller.structure_source.effective_path}
        controller.apply_parameters(params)
        controller.remove_structure()
        controller.import_cif(NACL_CIF)
        sf = controller.features[1]
        tab = sf.view

        assert tab.customized_plane_widget.calculator is sf.calculator


class TestReflectionPopupTornDownOnInvalidate:
    def test_open_popup_is_hidden_and_cleared_on_reset(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        params = {**cubic_params, "cif_file": controller.structure_source.effective_path}
        controller.apply_parameters(params)

        sf = controller.features[1]
        sf.calculator.initialize(controller.structure_source.effective_path, 8000.0)
        sf.open_reflection_popup()
        popup = sf._reflection_popup
        assert popup.isVisible() is True

        controller.reset_parameters()

        assert popup.isVisible() is False
        assert popup._current_context is None
        assert popup.export_csv_btn.isEnabled() is False
        assert popup.export_json_btn.isEnabled() is False

    def test_popup_not_yet_opened_does_not_raise_on_invalidate(self, controller, cubic_params):
        controller.apply_parameters(cubic_params)
        controller.features[1].invalidate_structure()  # must not raise


class TestCalculatorsAreFreshAfterInvalidate:
    def test_fresh_calculator_and_brillouin_calculator(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        params = {**cubic_params, "cif_file": controller.structure_source.effective_path}
        controller.apply_parameters(params)
        sf = controller.features[1]
        sf.calculator.initialize(controller.structure_source.effective_path, 8000.0)
        calc_before = sf.calculator
        brillouin_before = sf.brillouin_calculator

        sf.invalidate_structure()

        assert sf.calculator is not calc_before
        assert sf.calculator.is_initialized is False
        assert sf.brillouin_calculator is not brillouin_before


class TestCapabilityGatedInitialize:
    def test_geometry_only_structure_blocks_hkl_initialize_with_specific_reason(self, controller):
        controller.import_cif(CELL_ONLY_CIF)
        tab = controller.features[1].view

        message = tab._capability_block_message()

        assert message != ""
        assert "prevents structure-factor" in message

    def test_full_structure_does_not_block_initialize(self, controller):
        controller.import_cif(NACL_CIF)
        tab = controller.features[1].view

        assert tab._capability_block_message() == ""

    def test_manual_lattice_blocks_initialize(self, controller):
        controller.use_manual_lattice(5.0, 5.0, 5.0, 90.0, 90.0, 90.0)
        tab = controller.features[1].view

        assert tab._capability_block_message() != ""


class TestClearResetsStatusLabels:
    def test_status_labels_reset_after_invalidate(self, controller, cubic_params):
        controller.import_cif(NACL_CIF)
        params = {**cubic_params, "cif_file": controller.structure_source.effective_path}
        controller.apply_parameters(params)
        tab = controller.features[1].view
        tab.hkl_controls.set_status("Calculator initialized successfully", "green")

        controller.features[1].invalidate_structure()

        assert "Not initialized" in tab.hkl_controls.status_label.text()
