#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (QDoubleSpinBox, QFormLayout, QGridLayout,
                             QGroupBox, QLabel, QMessageBox, QPushButton,
                             QVBoxLayout, QWidget)

from advisor.domain import UnitConverter
from advisor.domain.orientation_types import OrientationFitSession
from advisor.ui.components.cif_selector import CifDropTarget, CifStructureSummary
from advisor.ui.dialogs import DiffractionTestDialog
from advisor.ui.dialogs.cif_details_dialog import CifDetailsDialog
from advisor.ui.visualizers import CoordinateVisualizer, UnitcellVisualizer


class HighPrecisionSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that stores/returns full internal precision (so
    `setValue()` doesn't silently truncate a UB-matrix fit's precision --
    see `decimals()` docs: it rounds the stored value, not just the display)
    while only *displaying* a fixed, shorter number of decimals.
    """

    def __init__(self, display_decimals=2, parent=None):
        super().__init__(parent)
        self._display_decimals = display_decimals

    def textFromValue(self, value):
        return f"{value:.{self._display_decimals}f}"


class InitWindow(QWidget):
    """Initialization window for setting up lattice parameters."""

    initialized = pyqtSignal(dict)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.unit_converter = UnitConverter()
        self._ub_session = OrientationFitSession()
        # The fit actually backing the current Euler-angle fields/ub_data --
        # distinct from self._ub_session.last_result, which is a draft/candidate
        # that persists across Cancel for dialog-reopen convenience but must
        # never itself be exported. Only set via an explicit Apply-and-Close.
        self._applied_ub_result = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI components."""
        layout = QGridLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(40)

        # Group box for lattice parameters
        lattice_group = QGroupBox("Lattice Parameters")
        lattice_layout = QGridLayout(lattice_group)

        # Lattice constants (left column). HighPrecisionSpinBox (not a plain
        # QDoubleSpinBox) so a CIF-derived value is never silently rounded by
        # setValue() before display -- the actual value handed to Initialize
        # comes from the accepted StructureSource, not these widgets, but the
        # displayed value must still not misrepresent it. Ranges are wide
        # enough that realistic cells (including large/organic ones) are
        # never clamped either; real cell validity is enforced by
        # advisor.domain.cif_import.cell_validation, not these bounds.
        self.a_input = HighPrecisionSpinBox(display_decimals=4)
        self.a_input.setRange(0.001, 10000.0)
        self.a_input.setDecimals(6)
        self.a_input.setValue(5.0)
        self.a_input.setSuffix(" Å")
        self.a_input.valueChanged.connect(self._invalidate_ub_session)
        lattice_layout.addWidget(QLabel("a:"), 0, 0)
        lattice_layout.addWidget(self.a_input, 0, 1)

        self.b_input = HighPrecisionSpinBox(display_decimals=4)
        self.b_input.setRange(0.001, 10000.0)
        self.b_input.setDecimals(6)
        self.b_input.setValue(5.0)
        self.b_input.setSuffix(" Å")
        self.b_input.valueChanged.connect(self._invalidate_ub_session)
        lattice_layout.addWidget(QLabel("b:"), 1, 0)
        lattice_layout.addWidget(self.b_input, 1, 1)

        self.c_input = HighPrecisionSpinBox(display_decimals=4)
        self.c_input.setRange(0.001, 10000.0)
        self.c_input.setDecimals(6)
        self.c_input.setValue(5.0)
        self.c_input.setSuffix(" Å")
        self.c_input.valueChanged.connect(self._invalidate_ub_session)
        lattice_layout.addWidget(QLabel("c:"), 2, 0)
        lattice_layout.addWidget(self.c_input, 2, 1)

        # Lattice angles (right column)
        self.alpha_input = HighPrecisionSpinBox(display_decimals=4)
        self.alpha_input.setRange(0.0001, 179.9999)
        self.alpha_input.setDecimals(6)
        self.alpha_input.setValue(90.0)
        self.alpha_input.setSuffix(" °")
        self.alpha_input.valueChanged.connect(self.update_visualization)
        self.alpha_input.valueChanged.connect(self._invalidate_ub_session)
        lattice_layout.addWidget(QLabel("α:"), 0, 2)
        lattice_layout.addWidget(self.alpha_input, 0, 3)

        self.beta_input = HighPrecisionSpinBox(display_decimals=4)
        self.beta_input.setRange(0.0001, 179.9999)
        self.beta_input.setDecimals(6)
        self.beta_input.setValue(90.0)
        self.beta_input.setSuffix(" °")
        self.beta_input.valueChanged.connect(self.update_visualization)
        self.beta_input.valueChanged.connect(self._invalidate_ub_session)
        lattice_layout.addWidget(QLabel("β:"), 1, 2)
        lattice_layout.addWidget(self.beta_input, 1, 3)

        self.gamma_input = HighPrecisionSpinBox(display_decimals=4)
        self.gamma_input.setRange(0.0001, 179.9999)
        self.gamma_input.setDecimals(6)
        self.gamma_input.setValue(90.0)
        self.gamma_input.setSuffix(" °")
        self.gamma_input.valueChanged.connect(self.update_visualization)
        self.gamma_input.valueChanged.connect(self._invalidate_ub_session)
        lattice_layout.addWidget(QLabel("γ:"), 2, 2)
        lattice_layout.addWidget(self.gamma_input, 2, 3)

        # Add spacing between columns and margins
        lattice_layout.setColumnStretch(1, 1)
        lattice_layout.setColumnStretch(3, 1)
        lattice_layout.setHorizontalSpacing(40)
        lattice_layout.setVerticalSpacing(10)
        lattice_layout.setContentsMargins(20, 20, 20, 20)

        # Add lattice group to main layout at (0,0)
        layout.addWidget(lattice_group, 0, 0)

        # Group box for X-ray energy
        energy_group = QGroupBox("X-ray Energy")
        energy_layout = QFormLayout(energy_group)

        self.energy_input = QDoubleSpinBox()
        self.energy_input.setRange(0, 1000000)
        self.energy_input.setValue(950.0)
        self.energy_input.setSuffix(" eV")
        self.energy_input.valueChanged.connect(self.on_energy_changed)
        energy_layout.addRow("Energy:", self.energy_input)

        self.wavelength_input = QDoubleSpinBox()
        self.wavelength_input.setRange(0, 1000)
        self.wavelength_input.setDecimals(3)
        self.wavelength_input.setValue(self.unit_converter.ev_to_angstrom(950.0))
        self.wavelength_input.setSuffix(" Å")
        self.wavelength_input.valueChanged.connect(self.on_wavelength_changed)
        energy_layout.addRow("λ:", self.wavelength_input)
        
        # wavevector
        self.wavevector_input = QDoubleSpinBox()
        self.wavevector_input.setRange(0, 100)
        self.wavevector_input.setDecimals(3)
        self.wavevector_input.setValue(2 * 3.1415926 / self.wavelength_input.value())
        self.wavevector_input.setSuffix(" Å⁻¹")
        self.wavevector_input.valueChanged.connect(self.on_wavevector_changed)
        energy_layout.addRow("|k|:", self.wavevector_input)


        # Add energy group to main layout at (0,1)
        layout.addWidget(energy_group, 0, 1)

        # Group box for Sample orientation Euler angles
        euler_group = QGroupBox("Sample Orientation (Euler Angles)")
        euler_layout = QFormLayout(euler_group)

        self.roll_input = HighPrecisionSpinBox(display_decimals=2)
        self.roll_input.setObjectName("eulerAngleSpinBox")
        self.roll_input.setRange(-180.0, 180.0)
        # Internal decimals stay high so setValue() doesn't silently truncate
        # a UB-matrix fit's precision before it reaches BrillouinCalculator;
        # only the displayed text (via HighPrecisionSpinBox) is 2 decimals.
        self.roll_input.setDecimals(6)
        self.roll_input.setValue(0.0)
        self.roll_input.setSuffix(" °")
        self.roll_input.setToolTip("Rotation about the new X axis")
        self.roll_input.valueChanged.connect(self.update_visualization)
        euler_layout.addRow("Roll:", self.roll_input)

        self.pitch_input = HighPrecisionSpinBox(display_decimals=2)
        self.pitch_input.setObjectName("eulerAngleSpinBox")
        self.pitch_input.setRange(-180.0, 180.0)
        self.pitch_input.setDecimals(6)
        self.pitch_input.setValue(0.0)
        self.pitch_input.setSuffix(" °")
        self.pitch_input.setToolTip("Rotation about the new Y axis")
        self.pitch_input.valueChanged.connect(self.update_visualization)
        euler_layout.addRow("Pitch:", self.pitch_input)

        self.yaw_input = HighPrecisionSpinBox(display_decimals=2)
        self.yaw_input.setObjectName("eulerAngleSpinBox")
        self.yaw_input.setRange(-180.0, 180.0)
        self.yaw_input.setDecimals(6)
        self.yaw_input.setValue(0.0)
        self.yaw_input.setSuffix(" °")
        self.yaw_input.setToolTip("Rotation about the original Z axis")
        self.yaw_input.valueChanged.connect(self.update_visualization)
        euler_layout.addRow("Yaw:", self.yaw_input)

        # Add "Set UB Matrix (Import from Diffraction Tests)" button
        self.import_orientation_btn = QPushButton("Set UB Matrix")
        self.import_orientation_btn.setToolTip(
            "Calculate Sample orientation (Euler angles) from known diffraction measurements. E.g. Two Braggs (002) (101) peaks are found at certain angles (tth, theta, phi, chi), at certain energy, the sample orientation can be determined."
        )
        self.import_orientation_btn.clicked.connect(self.open_diffraction_test_dialog)
        euler_layout.addRow(self.import_orientation_btn)

        # Add euler group to main layout at (0,2)
        layout.addWidget(euler_group, 0, 2)

        # Create and add the coordinate visualizer
        self.visualizer = CoordinateVisualizer()
        # initialize the visualizer
        self.visualizer.initialize(
            {
                "a": self.a_input.value(),
                "b": self.b_input.value(),
                "c": self.c_input.value(),
                "alpha": self.alpha_input.value(),
                "beta": self.beta_input.value(),
                "gamma": self.gamma_input.value(),
                "roll": self.roll_input.value(),
                "pitch": self.pitch_input.value(),
                "yaw": self.yaw_input.value(),
            }
        )
        self.visualizer.visualize_lab_system()
        layout.addWidget(self.visualizer, 1, 1)

        # Create and add the unit cell visualizer
        self.unitcell_visualizer = UnitcellVisualizer()
        layout.addWidget(self.unitcell_visualizer, 1, 2)

        # File input area: one shared CifDropTarget (drag-drop + Browse, both
        # funnel into a single cifSelected signal -- see cif_selector.py)
        # stacked above a compact CifStructureSummary. Same footprint as the
        # old line-edit+Browse row; the extra summary row fits in the
        # headroom this cell already has from the taller visualizers beside
        # it, so the window doesn't grow.
        file_group = QGroupBox("Crystal Structure File")
        file_layout = QVBoxLayout(file_group)

        self._cif_drop_target = CifDropTarget()
        self._cif_drop_target.cifSelected.connect(self._on_cif_selected)
        self._cif_drop_target.selectionRejected.connect(self._on_cif_selection_rejected)
        file_layout.addWidget(self._cif_drop_target)

        self._structure_summary = CifStructureSummary()
        self._structure_summary.set_empty()
        self._structure_summary.detailsRequested.connect(self._on_details_requested)
        self._structure_summary.useManualLatticeRequested.connect(self._on_use_manual_lattice_clicked)
        self._structure_summary.removeStructureRequested.connect(self._on_remove_cif_clicked)
        self._structure_summary.libraryPickerRequested.connect(self._on_library_picker_requested)
        self._structure_summary.tryExampleRequested.connect(self._on_try_example_requested)
        file_layout.addWidget(self._structure_summary)

        # Add file group to main layout at (1,0) spanning 1 column
        layout.addWidget(file_group, 1, 0, 1, 1)

        # Initialize button
        initialize_button = QPushButton("Initialize")
        initialize_button.clicked.connect(self.initialize)
        # Add initialize button at (2,0) spanning 1 column
        layout.addWidget(initialize_button, 2, 0, 1, 1)

        # Add spacer
        layout.setRowStretch(3, 1)

    def _invalidate_ub_session(self, *_args):
        """Clear the stored UB-matrix diffraction measurements and any
        fitted orientation, since they're no longer valid once the lattice
        parameters (or the CIF they were derived from) change.

        Also clears (and resets to 0) the Euler-angle fields if their
        current values came from an applied UB fit (`self._applied_ub_result`)
        -- otherwise a stale, now-orphaned orientation would silently remain
        active with `ub_data=None`, no longer traceable to the fit that
        produced it. Manually-entered Euler angles are left untouched.
        """
        self._ub_session.clear()
        if self._applied_ub_result is not None:
            self._applied_ub_result = None
            self.roll_input.setValue(0.0)
            self.pitch_input.setValue(0.0)
            self.yaw_input.setValue(0.0)

    def _effective_lattice_params(self) -> dict:
        """The single authoritative (a, b, c, alpha, beta, gamma) for this
        session: full-precision `StructureSource` values when CIF-derived,
        the (editable) widget values otherwise.

        `HighPrecisionSpinBox` only controls *displayed* text -- `setValue()`
        still rounds the internally stored value to `decimals()` (6 for the
        lattice fields), which is more precision than the old plain
        `QDoubleSpinBox` had but is still not the CIF's true full precision.
        UB fitting (`open_diffraction_test_dialog`, `_current_ub_data`'s
        staleness check) and the setup preview (`update_visualization`) must
        read the exact same value `initialize()` sends, not separately read
        the (slightly rounded, for a CIF source) widgets.
        """
        source = self.controller.structure_source if self.controller else None
        if source is not None and source.source_kind == "cif":
            return {
                "a": source.a, "b": source.b, "c": source.c,
                "alpha": source.alpha, "beta": source.beta, "gamma": source.gamma,
            }
        return {
            "a": self.a_input.value(), "b": self.b_input.value(), "c": self.c_input.value(),
            "alpha": self.alpha_input.value(), "beta": self.beta_input.value(), "gamma": self.gamma_input.value(),
        }

    @pyqtSlot()
    def open_diffraction_test_dialog(self):
        """Open the diffraction test dialog to import orientation from measurements."""
        lattice_params = self._effective_lattice_params()

        # Open the dialog, seeded with (and updating) this window's UB session
        # so table rows and the last accepted fit survive close/reopen -- this
        # is a *draft/candidate* state and persists across Cancel.
        dialog = DiffractionTestDialog(lattice_params, self, session=self._ub_session)
        accepted = dialog.exec_() == DiffractionTestDialog.Accepted
        # dialog keeps self._ub_session in sync (rows + result) regardless of
        # whether it was accepted or cancelled -- see DiffractionTestDialog.
        self._ub_session = dialog.session

        if accepted:
            result = dialog.get_result()
            if result is not None:
                # Apply the calculated Sample orientation Euler angles
                self.roll_input.setValue(result["roll"])
                self.pitch_input.setValue(result["pitch"])
                self.yaw_input.setValue(result["yaw"])
                # update_visualization will be triggered by valueChanged signals

                # Only an explicit Apply-and-Close sets the *applied* state
                # that ub_data is derived from -- a merely-calculated-then-
                # cancelled result must never reach _current_ub_data().
                self._applied_ub_result = self._ub_session.last_result

    def set_lattice_inputs_enabled(self, enabled: bool):
        """Enable/disable lattice parameter inputs (a,b,c,alpha,beta,gamma)."""
        self.a_input.setEnabled(enabled)
        self.b_input.setEnabled(enabled)
        self.c_input.setEnabled(enabled)
        self.alpha_input.setEnabled(enabled)
        self.beta_input.setEnabled(enabled)
        self.gamma_input.setEnabled(enabled)

    @pyqtSlot(str)
    def _on_cif_selected(self, path: str):
        """A CifDropTarget selection (drag-drop or Browse) -- exactly one
        deliberate import attempt per user action. Delegates validation and
        acceptance to AppController.import_cif(); this method only ever
        reflects the returned result, it never mutates accepted state
        itself. No modal dialog for an ordinary successful load -- the
        compact inline CifStructureSummary is the feedback surface.
        """
        if self.controller is None:
            return
        result = self.controller.import_cif(path)
        if result.status == "rejected":
            self._structure_summary.set_rejected(result.message)
        elif result.status == "unchanged":
            # A genuine "ready"/"ready_geometry_only" accept already shows
            # its library note via on_structure_changed() below (reached
            # through every accept entry point, not only this one) -- but an
            # "unchanged" reselection never invalidates/re-renders anything,
            # so this is the one status this handler must still surface
            # itself.
            self._structure_summary.set_library_note(result.library_note)

    @pyqtSlot()
    def _on_library_picker_requested(self):
        if self.controller is None:
            return
        from advisor.ui.dialogs.library_picker_dialog import LibraryPickerDialog

        invoking_widget = self.focusWidget()
        LibraryPickerDialog(self.controller, self).exec_()
        if invoking_widget is not None:
            invoking_widget.setFocus()

    @pyqtSlot()
    def _on_try_example_requested(self):
        """Loads the sole bundled example through the same accept path as
        any other CIF -- labeled origin, citation visible in Details…, and
        respects the remembering preference like any other import."""
        if self.controller is None:
            return
        from advisor.domain.library.bundled_examples import EXAMPLES

        result = self.controller.load_bundled_example(EXAMPLES[0].key)
        if result.status == "rejected":
            self._structure_summary.set_rejected(result.message)
        elif result.status == "unchanged":
            self._structure_summary.set_library_note(result.library_note)

    @pyqtSlot(str)
    def _on_cif_selection_rejected(self, message: str):
        """CifDropTarget rejected the selection itself (multi-file, folder,
        non-local, wrong extension) before it ever reached the importer."""
        self._structure_summary.set_rejected(message)

    @pyqtSlot()
    def _on_details_requested(self):
        source = self._structure_summary.current_source()
        if source is not None:
            CifDetailsDialog(source, self).exec_()

    @pyqtSlot()
    def _on_use_manual_lattice_clicked(self):
        """Keep the currently displayed cell values as a manual starting
        point, but drop the CIF association and atomic capabilities."""
        if self.controller is None:
            return
        self.controller.use_manual_lattice(
            self.a_input.value(), self.b_input.value(), self.c_input.value(),
            self.alpha_input.value(), self.beta_input.value(), self.gamma_input.value(),
        )

    @pyqtSlot()
    def _on_remove_cif_clicked(self):
        if self.controller is not None:
            self.controller.remove_structure()

    def on_structure_changed(self, source, library_note=None):
        """Called by AppController whenever the accepted structure changes
        (a genuine replacement, a switch to manual lattice, or removal) --
        never for a no-op reselection, since AppController filters those out
        before this is reached. Renders the new accepted state and performs
        the unconditional orientation/UB reset REQUIREMENT_1 requires for an
        actual structure change (distinct from the narrower per-field
        `_invalidate_ub_session`, which only fires for ordinary edits).

        `library_note` is shown here (rather than only by whichever widget's
        signal handler triggered the accept) so every accept entry point --
        setup drop/Browse, File>Open CIF, the Change Structure dialog, Try an
        example, and My structures -- surfaces a consistent "Added"/"could
        not save" confirmation, not only the setup screen's own handler
        (REVIEW.md finding #6).
        """
        if source is None:
            self._structure_summary.set_empty()
            self.set_lattice_inputs_enabled(True)
            self.unitcell_visualizer.reset()
        else:
            self._set_lattice_display(source.a, source.b, source.c, source.alpha, source.beta, source.gamma)
            self.set_lattice_inputs_enabled(source.source_kind != "cif")
            self._structure_summary.set_source(source)
            self._structure_summary.set_library_note(library_note)
            # Gate on structure_factor_ok, not geometry_ok: a geometry-only
            # CIF (valid cell, no usable atoms) still has geometry_ok=True,
            # but constructing a Crystal for the preview would render
            # Dans_Diffraction's silently-fabricated default atom -- not a
            # real atom from the file. Show the cell-only state (reset) in
            # that case instead of a fictitious structure.
            if source.source_kind == "cif" and source.capabilities.structure_factor_ok:
                self.update_unitcell_visualization(source.effective_path)
            else:
                self.unitcell_visualizer.reset()

        self._on_structure_replaced()
        self.update_visualization()

    def _set_lattice_display(self, a, b, c, alpha, beta, gamma):
        """Set the lattice spinboxes without re-triggering UB invalidation
        or a redraw for each individual field -- `on_structure_changed`
        does both once, explicitly, after all six are set."""
        for widget, value in (
            (self.a_input, a), (self.b_input, b), (self.c_input, c),
            (self.alpha_input, alpha), (self.beta_input, beta), (self.gamma_input, gamma),
        ):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)

    def _on_structure_replaced(self):
        """Unconditionally clear the UB session and zero the Euler-angle
        fields, including manually-entered ones, for an actual structure
        change. Distinct from `_invalidate_ub_session`, which only zeroes
        Euler fields if they came from an applied fit -- an ordinary manual
        edit to one lattice field shouldn't discard a manually-typed
        orientation, but a structure replacement/removal should.
        """
        self._ub_session.clear()
        self._applied_ub_result = None
        self.roll_input.setValue(0.0)
        self.pitch_input.setValue(0.0)
        self.yaw_input.setValue(0.0)

    def update_unitcell_visualization(self, cif_file_path: str):
        """Update the unit cell visualizer with a new CIF file.

        UnitcellVisualizer.set_parameters()/visualize_unitcell() already
        catch and record their own failures (`render_error_message`,
        surfaced inline on the plot) rather than raising, so this is a thin
        pass-through.
        """
        self.unitcell_visualizer.set_parameters({"cif_file": cif_file_path})
        self.unitcell_visualizer.visualize_unitcell()

    @pyqtSlot()
    def update_visualization(self):
        """Update the coordinate visualization when vectors change."""
        try:
            # Get current values
            roll = self.roll_input.value()
            pitch = self.pitch_input.value()
            yaw = self.yaw_input.value()

            # Validate values are within range
            if not (
                -180 <= roll <= 180 and -180 <= pitch <= 180 and -180 <= yaw <= 180
            ):
                # Reset to default values if invalid
                self.roll_input.setValue(0.0)
                self.pitch_input.setValue(0.0)
                self.yaw_input.setValue(0.0)
                roll, pitch, yaw = 0.0, 0.0, 0.0

            # Update the visualizer
            self.visualizer.initialize(
                {
                    **self._effective_lattice_params(),
                    "roll": roll,
                    "pitch": pitch,
                    "yaw": yaw,
                }
            )
            self.visualizer.visualize_lab_system()
        except Exception as e:
            raise e

    def _current_ub_data(self):
        """The list[dict] of diffraction measurements behind the currently
        applied Euler angles, for the `ub_data` application parameter --
        or None if there is no still-applied, still-valid fit.

        Deliberately reads `self._applied_ub_result`, NOT
        `self._ub_session.last_result`: the session's last_result is a
        draft/candidate that persists across Cancel purely so the dialog can
        restore it on reopen -- it must never be exported just because it
        was calculated. Only an explicit Apply-and-Close sets
        `self._applied_ub_result` (see `open_diffraction_test_dialog`), and
        `_invalidate_ub_session` clears it (and resets the Euler fields)
        whenever the lattice/CIF changes or Reset is used, so a stale
        orientation can never silently linger.
        """
        result = self._applied_ub_result
        if result is None or not result.valid:
            return None
        current_lattice = self._effective_lattice_params()
        if result.lattice_params != current_lattice:
            return None  # defense in depth; _invalidate_ub_session should already have cleared this
        return [m.to_dict() for m in result.measurements]

    @pyqtSlot()
    def initialize(self):
        """Initialize the application with the provided parameters.

        For a CIF-derived structure, a/b/c/alpha/beta/gamma and cif_file
        come from the accepted StructureSource (full precision, and the
        immutable session snapshot path), not from these display widgets --
        the widgets are read-only in that case and exist for display only.
        Manual-mode values are read straight from the (editable) widgets.
        """
        try:
            source = self.controller.structure_source if self.controller else None
            cif_file = source.effective_path if (source is not None and source.source_kind == "cif") else None

            params = {
                **self._effective_lattice_params(),
                "energy": self.energy_input.value(),
                "wavevector": self.wavevector_input.value(),
                "wavelength": self.wavelength_input.value(),
                "cif_file": cif_file,
                "roll": self.roll_input.value(),
                "pitch": self.pitch_input.value(),
                "yaw": self.yaw_input.value(),
                "ub_data": self._current_ub_data(), # angles and HKL that were used to calculate the orientation from diffraction tests
            }

            # Calls AppController.apply_parameters() directly (a plain
            # synchronous method call) rather than relying solely on
            # `initialized.emit(params)` -- PyQt5 does not propagate an
            # exception raised inside a connected slot back through the
            # emitting call (verified: it goes to sys.excepthook instead,
            # and emit() returns normally), so a failure inside
            # apply_parameters() previously never reached this method's own
            # except block below. `initialized` is still emitted afterward
            # so any other interested listener still sees success.
            if self.controller is not None:
                self.controller.apply_parameters(params)
            self.initialized.emit(params)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error initializing parameters: {str(e)}"
            )

    @pyqtSlot()
    def on_energy_changed(self):
        """Update wavelength when energy changes."""
        try:
            # Block signals to prevent infinite loop
            self.wavelength_input.blockSignals(True)
            self.wavevector_input.blockSignals(True)
            # Convert energy to wavelength
            wavelength = self.unit_converter.ev_to_angstrom(self.energy_input.value())
            self.wavelength_input.setValue(wavelength)
            wavevector = 2 * 3.1415926 / wavelength
            self.wavevector_input.setValue(wavevector)
            # Unblock signals
            self.wavelength_input.blockSignals(False)
            self.wavevector_input.blockSignals(False)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Error converting energy: {str(e)}")

    @pyqtSlot()
    def on_wavelength_changed(self):
        """Update energy when wavelength changes."""
        try:
            # Block signals to prevent infinite loop
            self.energy_input.blockSignals(True)
            self.wavevector_input.blockSignals(True)
            # Convert wavelength to energy
            wavelength_value = self.wavelength_input.value()
            energy = self.unit_converter.angstrom_to_ev(wavelength_value)
            self.energy_input.setValue(energy)
            wavevector = 2 * 3.1415926 / wavelength_value
            self.wavevector_input.setValue(wavevector)
            # Unblock signals
            self.energy_input.blockSignals(False)
            self.wavevector_input.blockSignals(False)
        except Exception as e:
            QMessageBox.warning(
                self, "Warning", f"Error converting wavelength: {str(e)}"
            )
    @pyqtSlot()
    def on_wavevector_changed(self):
        """Update energy and wavelength when wavevector changes."""
        try:
            # Block signals to prevent infinite loop
            self.energy_input.blockSignals(True)
            self.wavelength_input.blockSignals(True)
            # Convert wavevector to energy
            wavelength = 2 * 3.1415926 / self.wavevector_input.value()
            self.wavelength_input.setValue(wavelength)
            energy = self.unit_converter.angstrom_to_ev(wavelength)
            self.energy_input.setValue(energy)
            # Unblock signals
            self.energy_input.blockSignals(False)
            self.wavelength_input.blockSignals(False)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Error converting wavevector: {str(e)}")

    def reset_inputs(self):
        """Return the setup view to a clean, no-structure state.

        Shares its UI-reset logic with the "Remove CIF" action via
        `on_structure_changed(None)` -- AppController.reset_parameters()
        clears `structure_source`/`parameters` and invalidates every feature
        before calling this, so the two only differ in who initiated them.
        """
        self.on_structure_changed(None)
