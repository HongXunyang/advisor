"""Scientific results stay legible and controls stay reachable at compact sizes."""
import csv

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QScrollArea

from advisor.app import load_stylesheet
from advisor.controllers.app_controller import AppController
from advisor.features.scattering_geometry.ui.components.hkl_scan_components import HKLScanResultsTable


def test_scan_columns_and_export_keep_chi_phi_identity(qapp, tmp_path, monkeypatch):
    table = HKLScanResultsTable()
    table.display_results(dict(success=True, H=[1.0], K=[2.0], L=[3.0],
                              tth=[90.0], theta=[12.0], chi=[23.0], phi=[34.0],
                              feasible=[False]))
    assert table.horizontalHeaderItem(5).text() == "χ (°)"
    assert table.horizontalHeaderItem(6).text() == "φ (°)"
    assert table.item(0, 5).text() == "23.0"
    assert table.item(0, 6).text() == "34.0"
    assert table.item(0, 8).text() == "Outside range"
    destination = tmp_path / "scan.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(destination), "CSV"))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    table.export_to_csv()
    with destination.open() as stream:
        row = next(csv.DictReader(stream))
    assert float(row["chi (deg)"]) == 23.0
    assert float(row["phi (deg)"]) == 34.0
    table.close()


def test_compact_workspace_keeps_results_visible_and_custom_inputs_reachable(qapp, tmp_path):
    previous_style = qapp.styleSheet()
    qapp.setStyleSheet(load_stylesheet())
    controller = AppController(qt_app=qapp, library_root=str(tmp_path / "library"))
    try:
        controller.load_bundled_example("idealized_rock_salt")
        controller.init_window.energy_input.setValue(8000)
        controller.init_window.initialize()
        shell = controller.main_window
        shell.resize(1100, 700)
        shell.show()
        sg, sf = [feature.view for feature in controller.features]
        for index, results in [(1, sg.hkl_to_angles_results), (2, sg.hk_angles_results)]:
            sg.tab_widget.setCurrentIndex(index)
            qapp.processEvents()
            table = results.results_table
            rect = table.rect().translated(table.mapTo(shell, QPoint()))
            assert shell.rect().contains(rect)
            assert table.isVisible()
        shell.tab_widget.setCurrentIndex(1)
        sf.tab_widget.setCurrentIndex(1)
        qapp.processEvents()
        custom = sf.customized_plane_widget
        rail = custom.findChild(QScrollArea, "workspaceRail")
        for field in (custom.controls.u_line, custom.controls.v_line, custom.controls.c_line,
                      custom.accessible_controls.tth_min, custom.accessible_controls.tth_max):
            rail.ensureWidgetVisible(field)
            qapp.processEvents()
            position = field.mapTo(rail.viewport(), QPoint())
            assert position.x() >= 0
            assert position.x() + field.width() <= rail.viewport().width()
            assert rail.viewport().rect().contains(position + field.rect().center())
        assert shell.size().width() == 1100
        assert shell.size().height() == 700
    finally:
        controller._cleanup_on_shutdown()
        controller.main_window.close()
        qapp.setStyleSheet(previous_style)
