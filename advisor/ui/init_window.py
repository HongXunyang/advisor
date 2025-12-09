#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDoubleSpinBox,
    QGroupBox,
    QMessageBox,
    QFileDialog,
)
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent

from advisor.domain import UnitConverter
from advisor.ui.utils import readcif
from advisor.ui.visualizers import CoordinateVisualizer, UnitcellVisualizer


class DragDropLineEdit(QLineEdit):
    """Custom QLineEdit that accepts drag and drop events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Drag and drop CIF file here or click Browse...")
        self.setReadOnly(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().endswith(".cif"):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.endswith(".cif"):
                self.setText(file_path)
                self.textChanged.emit(file_path)


class DragDropGroupBox(QGroupBox):
    """QGroupBox that accepts CIF file drag-and-drop anywhere in the panel.

    When a valid CIF is dropped, it will update the target line edit.
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)
        self.setAcceptDrops(True)
        self._target_line_edit: QLineEdit = None

    def set_target_line_edit(self, line_edit: QLineEdit):
        self._target_line_edit = line_edit

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().endswith(".cif"):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        file_path = urls[0].toLocalFile()
        if file_path.endswith(".cif") and self._target_line_edit is not None:
            # Update target line edit; it will emit textChanged and trigger parsing
            self._target_line_edit.setText(file_path)
            self._target_line_edit.textChanged.emit(file_path)


class InitWindow(QWidget):
    """Initialization window for setting up lattice parameters."""

    initialized = pyqtSignal(dict)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.unit_converter = UnitConverter()
        self._lattice_locked = False
        self._accepted_cif_path = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI components."""
        layout = QGridLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(40)

        # Group box for lattice parameters
        lattice_group = QGroupBox("Lattice Parameters")
        lattice_layout = QGridLayout(lattice_group)

        # Lattice constants (left column)
        self.a_input = QDoubleSpinBox()
        self.a_input.setRange(0.1, 100.0)
        self.a_input.setValue(5.0)
        self.a_input.setSuffix(" Å")
        lattice_layout.addWidget(QLabel("a:"), 0, 0)
        lattice_layout.addWidget(self.a_input, 0, 1)

        self.b_input = QDoubleSpinBox()
        self.b_input.setRange(0.1, 100.0)
        self.b_input.setValue(5.0)
        self.b_input.setSuffix(" Å")
        lattice_layout.addWidget(QLabel("b:"), 1, 0)
        lattice_layout.addWidget(self.b_input, 1, 1)

        self.c_input = QDoubleSpinBox()
        self.c_input.setRange(0.1, 100.0)
        self.c_input.setValue(5.0)
        self.c_input.setSuffix(" Å")
        lattice_layout.addWidget(QLabel("c:"), 2, 0)
        lattice_layout.addWidget(self.c_input, 2, 1)

        # Lattice angles (right column)
        self.alpha_input = QDoubleSpinBox()
        self.alpha_input.setRange(1.0, 179.0)
        self.alpha_input.setValue(90.0)
        self.alpha_input.setSuffix(" °")
        self.alpha_input.valueChanged.connect(self.update_visualization)
        lattice_layout.addWidget(QLabel("α:"), 0, 2)
        lattice_layout.addWidget(self.alpha_input, 0, 3)

        self.beta_input = QDoubleSpinBox()
        self.beta_input.setRange(1.0, 179.0)
        self.beta_input.setValue(90.0)
        self.beta_input.setSuffix(" °")
        self.beta_input.valueChanged.connect(self.update_visualization)
        lattice_layout.addWidget(QLabel("β:"), 1, 2)
        lattice_layout.addWidget(self.beta_input, 1, 3)

        self.gamma_input = QDoubleSpinBox()
        self.gamma_input.setRange(1.0, 179.0)
        self.gamma_input.setValue(90.0)
        self.gamma_input.setSuffix(" °")
        self.gamma_input.valueChanged.connect(self.update_visualization)
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

        # Group box for Euler angles
        euler_group = QGroupBox("Euler Angles")
        euler_layout = QFormLayout(euler_group)

        self.roll_input = QDoubleSpinBox()
        self.roll_input.setObjectName("eulerAngleSpinBox")
        self.roll_input.setRange(-180.0, 180.0)
        self.roll_input.setValue(0.0)
        self.roll_input.setSuffix(" °")
        self.roll_input.setToolTip("Rotation about the new X axis")
        self.roll_input.valueChanged.connect(self.update_visualization)
        euler_layout.addRow("Roll:", self.roll_input)

        self.pitch_input = QDoubleSpinBox()
        self.pitch_input.setObjectName("eulerAngleSpinBox")
        self.pitch_input.setRange(-180.0, 180.0)
        self.pitch_input.setValue(0.0)
        self.pitch_input.setSuffix(" °")
        self.pitch_input.setToolTip("Rotation about the new Y axis")
        self.pitch_input.valueChanged.connect(self.update_visualization)
        euler_layout.addRow("Pitch:", self.pitch_input)

        self.yaw_input = QDoubleSpinBox()
        self.yaw_input.setObjectName("eulerAngleSpinBox")
        self.yaw_input.setRange(-180.0, 180.0)
        self.yaw_input.setValue(0.0)
        self.yaw_input.setSuffix(" °")
        self.yaw_input.setToolTip("Rotation about the original Z axis")
        self.yaw_input.valueChanged.connect(self.update_visualization)
        euler_layout.addRow("Yaw:", self.yaw_input)

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

        # File input area
        file_group = DragDropGroupBox("Crystal Structure File")
        file_layout = QGridLayout(file_group)

        self.file_path_input = DragDropLineEdit()
        self.file_path_input.textChanged.connect(self.on_cif_file_changed)
        file_layout.addWidget(self.file_path_input, 0, 0)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_cif_file)
        file_layout.addWidget(browse_button, 0, 1)

        # Allow dropping on the entire group box
        file_group.set_target_line_edit(self.file_path_input)

        # Add file group to main layout at (1,0) spanning 1 column
        layout.addWidget(file_group, 1, 0, 1, 1)

        # Initialize button
        initialize_button = QPushButton("Initialize")
        initialize_button.clicked.connect(self.initialize)
        # Add initialize button at (2,0) spanning 1 column
        layout.addWidget(initialize_button, 2, 0, 1, 1)

        # Add spacer
        layout.setRowStretch(3, 1)

    @pyqtSlot()
    def browse_cif_file(self):
        """Browse for CIF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CIF File", "", "CIF Files (*.cif);;All Files (*)"
        )

        if file_path:
            self.file_path_input.setText(file_path)
            # on_cif_file_changed will be triggered by textChanged

    def set_lattice_inputs_enabled(self, enabled: bool):
        """Enable/disable lattice parameter inputs (a,b,c,alpha,beta,gamma)."""
        self.a_input.setEnabled(enabled)
        self.b_input.setEnabled(enabled)
        self.c_input.setEnabled(enabled)
        self.alpha_input.setEnabled(enabled)
        self.beta_input.setEnabled(enabled)
        self.gamma_input.setEnabled(enabled)

    @pyqtSlot(str)
    def on_cif_file_changed(self, file_path: str):
        """Handle CIF file path changes: parse CIF and apply lattice params.

        Once a CIF is successfully applied, lattice inputs are locked for the session.
        """
        try:
            if self._lattice_locked:
                # Prevent changing CIF after lock
                if self._accepted_cif_path and file_path != self._accepted_cif_path:
                    QMessageBox.warning(
                        self,
                        "Lattice Parameters Locked",
                        "Lattice parameters are locked from a previously accepted CIF. "
                        "Restart the application to change the CIF.",
                    )
                    # revert displayed path
                    # Block signal to avoid recursion
                    self.file_path_input.blockSignals(True)
                    self.file_path_input.setText(self._accepted_cif_path)
                    self.file_path_input.blockSignals(False)
                return

            # Empty path - user cleared the field; keep inputs editable
            if not file_path:
                self._accepted_cif_path = None
                self._lattice_locked = False
                self.set_lattice_inputs_enabled(True)
                # Clear unit cell visualization
                self.clear_unitcell_visualization()
                return

            # Parse CIF using custom readcif function
            cif = readcif(file_path)
            if not cif or len(cif.keys()) == 0:
                raise ValueError("No data found in CIF file")

            def parse_numeric(value) -> float:
                s = str(value).strip()
                if "(" in s:
                    s = s.split("(")[0]
                return float(s)

            def get_float(key: str) -> float:
                value = cif.get(key)
                if value is None:
                    raise KeyError(f"Missing required CIF field: {key}")
                return parse_numeric(value)

            a = get_float("_cell_length_a")
            b = get_float("_cell_length_b")
            c = get_float("_cell_length_c")
            alpha = get_float("_cell_angle_alpha")
            beta = get_float("_cell_angle_beta")
            gamma = get_float("_cell_angle_gamma")

            # Basic validation (units assumed Angstroms and degrees)
            if min(a, b, c) <= 0:
                raise ValueError("Cell lengths must be positive")
            for ang, name in [(alpha, "alpha"), (beta, "beta"), (gamma, "gamma")]:
                if not (0.0 < ang < 180.0):
                    raise ValueError(
                        f"Cell angle {name} must be between 0 and 180 degrees"
                    )

            # Apply to UI and lock
            self.apply_cif_parameters(a, b, c, alpha, beta, gamma)
            self._lattice_locked = True
            self._accepted_cif_path = file_path
            self.set_lattice_inputs_enabled(False)
            
            # Update unit cell visualizer with the CIF file
            self.update_unitcell_visualization(file_path)
            
            QMessageBox.information(
                self,
                "CIF Loaded",
                "Lattice parameters have been loaded from the CIF and inputs are now locked.",
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Invalid CIF",
                f"Failed to read lattice parameters from CIF: {str(e)}",
            )
            # clear text and keep inputs editable
            self.file_path_input.blockSignals(True)
            self.file_path_input.clear()
            self.file_path_input.blockSignals(False)
            self._accepted_cif_path = None
            self._lattice_locked = False
            self.set_lattice_inputs_enabled(True)

    def apply_cif_parameters(
        self, a: float, b: float, c: float, alpha: float, beta: float, gamma: float
    ):
        """Set lattice parameter inputs from parsed CIF values and refresh visualization."""
        # Block signals to avoid multiple redraws
        self.a_input.blockSignals(True)
        self.b_input.blockSignals(True)
        self.c_input.blockSignals(True)
        self.alpha_input.blockSignals(True)
        self.beta_input.blockSignals(True)
        self.gamma_input.blockSignals(True)

        self.a_input.setValue(a)
        self.b_input.setValue(b)
        self.c_input.setValue(c)
        self.alpha_input.setValue(alpha)
        self.beta_input.setValue(beta)
        self.gamma_input.setValue(gamma)

        self.a_input.blockSignals(False)
        self.b_input.blockSignals(False)
        self.c_input.blockSignals(False)
        self.alpha_input.blockSignals(False)
        self.beta_input.blockSignals(False)
        self.gamma_input.blockSignals(False)

        # Update visualization with new parameters
        self.update_visualization()

    def update_unitcell_visualization(self, cif_file_path: str):
        """Update the unit cell visualizer with a new CIF file."""
        try:
            self.unitcell_visualizer.set_parameters({"cif_file": cif_file_path})
            self.unitcell_visualizer.visualize_unitcell()
        except Exception as e:
            print(f"Error updating unit cell visualization: {e}")

    def clear_unitcell_visualization(self):
        """Clear the unit cell visualization."""
        try:
            self.unitcell_visualizer.axes.clear()
            self.unitcell_visualizer.axes.set_facecolor("white")
            self.unitcell_visualizer.axes.set_axis_off()
            self.unitcell_visualizer.draw()
        except Exception as e:
            print(f"Error clearing unit cell visualization: {e}")

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
                    "a": self.a_input.value(),
                    "b": self.b_input.value(),
                    "c": self.c_input.value(),
                    "alpha": self.alpha_input.value(),
                    "beta": self.beta_input.value(),
                    "gamma": self.gamma_input.value(),
                    "roll": roll,
                    "pitch": pitch,
                    "yaw": yaw,
                }
            )
            self.visualizer.visualize_lab_system()
        except Exception as e:
            raise e

    @pyqtSlot()
    def initialize(self):
        """Initialize the application with the provided parameters."""
        try:
            # Get parameters
            params = {
                "a": self.a_input.value(),
                "b": self.b_input.value(),
                "c": self.c_input.value(),
                "alpha": self.alpha_input.value(),
                "beta": self.beta_input.value(),
                "gamma": self.gamma_input.value(),
                "energy": self.energy_input.value(),
                "cif_file": (
                    self.file_path_input.text() if self.file_path_input.text() else None
                ),
                "roll": self.roll_input.value(),
                "pitch": self.pitch_input.value(),
                "yaw": self.yaw_input.value(),
            }

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
        """Clear CIF lock and re-enable lattice inputs."""
        self._lattice_locked = False
        self._accepted_cif_path = None
        self.file_path_input.blockSignals(True)
        self.file_path_input.clear()
        self.file_path_input.blockSignals(False)
        self.set_lattice_inputs_enabled(True)
        self.clear_unitcell_visualization()
        self.update_visualization()
