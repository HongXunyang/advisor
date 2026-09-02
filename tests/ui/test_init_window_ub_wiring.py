"""Headless wiring tests for InitWindow's "Set UB Matrix" state handling:
the Cancel-crash regression, invalidation on lattice/CIF change and Reset,
and the ub_data application-parameter boundary.
"""
from PyQt5.QtWidgets import QDialog

from advisor.domain.orientation_calculator import OrientationCalculator
from advisor.domain.orientation import fit_orientation_from_diffraction_tests
from advisor.ui.dialogs.diffraction_test_dialog import DiffractionTestDialog
from advisor.ui.init_window import InitWindow
from tests.conftest import LATTICE_CONFIGS

_LATTICE = LATTICE_CONFIGS["orthorhombic"]


def _valid_fit_result(lattice_params, energy=20000.0, roll=3.0, pitch=-2.0, yaw=5.0):
    calc = OrientationCalculator()
    calc.initialize({**lattice_params, "energy": energy, "roll": roll, "pitch": pitch, "yaw": yaw})
    tests = []
    for tth, theta, phi, chi in [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 10.0, 5.0)]:
        r = calc.calculate_hkl(tth, theta, phi, chi)
        tests.append({"H": r["H"], "K": r["K"], "L": r["L"], "energy": energy,
                       "tth": tth, "theta": theta, "phi": phi, "chi": chi})
    return fit_orientation_from_diffraction_tests(lattice_params, tests)


def _apply_valid_fit(window):
    """Simulate a full accepted Set-UB-Matrix flow: run a real fit against
    the window's current lattice params and store it as if the user had
    clicked Calculate then Apply and Close."""
    lattice_params = {
        "a": window.a_input.value(), "b": window.b_input.value(), "c": window.c_input.value(),
        "alpha": window.alpha_input.value(), "beta": window.beta_input.value(), "gamma": window.gamma_input.value(),
    }
    fit_result = _valid_fit_result(lattice_params)
    assert fit_result.valid
    window._ub_session.measurements = fit_result.measurements
    window._ub_session.last_result = fit_result
    window._ub_session.lattice_params_at_fit = dict(lattice_params)
    window._applied_ub_result = fit_result
    window.roll_input.setValue(fit_result.roll)
    window.pitch_input.setValue(fit_result.pitch)
    window.yaw_input.setValue(fit_result.yaw)
    return fit_result


def test_cancel_does_not_raise(qapp, monkeypatch):
    """Regression test for the confirmed UnboundLocalError: clicking Cancel
    (dialog.exec_() returns Rejected) used to crash because `result` was
    read outside the `if Accepted:` block."""

    def fake_exec(self):
        self.reject()
        return QDialog.Rejected

    monkeypatch.setattr(DiffractionTestDialog, "exec_", fake_exec)

    window = InitWindow()
    window.open_diffraction_test_dialog()  # must not raise

    assert window._ub_session.last_result is None
    assert window._current_ub_data() is None


def test_lattice_change_clears_ub_session(qapp):
    window = InitWindow()
    _apply_valid_fit(window)
    assert window._current_ub_data() is not None

    window.a_input.setValue(window.a_input.value() + 1.0)

    assert window._ub_session.last_result is None
    assert window._ub_session.measurements == []
    assert window._current_ub_data() is None
    # Euler-angle fields are left as-is (not force-reset), matching how
    # lattice inputs themselves aren't reset by unrelated changes either.


def test_angle_lattice_change_clears_ub_session(qapp):
    window = InitWindow()
    _apply_valid_fit(window)
    window.alpha_input.setValue(window.alpha_input.value() + 1.0)
    assert window._current_ub_data() is None


def test_cif_apply_clears_ub_session(qapp):
    window = InitWindow()
    _apply_valid_fit(window)
    assert window._current_ub_data() is not None

    window.apply_cif_parameters(4.5, 4.5, 10.0, 90.0, 90.0, 120.0)

    assert window._current_ub_data() is None


def test_reset_clears_ub_session(qapp):
    window = InitWindow()
    _apply_valid_fit(window)
    assert window._current_ub_data() is not None

    window.reset_inputs()

    assert window._ub_session.last_result is None
    assert window._ub_session.measurements == []
    assert window._current_ub_data() is None


def test_valid_fit_populates_ub_data_on_initialize(qapp):
    window = InitWindow()
    fit_result = _apply_valid_fit(window)

    ub_data = window._current_ub_data()
    assert ub_data is not None
    assert len(ub_data) == len(fit_result.measurements)
    assert ub_data[0]["H"] == fit_result.measurements[0].H


def test_no_ub_data_without_a_fit(qapp):
    window = InitWindow()
    assert window._current_ub_data() is None


def test_calculate_then_cancel_does_not_leak_into_ub_data(qapp, monkeypatch, message_box_calls):
    """Regression test: a valid Calculate followed by Cancel must not export
    ub_data, and must not touch the Euler-angle fields -- only an explicit
    Apply-and-Close may do either. (Previously, DiffractionTestDialog wrote
    every valid calculation straight into session.last_result, and
    _current_ub_data() only checked validity/staleness, not whether the
    dialog was actually accepted -- so a cancelled calculation still leaked
    into the exported ub_data.)
    """
    lattice_params = {
        "a": 4.0, "b": 4.0, "c": 4.0, "alpha": 90.0, "beta": 90.0, "gamma": 90.0,
    }

    def fake_exec(self):
        rows = []
        calc = OrientationCalculator()
        calc.initialize({**lattice_params, "energy": 20000.0, "roll": 3.0, "pitch": -2.0, "yaw": 5.0})
        for tth, theta, phi, chi in [(90.0, 45.0, 0.0, 0.0), (60.0, 30.0, 10.0, 5.0)]:
            r = calc.calculate_hkl(tth, theta, phi, chi)
            rows.append({"H": r["H"], "K": r["K"], "L": r["L"], "energy": 20000.0,
                         "tth": tth, "theta": theta, "phi": phi, "chi": chi})
        columns = ("H", "K", "L", "energy", "tth", "theta", "chi", "phi")
        while self.table.rowCount() < len(rows):
            self._add_row()
        for r, row in enumerate(rows):
            for c, key in enumerate(columns):
                self.table.item(r, c).setText(str(row[key]))
        self._calculate_orientation()
        assert self.result is not None  # calculation succeeded
        self.reject()  # then the user clicks Cancel
        return QDialog.Rejected

    monkeypatch.setattr(DiffractionTestDialog, "exec_", fake_exec)

    window = InitWindow()
    window.a_input.setValue(4.0)
    window.b_input.setValue(4.0)
    window.c_input.setValue(4.0)
    window.open_diffraction_test_dialog()

    assert window._ub_session.last_result is not None  # draft persisted for reopen
    assert window._applied_ub_result is None  # but never applied
    assert window._current_ub_data() is None
    assert window.roll_input.value() == 0.0
    assert window.pitch_input.value() == 0.0
    assert window.yaw_input.value() == 0.0
