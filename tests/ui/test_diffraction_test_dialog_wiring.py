"""Headless wiring tests for DiffractionTestDialog: edit-after-calculate
invalidation and cross-reopen persistence via OrientationFitSession.

These exercise the real dialog (only QMessageBox is stubbed), matching the
existing pattern in tests/features/scattering_geometry/ui/.
"""
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


def test_removing_row_after_calculate_disables_apply(qapp, message_box_calls):
    dialog = DiffractionTestDialog(dict(_LATTICE))
    _fill_table(dialog, _two_valid_rows())
    dialog._calculate_orientation()
    assert dialog.apply_btn.isEnabled()

    dialog.table.setCurrentCell(0, 0)
    dialog._remove_selected_row()

    assert not dialog.apply_btn.isEnabled()
    assert dialog.result is None


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
