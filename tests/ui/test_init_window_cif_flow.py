"""End-to-end CIF import through the real InitWindow + AppController wiring:
Browse/drop -> AppController.import_cif -> on_structure_changed. Previously
InitWindow.browse_cif_file()/on_cif_file_changed() had zero test coverage
(only the UB-session side effect of calling apply_cif_parameters() with
hardcoded numbers was tested) -- this exercises the real CIF-parsing path.
"""

import os

from PyQt5.QtWidgets import QDialog, QFileDialog

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io
from advisor.ui.dialogs.diffraction_test_dialog import DiffractionTestDialog

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "advisor", "resources", "data", "nacl.cif")
)
CELL_ONLY_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif", "cell_only.cif")
)
MALFORMED_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif", "malformed.cif")
)
HIGH_PRECISION_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif", "high_precision.cif")
)


def _cleanup(controller):
    if controller.structure_source and controller.structure_source.effective_path:
        cif_io.cleanup_snapshot(controller.structure_source.effective_path)


class TestDropSelectionAppliesFullPrecisionCell:
    def test_valid_cif_locks_inputs_and_shows_ready_status(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(NACL_CIF)

            assert window.a_input.value() == 2.86
            assert window.alpha_input.value() == 90.0
            assert window.a_input.isEnabled() is False
            assert window._structure_summary.current_source() is not None
            assert "Ready for geometry and structure factors." in window._structure_summary._status_label.text()
            assert controller.structure_source.source_kind == "cif"
        finally:
            _cleanup(controller)

    def test_geometry_only_cif_keeps_geometry_usable(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(CELL_ONLY_CIF)

            assert window.a_input.isEnabled() is False
            assert controller.structure_source.capabilities.geometry_ok is True
            assert controller.structure_source.capabilities.structure_factor_ok is False
            assert "prevents structure-factor" in window._structure_summary._status_label.text()
        finally:
            _cleanup(controller)


class TestRejectedSelectionPreservesState:
    def test_malformed_cif_leaves_previous_structure_and_lock_state(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(NACL_CIF)
            a_before = window.a_input.value()

            window._cif_drop_target.cifSelected.emit(MALFORMED_CIF)

            assert window.a_input.value() == a_before
            assert window.a_input.isEnabled() is False
            assert "missing required cell parameters" in window._structure_summary._status_label.text()
        finally:
            _cleanup(controller)

    def test_missing_file_before_any_structure_leaves_manual_inputs_editable(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window

        window._cif_drop_target.cifSelected.emit("/does/not/exist.cif")

        assert window.a_input.isEnabled() is True
        assert controller.structure_source is None


class TestChangeStructureWithoutReset:
    def test_switching_cif_does_not_require_reset(self, qapp, tmp_path):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(NACL_CIF)
            first_source = controller.structure_source

            copy_path = tmp_path / "cell_only_copy.cif"
            with open(CELL_ONLY_CIF, "rb") as fh:
                copy_path.write_bytes(fh.read())

            window._cif_drop_target.cifSelected.emit(str(copy_path))

            assert controller.structure_source is not first_source
            assert controller.structure_source.capabilities.structure_factor_ok is False
        finally:
            _cleanup(controller)


class TestUseManualLatticeAndRemove:
    def test_use_manual_lattice_keeps_cell_values_editable(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(NACL_CIF)
            assert window.a_input.isEnabled() is False

            window._on_use_manual_lattice_clicked()

            assert window.a_input.isEnabled() is True
            assert window.a_input.value() == 2.86
            assert controller.structure_source.source_kind == "manual"
            assert controller.structure_source.capabilities.structure_factor_ok is False
        finally:
            _cleanup(controller)

    def test_remove_cif_unlocks_inputs_and_clears_summary(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        window._cif_drop_target.cifSelected.emit(NACL_CIF)

        window._on_remove_cif_clicked()

        assert window.a_input.isEnabled() is True
        assert controller.structure_source is None
        assert window._structure_summary.current_source() is None


class TestBrowseUsesSameImporter:
    def test_browse_click_routes_through_cif_selected(self, qapp, monkeypatch):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            monkeypatch.setattr(
                QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (NACL_CIF, ""))
            )
            window._cif_drop_target._on_browse_clicked()

            assert controller.structure_source is not None
            assert controller.structure_source.display_path == NACL_CIF
        finally:
            _cleanup(controller)


class TestGeometryOnlyPreviewShowsNoFabricatedAtoms:
    """Regression test: a geometry-only structure (valid cell,
    capabilities.geometry_ok=True, structure_factor_ok=False) previously
    still triggered a full unit-cell preview render, because
    on_structure_changed() gated on geometry_ok. Dans_Diffraction.Crystal()
    silently fabricates a default synthetic atom when no real atom data is
    present, so the preview would show an atom position that isn't actually
    in the CIF. Fixed to gate on structure_factor_ok instead.
    """

    def test_cell_only_cif_does_not_initialize_the_unitcell_preview(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(CELL_ONLY_CIF)

            assert window.unitcell_visualizer.is_initialized is False
            assert window.unitcell_visualizer.crystal is None
        finally:
            _cleanup(controller)

    def test_full_structure_still_shows_the_preview(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(NACL_CIF)

            assert window.unitcell_visualizer.is_initialized is True
        finally:
            _cleanup(controller)


class TestFileFieldNeverShowsCandidateAsIfAccepted:
    """Regression test: CifDropTarget's own line-edit used to persist
    whatever path was last dropped/browsed, including a subsequently
    rejected one -- so after loading NaCl then attempting (and having
    rejected) a malformed file, the field showed the malformed path next to
    a structure summary still correctly showing NaCl as accepted. Fixed by
    having the drop target never display candidate text at all; only
    CifStructureSummary reflects accepted state.
    """

    def test_rejected_selection_does_not_appear_in_the_drop_target(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(NACL_CIF)
            window._cif_drop_target.cifSelected.emit(MALFORMED_CIF)

            assert window._cif_drop_target._display.text() == ""
            assert controller.structure_source.display_path == NACL_CIF
            assert window._structure_summary.current_source().display_path == NACL_CIF
        finally:
            _cleanup(controller)

    def test_accepted_selection_also_does_not_linger_in_the_drop_target(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(NACL_CIF)
            assert window._cif_drop_target._display.text() == ""
        finally:
            _cleanup(controller)


class TestUBPrecisionThroughDialogBoundary:
    """Regression test: HighPrecisionSpinBox only controls *displayed*
    text -- setValue() still rounds the internally stored value to
    decimals() (6, for the lattice fields). Global Initialize was fixed to
    read structure_source directly, but open_diffraction_test_dialog() and
    _current_ub_data()'s staleness check still read the (rounded) widgets.
    Fixed via a single _effective_lattice_params() helper used everywhere.
    """

    def test_widget_itself_is_rounded_relative_to_the_source(self, qapp):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(HIGH_PRECISION_CIF)
            assert controller.structure_source.a == 5.431020511
            assert window.a_input.value() != 5.431020511
            assert round(window.a_input.value(), 6) == 5.431021
        finally:
            _cleanup(controller)

    def test_diffraction_dialog_receives_full_precision_lattice(self, qapp, monkeypatch):
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(HIGH_PRECISION_CIF)

            captured = {}

            def fake_exec(self):
                captured["lattice_params"] = dict(self.lattice_params)
                return QDialog.Rejected

            monkeypatch.setattr(DiffractionTestDialog, "exec_", fake_exec)
            window.open_diffraction_test_dialog()

            assert captured["lattice_params"]["a"] == 5.431020511
        finally:
            _cleanup(controller)

    def test_current_ub_data_staleness_check_uses_full_precision_too(self, qapp):
        """_current_ub_data() compares result.lattice_params against the
        *current* effective lattice -- both sides must use the same
        (full-precision) source or a still-valid applied fit would look
        spuriously stale."""
        controller = AppController(qt_app=qapp)
        window = controller.init_window
        try:
            window._cif_drop_target.cifSelected.emit(HIGH_PRECISION_CIF)
            assert window._effective_lattice_params()["a"] == 5.431020511
        finally:
            _cleanup(controller)
