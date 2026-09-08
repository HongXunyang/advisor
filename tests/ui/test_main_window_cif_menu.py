"""File > Open CIF… and the Change Structure action must route through the
same shared importer as drag-and-drop/Browse -- previously "File > Open" was
a genuine no-op (delegated to a stub TabInterface.open_file() that always
returned False and was never overridden).
"""

import os

from PyQt5.QtWidgets import QFileDialog, QToolBar

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io

NACL_CIF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "advisor", "resources", "data", "nacl.cif")
)


def _cleanup(controller):
    if controller.structure_source and controller.structure_source.effective_path:
        cif_io.cleanup_snapshot(controller.structure_source.effective_path)


class TestOpenCifMenuAction:
    def test_open_cif_calls_controller_import_cif(self, qapp, monkeypatch):
        controller = AppController(qt_app=qapp)
        try:
            monkeypatch.setattr(
                QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (NACL_CIF, ""))
            )
            controller.main_window._open_cif()

            assert controller.structure_source is not None
            assert controller.structure_source.capabilities.structure_factor_ok is True
        finally:
            _cleanup(controller)

    def test_open_cif_shows_library_note_via_structure_summary(self, qapp, monkeypatch):
        """REVIEW.md finding #6: File > Open CIF must not be a route where
        "Added to My structures"/"could not save" is invisible -- it's
        surfaced centrally by AppController.on_structure_changed(), reached
        from every accept entry point, not only the setup screen's own
        drop/Browse handler."""
        controller = AppController(qt_app=qapp)
        try:
            monkeypatch.setattr(
                QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (NACL_CIF, ""))
            )
            controller.main_window._open_cif()

            note = controller.init_window._structure_summary._library_note_label.text()
            assert note == "Added to My structures."
        finally:
            _cleanup(controller)

    def test_cancelling_the_dialog_does_nothing(self, qapp, monkeypatch):
        controller = AppController(qt_app=qapp)
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", ""))
        )
        controller.main_window._open_cif()
        assert controller.structure_source is None

    def test_rejected_cif_shows_status_message_not_a_dialog(self, qapp, monkeypatch):
        controller = AppController(qt_app=qapp)
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("/does/not/exist.cif", ""))
        )
        controller.main_window._open_cif()
        assert controller.structure_source is None
        message = controller.main_window.statusBar().currentMessage()
        assert message != ""
        assert "not found" in message.lower()


class TestChangeStructureDialogAction:
    def test_opens_a_dialog_wrapping_the_shared_drop_target(self, qapp, monkeypatch):
        from advisor.ui.dialogs.change_structure_dialog import ChangeStructureDialog

        controller = AppController(qt_app=qapp)
        opened = {}

        def fake_exec(self):
            opened["called"] = True
            return 0

        monkeypatch.setattr(ChangeStructureDialog, "exec_", fake_exec)
        controller.main_window._open_change_structure_dialog()

        assert opened.get("called") is True

    def test_accepting_a_cif_shows_library_note_via_structure_summary(self, qapp):
        """REVIEW.md finding #6: the Change Structure dialog closes
        immediately on a successful accept, showing only the scientific
        `result.message` -- but the setup screen's structure summary (shown
        again once the dialog closes) must still reflect the library note,
        via the same centralized `on_structure_changed()` path File>Open
        uses."""
        from advisor.ui.dialogs.change_structure_dialog import ChangeStructureDialog

        controller = AppController(qt_app=qapp)
        try:
            dialog = ChangeStructureDialog(controller)
            dialog._drop_target.cifSelected.emit(NACL_CIF)

            note = controller.init_window._structure_summary._library_note_label.text()
            assert note == "Added to My structures."
        finally:
            _cleanup(controller)


class TestLibraryPickerAction:
    def test_opens_the_library_picker_dialog(self, qapp, monkeypatch):
        from advisor.ui.dialogs.library_picker_dialog import LibraryPickerDialog

        controller = AppController(qt_app=qapp)
        opened = {}

        def fake_exec(self):
            opened["called"] = True
            return 0

        monkeypatch.setattr(LibraryPickerDialog, "exec_", fake_exec)
        controller.main_window._open_library_picker()

        assert opened.get("called") is True

    def test_toolbar_and_file_menu_both_expose_it(self, qapp):
        controller = AppController(qt_app=qapp)
        toolbar = controller.main_window.findChild(QToolBar)
        toolbar_texts = [a.text() for a in toolbar.actions()]
        assert "My structures…" in toolbar_texts

        file_menu = controller.main_window.menuBar().actions()[0].menu()
        menu_texts = [a.text() for a in file_menu.actions() if a.text()]
        assert any("structures" in t.lower() for t in menu_texts)


class TestSingleConsolidatedEntryPoint:
    """Regression tests: 'Change Structure…' and 'Reset Parameters' used to
    be two separate toolbar/menu actions with overlapping purpose. Fixed by
    folding the destructive reset into a "Start over" button inside the
    Change Structure dialog -- there is now exactly one toolbar action and
    one relevant File-menu action for managing the structure.
    """

    def test_toolbar_has_no_separate_reset_action(self, qapp):
        controller = AppController(qt_app=qapp)
        toolbar = controller.main_window.findChild(QToolBar)
        texts = [a.text() for a in toolbar.actions()]

        # "My structures…" (REQUIREMENT_2) is a legitimate additional
        # toolbar action, not a reintroduction of the old separate "Reset"
        # action this regression test guards against.
        assert texts == ["Change Structure…", "My structures…"]
        assert not any("Reset" in t for t in texts)

    def test_file_menu_has_no_separate_reset_action(self, qapp):
        controller = AppController(qt_app=qapp)
        file_menu = controller.main_window.menuBar().actions()[0].menu()
        texts = [a.text() for a in file_menu.actions() if a.text()]

        assert not any("Reset" in t for t in texts)
        assert any("Change Structure" in t for t in texts)

    def test_ctrl_r_now_opens_change_structure(self, qapp, monkeypatch):
        from advisor.ui.dialogs.change_structure_dialog import ChangeStructureDialog

        controller = AppController(qt_app=qapp)
        file_menu = controller.main_window.menuBar().actions()[0].menu()
        change_structure_action = next(
            a for a in file_menu.actions() if "Change Structure" in (a.text() or "")
        )

        assert change_structure_action.shortcut().toString() == "Ctrl+R"


class TestChangeStructureDialogStartOver:
    """The dialog's "Start over" button is the sole remaining path to the
    full destructive reset (AppController.reset_parameters())."""

    def test_start_over_calls_reset_parameters_and_closes(self, qapp):
        from advisor.ui.dialogs.change_structure_dialog import ChangeStructureDialog

        controller = AppController(qt_app=qapp)
        try:
            controller.import_cif(NACL_CIF)
            assert controller.structure_source is not None

            dialog = ChangeStructureDialog(controller)
            dialog._on_start_over()

            assert controller.structure_source is None
            assert dialog.result() == ChangeStructureDialog.Accepted
        finally:
            _cleanup(controller)

    def test_scattering_geometry_tab_button_opens_the_dialog(self, qapp, monkeypatch):
        from advisor.ui.dialogs.change_structure_dialog import ChangeStructureDialog

        controller = AppController(qt_app=qapp)
        tab = controller.features[0].view
        opened = {}

        def fake_exec(self):
            opened["called"] = True
            return 0

        monkeypatch.setattr(ChangeStructureDialog, "exec_", fake_exec)
        tab._open_change_structure_dialog()

        assert opened.get("called") is True
