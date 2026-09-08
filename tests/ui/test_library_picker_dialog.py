"""`LibraryPickerDialog`: highlighting/cancelling must never touch the
session; empty/no-results/geometry-only/storage-error states render
actionable copy; star/rename/note edits and Remove work through the real
`AppController`/`LibraryService`.
"""

import os

import pytest
from PyQt5.QtWidgets import QMessageBox

from advisor.controllers.app_controller import AppController
from advisor.domain.cif_import import io as cif_io
from advisor.ui.dialogs.library_picker_dialog import LibraryPickerDialog

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixtures", "cif"))
HIGH_PRECISION_CIF = os.path.join(FIXTURE_DIR, "high_precision.cif")
CELL_ONLY_CIF = os.path.join(FIXTURE_DIR, "cell_only.cif")


@pytest.fixture
def controller(qapp, tmp_path):
    ctrl = AppController(qt_app=qapp, library_root=str(tmp_path / "lib"))
    yield ctrl
    if ctrl.structure_source and ctrl.structure_source.effective_path:
        cif_io.cleanup_snapshot(ctrl.structure_source.effective_path)


def test_empty_library_shows_actionable_empty_state(qapp, controller):
    dialog = LibraryPickerDialog(controller)
    assert dialog._list_widget.isHidden() is True
    assert dialog._empty_label.isHidden() is False
    assert "Try an example" in dialog._empty_label.text()


def test_populated_library_shows_rows_recent_first(qapp, controller):
    controller.import_cif(HIGH_PRECISION_CIF)
    dialog = LibraryPickerDialog(controller)
    assert dialog._list_widget.count() == 1


def test_list_never_allows_horizontal_scrolling(qapp, controller):
    """REVIEW.md finding #7: a hard guarantee on top of LibraryRowWidget's
    own text eliding -- even a pathologically long display name must not
    make the picker's primary control require horizontal scrolling."""
    from PyQt5.QtCore import Qt

    controller.import_cif(HIGH_PRECISION_CIF)
    record_id = controller.library.list_recent()[0].id
    controller.library.rename(record_id, "x" * 500)

    dialog = LibraryPickerDialog(controller)
    assert dialog._list_widget.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    dialog.resize(560, 460)
    dialog.show()
    qapp.processEvents()
    assert dialog._list_widget.horizontalScrollBar().maximum() == 0


def test_no_search_results_offers_clear_search(qapp, controller):
    controller.import_cif(HIGH_PRECISION_CIF)
    dialog = LibraryPickerDialog(controller)
    dialog._search_edit.setText("no-such-structure-anywhere")
    assert dialog._list_widget.isHidden() is True
    assert dialog._clear_search_btn.isHidden() is False

    dialog._clear_search_btn.click()
    assert dialog._search_edit.text() == ""
    assert dialog._list_widget.isHidden() is False


def test_geometry_only_row_offers_use_for_geometry_wording(qapp, controller):
    controller.import_cif(CELL_ONLY_CIF)
    dialog = LibraryPickerDialog(controller)
    item = dialog._list_widget.item(0)
    dialog._list_widget.setCurrentItem(item)
    assert dialog._use_button.text() == "Use for geometry"


def test_highlighting_a_row_never_touches_app_controller(qapp, controller):
    controller.import_cif(HIGH_PRECISION_CIF)
    source_before = controller.structure_source
    dialog = LibraryPickerDialog(controller)

    item = dialog._list_widget.item(0)
    dialog._list_widget.setCurrentItem(item)

    assert controller.structure_source is source_before


def test_cancelling_dialog_leaves_current_setup_untouched(qapp, controller):
    controller.import_cif(HIGH_PRECISION_CIF)
    source_before = controller.structure_source
    dialog = LibraryPickerDialog(controller)
    dialog._list_widget.setCurrentItem(dialog._list_widget.item(0))

    dialog.reject()

    assert controller.structure_source is source_before


def test_switching_filters_and_searching_does_not_touch_session(qapp, controller):
    controller.import_cif(HIGH_PRECISION_CIF)
    source_before = controller.structure_source
    dialog = LibraryPickerDialog(controller)

    dialog._starred_btn.click()
    dialog._all_btn.click()
    dialog._search_edit.setText("silicon")
    dialog._search_edit.setText("")

    assert controller.structure_source is source_before


def test_use_structure_applies_through_app_controller(qapp, controller):
    controller.import_cif(HIGH_PRECISION_CIF)
    controller.reset_parameters()
    dialog = LibraryPickerDialog(controller)
    dialog._list_widget.setCurrentItem(dialog._list_widget.item(0))

    dialog._on_use_clicked()

    assert controller.structure_source is not None
    assert controller.structure_source.source_kind == "cif"
    assert controller.parameters is None  # accepted, but Initialize was not re-run


def test_star_rename_note_edits_persist(qapp, controller):
    controller.import_cif(HIGH_PRECISION_CIF)
    dialog = LibraryPickerDialog(controller)
    dialog._list_widget.setCurrentItem(dialog._list_widget.item(0))

    dialog._star_checkbox.setChecked(True)
    dialog._name_edit.setText("My silicon")
    dialog._name_edit.editingFinished.emit()
    dialog._note_edit.setText("lab reference")
    dialog._note_edit.editingFinished.emit()

    record = controller.library.list_all()[0]
    assert record.starred is True
    assert record.display_name == "My silicon"
    assert record.note == "lab reference"


def test_remove_from_library_confirms_then_removes(qapp, controller, monkeypatch):
    controller.import_cif(HIGH_PRECISION_CIF)
    record_id = controller.library.list_recent()[0].id
    source_before = controller.structure_source

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))

    dialog = LibraryPickerDialog(controller)
    dialog._list_widget.setCurrentItem(dialog._list_widget.item(0))
    dialog._on_remove_clicked()

    assert controller.library.get(record_id) is None
    assert controller.structure_source is source_before  # active session untouched


def test_remove_declined_keeps_record(qapp, controller, monkeypatch):
    controller.import_cif(HIGH_PRECISION_CIF)
    record_id = controller.library.list_recent()[0].id

    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))

    dialog = LibraryPickerDialog(controller)
    dialog._list_widget.setCurrentItem(dialog._list_widget.item(0))
    dialog._on_remove_clicked()

    assert controller.library.get(record_id) is not None


def test_remember_checkbox_reflects_and_updates_preference(qapp, controller):
    dialog = LibraryPickerDialog(controller)
    assert dialog._remember_checkbox.isChecked() is True

    dialog._remember_checkbox.setChecked(False)
    assert controller.library.remember_enabled() is False
