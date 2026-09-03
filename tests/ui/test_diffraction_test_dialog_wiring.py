"""Headless wiring tests for DiffractionTestDialog: edit-after-calculate
invalidation and cross-reopen persistence via OrientationFitSession.

These exercise the real dialog (only QMessageBox is stubbed), matching the
existing pattern in tests/features/scattering_geometry/ui/.
"""
import ast

import numpy as np
from PyQt5.QtWidgets import QApplication

from advisor.domain.orientation_calculator import OrientationCalculator
from advisor.domain.orientation_types import OrientationFitSession
from advisor.ui.dialogs.diffraction_test_dialog import DiffractionTestDialog
from tests.conftest import LATTICE_CONFIGS

_LATTICE = LATTICE_CONFIGS["orthorhombic"]


def _two_valid_rows():
    """Two diffraction-test rows that are genuinely self-consistent (i.e.
    correspond to the same real orientation), so a Calculate on them
    produces a valid, low-residual fit -- not just individually
    magnitude-consistent rows with an arbitrary, mutually-inconsistent
    angular relationship between them."""
    calc = OrientationCalculator()
    calc.initialize({**_LATTICE, "energy": 20000.0, "roll": 3.0, "pitch": -2.0, "yaw": 5.0})
    rows = []
    for tth, theta, phi, chi in [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 10.0, 5.0)]:
        r = calc.calculate_hkl(tth, theta, phi, chi)
        rows.append({"H": r["H"], "K": r["K"], "L": r["L"], "energy": 20000.0,
                     "tth": tth, "theta": theta, "phi": phi, "chi": chi})
    return rows


def _parallel_hkl_rows():
    """Two rows whose HKL (hence reciprocal g) vectors are parallel, so the
    fit is rejected as non-identifiable (fit_result.valid is False) --
    used to exercise the "failed calculation must not leave a stale UB
    matrix" path."""
    return [
        {"H": 1.0, "K": 0.0, "L": 0.0, "energy": 20000.0,
         "tth": 90.0, "theta": 45.0, "phi": 0.0, "chi": 0.0},
        {"H": 2.0, "K": 0.0, "L": 0.0, "energy": 20000.0,
         "tth": 80.0, "theta": 40.0, "phi": 5.0, "chi": 5.0},
    ]


def _fill_table(dialog, rows):
    while dialog.table.rowCount() < len(rows):
        dialog._add_row()
    while dialog.table.rowCount() > len(rows):
        dialog.table.removeRow(dialog.table.rowCount() - 1)
    columns = ("H", "K", "L", "energy", "tth", "theta", "chi", "phi")
    for r, row in enumerate(rows):
        for c, key in enumerate(columns):
            dialog.table.item(r, c).setText(str(row[key]))


def test_calculate_enables_apply(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    _fill_table(dialog, _two_valid_rows())

    dialog._calculate_orientation()

    assert dialog.apply_btn.isEnabled()
    assert dialog.result is not None
    assert not message_box_calls.warnings


def test_calculate_populates_ub_matrix_from_fit_result(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    _fill_table(dialog, _two_valid_rows())

    dialog._calculate_orientation()

    assert dialog._ub_matrix is not None
    # Exact equality (not allclose): proves the displayed matrix is the same
    # full-precision domain object, not reconstructed from rounded Euler angles.
    assert np.array_equal(dialog._ub_matrix, dialog.session.last_result.UB)
    assert dialog.copy_ub_btn.isEnabled()
    # Spot-check the on-screen cells reflect the same values (6 sig figs).
    assert dialog.ub_matrix_cells[0][0].text() == f"{dialog._ub_matrix[0, 0]:.6g}"


def test_copy_ub_matrix_roundtrips(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    _fill_table(dialog, _two_valid_rows())
    dialog._calculate_orientation()

    dialog._copy_ub_matrix()

    clipboard_text = QApplication.clipboard().text()
    parsed = ast.literal_eval(clipboard_text)
    assert len(parsed) == 3 and all(len(row) == 3 for row in parsed)
    assert np.allclose(np.array(parsed), dialog._ub_matrix, rtol=1e-12)


def test_copy_ub_matrix_disabled_without_result(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    assert not dialog.copy_ub_btn.isEnabled()
    # Calling the handler directly (e.g. if somehow invoked) must be a no-op.
    dialog._copy_ub_matrix()


def test_failed_calculation_clears_stale_ub_matrix(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    _fill_table(dialog, _two_valid_rows())
    dialog._calculate_orientation()
    assert dialog._ub_matrix is not None

    _fill_table(dialog, _parallel_hkl_rows())
    dialog._calculate_orientation()

    assert dialog.result is None
    assert dialog._ub_matrix is None
    assert not dialog.copy_ub_btn.isEnabled()
    assert all(cell.text() == "--" for row in dialog.ub_matrix_cells for cell in row)


def test_editing_after_calculate_disables_apply(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    _fill_table(dialog, _two_valid_rows())
    dialog._calculate_orientation()
    assert dialog.apply_btn.isEnabled()

    # Edit a cell after a successful calculation.
    dialog.table.item(0, 0).setText("1.5")

    assert not dialog.apply_btn.isEnabled()
    assert dialog.result is None
    assert "stale" in dialog.results_group.title().lower()
    assert dialog._ub_matrix is None
    assert not dialog.copy_ub_btn.isEnabled()


def test_removing_row_after_calculate_disables_apply(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    _fill_table(dialog, _two_valid_rows())
    dialog._calculate_orientation()
    assert dialog.apply_btn.isEnabled()

    dialog.table.setCurrentCell(0, 0)
    dialog._remove_selected_row()

    assert not dialog.apply_btn.isEnabled()
    assert dialog.result is None
    assert dialog._ub_matrix is None
    assert not dialog.copy_ub_btn.isEnabled()


def test_apply_and_close_blocked_without_result(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    dialog._apply_and_close()
    assert message_box_calls.warnings  # "No Result" warning shown
    assert dialog.result is None


def test_session_persists_rows_across_reopen_after_cancel(qapp, message_box_calls):
    rows = _two_valid_rows()
    session = OrientationFitSession()
    dialog1 = DiffractionTestDialog(dict(_LATTICE), session=session)
    _fill_table(dialog1, rows)
    dialog1.reject()  # simulates clicking Cancel

    assert len(session.measurements) == 2

    dialog2 = DiffractionTestDialog(dict(_LATTICE), session=session)
    assert dialog2.table.rowCount() == 2
    assert dialog2.table.item(0, 0).text() == str(rows[0]["H"])
    assert dialog2.table.item(1, 1).text() == str(rows[1]["K"])


def test_session_restores_valid_result_on_reopen(qapp, message_box_calls):
    session = OrientationFitSession()
    dialog1 = DiffractionTestDialog(dict(_LATTICE), session=session)
    _fill_table(dialog1, _two_valid_rows())
    dialog1._calculate_orientation()
    assert dialog1.result is not None
    dialog1.accept()

    assert session.last_result is not None
    assert session.last_result.valid

    dialog2 = DiffractionTestDialog(dict(_LATTICE), session=session)
    # Result should be pre-displayed and Apply already enabled, without
    # needing to click Calculate again.
    assert dialog2.apply_btn.isEnabled()
    assert dialog2.result is not None
    assert dialog2._ub_matrix is not None
    assert np.array_equal(dialog2._ub_matrix, session.last_result.UB)
    assert dialog2.copy_ub_btn.isEnabled()


def test_editing_after_calculate_then_closing_does_not_resurrect_stale_fit(qapp, message_box_calls):
    """Regression test: edit a cell after a successful Calculate (which
    invalidates the visible result), then close without recalculating. On
    reopen, the *old* fit must not be restored as valid/applyable against
    the now-different visible rows. (Previously, _invalidate_result() only
    cleared the dialog-local self.result, not session.last_result, so the
    stale fit survived into the session and was restored on reopen even
    though the displayed rows no longer matched it.)
    """
    rows = _two_valid_rows()
    session = OrientationFitSession()
    dialog1 = DiffractionTestDialog(dict(_LATTICE), session=session)
    _fill_table(dialog1, rows)
    dialog1._calculate_orientation()
    assert dialog1.result is not None

    # Edit H on the first row after the calculation.
    edited_h = rows[0]["H"] + 0.5
    dialog1.table.item(0, 0).setText(str(edited_h))
    assert dialog1.result is None  # invalidated locally

    dialog1.reject()  # close without recalculating

    assert session.last_result is None  # must not persist the stale fit
    assert session.measurements[0].H == edited_h

    dialog2 = DiffractionTestDialog(dict(_LATTICE), session=session)
    assert not dialog2.apply_btn.isEnabled()
    assert dialog2.result is None
    assert dialog2.table.item(0, 0).text() == str(edited_h)


def test_stale_session_not_restored_as_applyable(qapp, message_box_calls):
    session = OrientationFitSession()
    dialog1 = DiffractionTestDialog(dict(_LATTICE), session=session)
    _fill_table(dialog1, _two_valid_rows())
    dialog1._calculate_orientation()
    dialog1.accept()
    assert session.last_result.valid

    different_lattice = {**_LATTICE, "a": _LATTICE["a"] + 1.0}
    dialog2 = DiffractionTestDialog(different_lattice, session=session)
    assert not dialog2.apply_btn.isEnabled()
    assert dialog2.result is None
    assert dialog2._ub_matrix is None
    assert not dialog2.copy_ub_btn.isEnabled()
