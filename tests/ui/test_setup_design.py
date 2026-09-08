"""Rendered setup/picker regressions: compact sizing and accepted preview state."""

from pathlib import Path

import pytest
from PyQt5.QtCore import QPoint

from advisor.app import load_stylesheet
from advisor.controllers.app_controller import AppController
from advisor.ui.dialogs.library_picker_dialog import LibraryPickerDialog


@pytest.fixture
def styled_controller(qapp, tmp_path):
    previous = qapp.styleSheet()
    qapp.setStyleSheet(load_stylesheet())
    controller = AppController(qt_app=qapp, library_root=str(tmp_path / "library"))
    yield controller
    controller._cleanup_on_shutdown()
    controller.main_window.close()
    qapp.setStyleSheet(previous)


def test_setup_fits_compact_shell_and_preview_tracks_accepted_source(qapp, styled_controller):
    controller = styled_controller
    shell, setup = controller.main_window, controller.init_window
    shell.resize(1100, 700)
    shell.show()
    qapp.processEvents()
    assert shell.width() == 1100
    assert shell.height() == 700
    assert setup._atomic_preview_stack.currentWidget() is setup._atomic_empty_label

    controller.load_bundled_example("idealized_rock_salt")
    qapp.processEvents()
    assert setup._atomic_preview_stack.currentWidget() is setup.unitcell_visualizer
    assert setup.unitcell_visualizer.render_error_message is None
    assert setup.a_input.isEnabled() is False

    # A rejected candidate must not hide the accepted atomic preview.
    controller.import_cif(str(Path(__file__).parent / "missing.cif"))
    assert setup._atomic_preview_stack.currentWidget() is setup.unitcell_visualizer

    controller.import_cif(str(Path(__file__).parents[1] / "fixtures/cif/cell_only.cif"))
    qapp.processEvents()
    assert setup._atomic_preview_stack.currentWidget() is setup._atomic_empty_label
    assert setup.unitcell_visualizer.crystal is None
    assert shell.size().width() == 1100
    assert shell.size().height() == 700
    assert setup.rect().contains(setup.initialize_button.mapTo(setup, QPoint(0, 0)))

    controller.remove_structure()
    assert setup.a_input.isEnabled()
    assert setup._atomic_preview_stack.currentWidget() is setup._atomic_empty_label


def test_picker_selection_fits_small_window_without_resizing_or_applying(qapp, styled_controller):
    controller = styled_controller
    controller.load_bundled_example("idealized_rock_salt")
    source = controller.structure_source
    dialog = LibraryPickerDialog(controller)
    dialog.resize(560, 460)
    dialog.show()
    qapp.processEvents()
    initial_size = dialog.size()
    assert dialog._detail_stack.currentIndex() == 0
    dialog._list_widget.setCurrentRow(0)
    qapp.processEvents()
    assert dialog.size() == initial_size
    assert dialog._detail_stack.currentIndex() == 1
    assert controller.structure_source is source
    page = dialog._detail_stack.currentWidget()
    for widget in (dialog._detail_label, dialog._name_edit, dialog._note_edit,
                   dialog._star_checkbox, dialog._details_button, dialog._remove_button):
        origin = widget.mapTo(page, QPoint(0, 0))
        assert page.rect().contains(origin)
        assert page.rect().contains(origin + QPoint(widget.width() - 1, widget.height() - 1))
    row = dialog._list_widget.itemWidget(dialog._list_widget.item(0))
    assert row.property("selected") is True
    dialog._search_edit.setText("no matching structure")
    qapp.processEvents()
    assert dialog._detail_stack.currentIndex() == 0
    assert not dialog._use_button.isEnabled()
    assert dialog.size() == initial_size
    dialog.close()
