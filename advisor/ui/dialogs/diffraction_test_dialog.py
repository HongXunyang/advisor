#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dialog for importing orientation from diffraction test data."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (QApplication, QDialog, QDoubleSpinBox, QFormLayout,
                             QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                             QHeaderView, QLabel, QMessageBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from advisor.domain.orientation import fit_orientation_from_diffraction_tests
from advisor.domain.orientation_types import (
    FIT_QUALITY_GOOD,
    FIT_QUALITY_POOR,
    FIT_QUALITY_WARNING,
    DiffractionMeasurement,
    OrientationFitSession,
)

_TABLE_COLUMNS = ("H", "K", "L", "energy", "tth", "theta", "chi", "phi")
_DEFAULT_ROW_VALUES = (0.0, 0.0, 0.0, 2200.0, 90.0, 45.0, 0.0, 0.0)

# Residual-quality -> (display color, short caveat) for the results panel
# and the "Calculation Complete" popup. A fit is never blocked by quality
# (see OrientationFitConfig) -- this is purely advisory styling.
_QUALITY_STYLE = {
    FIT_QUALITY_GOOD: ("#2d5a3d", ""),
    FIT_QUALITY_WARNING: ("#b8860b", "  ⚠ uncertainty is a bit large"),
    FIT_QUALITY_POOR: ("#c0392b", "  ⚠ large uncertainty -- verify before use"),
}


class DiffractionTestDialog(QDialog):
    """Dialog for entering diffraction test data and calculating orientation.

    This dialog allows users to input multiple diffraction tests (H, K, L, energy,
    tth, theta, phi, chi) and calculates the optimal Euler angles (roll, pitch, yaw)
    that best fit the data.

    Table rows and the last accepted result are held in an `OrientationFitSession`
    (see `advisor.domain.orientation_types`), owned by the caller (`InitWindow`)
    and passed in so the dialog can be re-opened with its previous state intact,
    regardless of whether it was previously closed via Cancel or Apply. The
    session is kept in sync (`self.session`) whenever the dialog closes, so the
    caller should re-read `self.session` after `exec_()` rather than only
    `get_result()`.
    """

    def __init__(self, lattice_params: dict, parent=None, session: OrientationFitSession = None):
        """Initialize the dialog.

        Args:
            lattice_params: Dictionary containing lattice parameters (a, b, c, alpha, beta, gamma)
            parent: Parent widget
            session: Optional OrientationFitSession to restore table rows and the
                last accepted fit from (e.g. from a previous time this dialog was
                opened in this Init Window session). A fresh session is created
                if not provided.
        """
        super().__init__(parent)
        self.lattice_params = lattice_params
        self.session = session if session is not None else OrientationFitSession()
        self.result = None  # dict with roll/pitch/yaw/ub_data, set only on a successful Calculate
        self._ub_matrix = None  # full-precision OrientationFitResult.UB, kept separate from
        # `self.result` so displaying/copying it can never change `ub_data`'s shape/contents

        self.setWindowTitle("Import Orientation from UB Matrix Tests")
        self.setMinimumWidth(800)
        self.setMinimumHeight(550)

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)

        # Instructions label
        instructions = QLabel(
            "Enter UB matrix test (diffraction test) data below. Each row represents a measurement "
            "with known HKL indices and measured angles. At least two non-parallel tests are required."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Table for diffraction tests
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["H", "K", "L", "Energy (eV)", "tth (°)", "θ (°)", "χ (°)", "φ (°)"]
        )

        # Set column resize mode
        header = self.table.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        # Restore rows from the session, if any; otherwise start with two blank rows.
        if self.session.measurements:
            for measurement in self.session.measurements:
                self._add_row(measurement)
        else:
            self._add_row()
            self._add_row()

        layout.addWidget(self.table)

        # Row management buttons
        row_buttons_layout = QHBoxLayout()

        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(lambda: self._add_row())
        row_buttons_layout.addWidget(add_row_btn)

        remove_row_btn = QPushButton("Remove Selected Row")
        remove_row_btn.clicked.connect(self._remove_selected_row)
        row_buttons_layout.addWidget(remove_row_btn)

        row_buttons_layout.addStretch()
        layout.addLayout(row_buttons_layout)

        # Results display area: Euler angles on the left, UB matrix on the
        # right, side by side.
        self.results_group = QGroupBox("Calculated Orientation")
        results_outer_layout = QHBoxLayout(self.results_group)

        angles_widget = QWidget()
        angles_layout = QFormLayout(angles_widget)
        angles_layout.setContentsMargins(0, 0, 0, 0)

        self.roll_result = QDoubleSpinBox()
        self.roll_result.setRange(-180, 180)
        self.roll_result.setDecimals(4)
        self.roll_result.setReadOnly(True)
        self.roll_result.setSuffix(" °")
        angles_layout.addRow("Roll:", self.roll_result)

        self.pitch_result = QDoubleSpinBox()
        self.pitch_result.setRange(-180, 180)
        self.pitch_result.setDecimals(4)
        self.pitch_result.setReadOnly(True)
        self.pitch_result.setSuffix(" °")
        angles_layout.addRow("Pitch:", self.pitch_result)

        self.yaw_result = QDoubleSpinBox()
        self.yaw_result.setRange(-180, 180)
        self.yaw_result.setDecimals(4)
        self.yaw_result.setReadOnly(True)
        self.yaw_result.setSuffix(" °")
        angles_layout.addRow("Yaw:", self.yaw_result)

        self.error_label = QLabel("Residual Error: --")
        self.error_label.setWordWrap(True)
        angles_layout.addRow(self.error_label)

        results_outer_layout.addWidget(angles_widget)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        results_outer_layout.addWidget(separator)

        # UB matrix -- populated from OrientationFitResult.UB directly (never
        # reconstructed from the rounded roll/pitch/yaw fields above), so it
        # stays numerically identical to the domain result. Plain labels
        # (not editable boxes) inside one bordered frame, so it reads as a
        # single matrix rather than nine separate input fields.
        ub_widget = QWidget()
        ub_layout = QVBoxLayout(ub_widget)
        ub_layout.setContentsMargins(0, 0, 0, 0)

        ub_title = QLabel("UB Matrix (Å⁻¹)")
        ub_title.setStyleSheet("font-weight: bold;")
        ub_layout.addWidget(ub_title)

        matrix_frame = QFrame()
        matrix_frame.setObjectName("ubMatrixFrame")
        matrix_frame.setFrameShape(QFrame.StyledPanel)
        # Scoped to #ubMatrixFrame specifically -- QLabel is itself a QFrame
        # subclass, so an unscoped "QFrame { border: ... }" rule here would
        # cascade down and put a border around every individual cell too.
        matrix_frame.setStyleSheet(
            "QFrame#ubMatrixFrame { background-color: palette(base); "
            "border: 1px solid palette(mid); border-radius: 3px; }"
        )
        matrix_grid = QGridLayout(matrix_frame)
        matrix_grid.setContentsMargins(12, 10, 12, 10)
        matrix_grid.setHorizontalSpacing(18)
        matrix_grid.setVerticalSpacing(6)
        monospace_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.ub_matrix_cells = []
        for i in range(3):
            row_cells = []
            for j in range(3):
                cell = QLabel("--")
                cell.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                cell.setFont(monospace_font)
                cell.setTextInteractionFlags(Qt.TextSelectableByMouse)
                cell.setMinimumWidth(90)
                matrix_grid.addWidget(cell, i, j)
                row_cells.append(cell)
            self.ub_matrix_cells.append(row_cells)
        ub_layout.addWidget(matrix_frame)
        ub_layout.addStretch()

        results_outer_layout.addWidget(ub_widget)
        results_outer_layout.addStretch()

        self.results_group.setVisible(False)
        layout.addWidget(self.results_group)

        # Action buttons
        button_layout = QHBoxLayout()

        self.calculate_btn = QPushButton("Calculate Orientation")
        self.calculate_btn.clicked.connect(self._calculate_orientation)
        self._set_button_highlighted(self.calculate_btn, True)  # Highlight initially
        button_layout.addWidget(self.calculate_btn)

        self.apply_btn = QPushButton("Apply and Close")
        self.apply_btn.clicked.connect(self._apply_and_close)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)

        self.copy_ub_btn = QPushButton("Copy UB Matrix")
        self.copy_ub_btn.clicked.connect(self._copy_ub_matrix)
        self.copy_ub_btn.setEnabled(False)
        button_layout.addWidget(self.copy_ub_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # Restore the last result, if it's still valid for the current lattice
        # parameters (defense in depth -- the caller is expected to clear the
        # session already when lattice params change).
        restorable = (
            self.session.last_result is not None
            and self.session.last_result.valid
            and not self.session.is_stale_against(self.lattice_params)
        )
        if restorable:
            self._show_result(self.session.last_result, announce=False)

        # Connect edit-invalidation *after* the initial population above, so
        # restoring rows/results from the session doesn't immediately mark
        # itself stale.
        self.table.itemChanged.connect(self._invalidate_result)

    def _set_button_highlighted(self, button: QPushButton, highlighted: bool):
        """Set button to highlighted (pastel blue) or normal style."""
        if highlighted:
            button.setStyleSheet(
                "background-color: #a8d0f0; color: #2c5282; font-weight: bold;"
            )
        else:
            button.setStyleSheet("")  # Reset to default

    def _set_button_success(self, button: QPushButton, success: bool):
        """Set button to success (pastel green) or normal style."""
        if success:
            button.setStyleSheet(
                "background-color: #a8e6c1; color: #2d5a3d; font-weight: bold;"
            )
        else:
            button.setStyleSheet("")  # Reset to default

    def _add_row(self, measurement: DiffractionMeasurement = None):
        """Add a new row to the table, either blank or pre-filled from a
        DiffractionMeasurement (used to restore rows from a session)."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        if measurement is not None:
            values = (
                measurement.H, measurement.K, measurement.L, measurement.energy,
                measurement.tth, measurement.theta, measurement.chi, measurement.phi,
            )
        else:
            values = _DEFAULT_ROW_VALUES

        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, col, item)

    def _remove_selected_row(self):
        """Remove the currently selected row."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
        elif self.table.rowCount() > 0:
            # If no row selected, remove the last row
            self.table.removeRow(self.table.rowCount() - 1)
        self._invalidate_result()

    def _invalidate_result(self, *_args):
        """Mark any previously-calculated/restored result as stale: any table
        edit, row addition, or row removal after a calculation must not leave
        a now-inconsistent result applyable via "Apply and Close".

        Also clears the persisted `session.last_result` (not just the
        dialog-local `self.result`/display), so that closing without
        recalculating can't later restore a "valid" result on reopen that no
        longer matches the edited rows.
        """
        if self.result is None and not self.results_group.isVisible():
            return  # nothing to invalidate yet
        self.result = None
        self.session.last_result = None
        self.session.lattice_params_at_fit = None
        self.apply_btn.setEnabled(False)
        self._set_button_success(self.apply_btn, False)
        self._set_button_highlighted(self.calculate_btn, True)
        self.results_group.setTitle("Calculated Orientation (stale -- recalculate)")
        self.error_label.setStyleSheet("")  # clear any quality-warning color from the last result

        self._ub_matrix = None
        for row_cells in self.ub_matrix_cells:
            for cell in row_cells:
                cell.setText("--")
        self.copy_ub_btn.setEnabled(False)

    def _get_diffraction_tests(self, *, strict: bool) -> list:
        """Extract diffraction test data from the table.

        In strict mode (used by "Calculate"): shows a warning and returns
        None on the first unparseable row or if the table is empty.

        In non-strict mode (used when syncing the session on close): silently
        skips unparseable rows instead of blocking, so whatever is still
        parseable survives a Cancel for the next time the dialog is opened.
        """
        tests = []
        for row in range(self.table.rowCount()):
            try:
                test = {
                    "H": float(self.table.item(row, 0).text()),
                    "K": float(self.table.item(row, 1).text()),
                    "L": float(self.table.item(row, 2).text()),
                    "energy": float(self.table.item(row, 3).text()),
                    "tth": float(self.table.item(row, 4).text()),
                    "theta": float(self.table.item(row, 5).text()),
                    "chi": float(self.table.item(row, 6).text()),
                    "phi": float(self.table.item(row, 7).text()),
                }
                tests.append(test)
            except (ValueError, AttributeError) as e:
                if strict:
                    QMessageBox.warning(
                        self,
                        "Invalid Input",
                        f"Row {row + 1} contains invalid data. Please enter numeric values.\n\nError: {e}",
                    )
                    return None
                continue

        if not tests and strict:
            QMessageBox.warning(
                self,
                "No Data",
                "Please enter at least two non-parallel diffraction tests.",
            )
            return None

        return tests

    def _calculate_orientation(self):
        """Calculate the optimal orientation from the entered data."""
        tests = self._get_diffraction_tests(strict=True)
        if tests is None:
            return

        fit_result = fit_orientation_from_diffraction_tests(self.lattice_params, tests)

        # Keep the session's raw measurements in sync regardless of outcome,
        # so a failed/rejected calculation still preserves what was typed.
        self.session.measurements = [DiffractionMeasurement.from_dict(t) for t in tests]

        if not fit_result.valid:
            self.session.last_result = None
            self.session.lattice_params_at_fit = None
            self._invalidate_result()
            QMessageBox.warning(
                self,
                "Calculation Failed",
                f"Failed to calculate a valid orientation:\n\n{fit_result.message}",
            )
            return

        self.session.last_result = fit_result
        self.session.lattice_params_at_fit = dict(self.lattice_params)
        self._show_result(fit_result, announce=True)

    def _show_result(self, fit_result, announce: bool):
        """Display an accepted OrientationFitResult and enable Apply.

        A fit is shown (and Apply enabled) regardless of `fit_result.quality`
        -- the Kabsch solve always returns the least-squares-best rotation
        for whatever was entered, so "poor" quality is a caveat to surface,
        not a reason to withhold the result. See `_QUALITY_STYLE`.
        """
        self.roll_result.setValue(fit_result.roll)
        self.pitch_result.setValue(fit_result.pitch)
        self.yaw_result.setValue(fit_result.yaw)

        color, caveat = _QUALITY_STYLE.get(fit_result.quality, ("#000000", ""))
        self.error_label.setText(f"Residual RMS: {fit_result.residual_rms:.6g} r.l.u.{caveat}")
        self.error_label.setStyleSheet(f"color: {color}; font-weight: bold;" if caveat else "")

        self.results_group.setTitle("Calculated Orientation (Updated)")
        self.results_group.setVisible(True)
        self.apply_btn.setEnabled(True)

        self._set_button_highlighted(self.calculate_btn, False)
        self._set_button_success(self.apply_btn, True)

        self._ub_matrix = fit_result.UB.copy()
        for i in range(3):
            for j in range(3):
                self.ub_matrix_cells[i][j].setText(f"{self._ub_matrix[i, j]:.6g}")
        self.copy_ub_btn.setEnabled(True)

        self.result = {
            "roll": fit_result.roll,
            "pitch": fit_result.pitch,
            "yaw": fit_result.yaw,
            "ub_data": [m.to_dict() for m in fit_result.measurements],
        }

        if announce:
            error_text = "<br>".join(
                f"&nbsp;&nbsp;Test {i + 1}: residual = {r:.4g} r.l.u."
                for i, r in enumerate(fit_result.per_measurement_residuals or [])
            )
            caveat_html = (
                f'<p style="color:{color};"><b>{caveat.strip()}</b></p>' if caveat else ""
            )
            # Qt auto-detects and renders this as rich text (HTML tags present),
            # so the plain static QMessageBox.information(...) call still works
            # -- keeping it as a static call (rather than an instance + exec_())
            # matters so tests can stub it the same way as every other QMessageBox
            # call in this codebase.
            QMessageBox.information(
                self,
                "Calculation Complete",
                f"Orientation calculated successfully.<br><br>"
                f"Roll: {fit_result.roll:.4f}°<br>"
                f"Pitch: {fit_result.pitch:.4f}°<br>"
                f"Yaw: {fit_result.yaw:.4f}°<br><br>"
                f'<span style="color:{color};">Residual RMS: {fit_result.residual_rms:.6g} r.l.u.</span>'
                f"{caveat_html}<br>"
                f"Per-measurement residuals:<br>{error_text}",
            )

    def _copy_ub_matrix(self):
        """Copy the full-precision UB matrix to the clipboard as a parseable
        three-row nested list, e.g. [[v11, v12, v13], ...]. `repr()` on the
        native Python floats gives the shortest decimal string that
        round-trips exactly to the original float64 value (~15-17
        significant digits), which is what a comparison script needs.

        Purely reads `self._ub_matrix`; never touches `self.session` or
        `ub_data`, so it cannot apply the orientation or alter app state.
        """
        if self._ub_matrix is None:
            return
        QApplication.clipboard().setText(repr(self._ub_matrix.tolist()))

    def _apply_and_close(self):
        """Apply the calculated orientation and close the dialog."""
        if self.result is not None:
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "No Result",
                "Please calculate the orientation first.",
            )

    def _sync_session_before_close(self):
        """Best-effort capture of whatever is currently in the table, so it
        survives even a Cancel/close without a successful Calculate."""
        tests = self._get_diffraction_tests(strict=False)
        self.session.measurements = [DiffractionMeasurement.from_dict(t) for t in tests]

    def accept(self):
        self._sync_session_before_close()
        super().accept()

    def reject(self):
        self._sync_session_before_close()
        super().reject()

    def get_result(self) -> dict:
        """Get the calculated orientation.

        Returns:
            Dictionary with roll, pitch, yaw, ub_data, or None if not calculated
            (or invalidated by a subsequent edit).
        """
        return self.result
