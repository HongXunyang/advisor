#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
import matplotlib
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QDoubleSpinBox,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QFileDialog,
    QMessageBox,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSlot, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QBrush

# Tell matplotlib to render plots using the Qt5 framework with the Agg backend for drawing
matplotlib.use("Qt5Agg")

from advisor.features.scattering_geometry.domain import BrillouinCalculator
from advisor.ui.tab_interface import TabInterface
from advisor.ui.visualizers import (
    ScatteringVisualizer,
    UnitcellVisualizer,
    HKLScan2DVisualizer,
)
from advisor.ui.tips import Tips, set_tip
from .components import (
    HKLScanControls,
    HKLScanResultsTable,
    HKAnglesControls,
    HKAnglesResultsWidget,
    AnglesToHKLControls,
    AnglesToHKLResults,
    HKLToAnglesControls,
    HKLToAnglesResultsWidget,
)
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
                # Emit the textChanged signal to notify parent
                self.textChanged.emit(file_path)


class ScatteringGeometryTab(TabInterface):
    """Tab for calculating Brillouin zone / scattering geometry parameters."""

    def __init__(self, controller=None, calculator=None):
        self.controller = controller
        # Backend instance provided by controller
        self.calculator = calculator or BrillouinCalculator()
        self.angles_to_hkl_visualizer = ScatteringVisualizer()  # first subtab
        self.hkl_to_angles_visualizer = ScatteringVisualizer()  # second subtab
        self.hk_fixed_tth_visualizer = ScatteringVisualizer()  # third subtab
        
        # Unit cell visualizers for each subtab
        self.angles_to_hkl_unitcell_viz = UnitcellVisualizer()
        self.hkl_to_angles_unitcell_viz = UnitcellVisualizer()
        self.hk_fixed_tth_unitcell_viz = UnitcellVisualizer()
        self.funtional_objects = [
            self.calculator,
            self.angles_to_hkl_visualizer,
            self.hkl_to_angles_visualizer,
            self.hk_fixed_tth_visualizer,
        ]  # group up the funtional objects and initailize them later on
        self.tips = Tips()

        # Store parameters for display
        self.parameters = None

        # Initialize UI
        main_window = controller.app_controller.main_window if controller else None
        super().__init__(controller=controller, main_window=main_window)

        params = controller.app_controller.get_parameters() if controller else None
        if params:
            self.set_parameters(params)
        # Set window title
        self.setWindowTitle("Scattering Geometry")

    def init_ui(self):
        """Initialize UI components."""
        # Create tab widget for input methods
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget, 0, 0)  # Back to (0,0) position

        # Create and add parameter header to the right
        self._create_parameter_header()

        # Create tabs for different functionalities
        self._create_angles_to_hkl_tab()
        self._create_hkl_to_angles_tab()
        self._create_hk_to_angles_tth_fixed_tab()
        self._create_hkl_scan_tab()  # Add the new HKL scan tab

    def _create_parameter_header(self):
        """Create parameter display header."""
        # Create main header frame
        header_frame = QFrame()
        header_frame.setObjectName("parameterPanel")
        header_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        header_frame.setLineWidth(1)
        header_frame.setFixedWidth(200)  # Reduced from 280 to 220 for narrower panel

        # Create header layout - vertical for sidebar
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(15)  # Reduced from 25 to 15 for more compact layout

        # Crystal Structure section
        crystal_title = QLabel("Crystal Structure")
        crystal_title.setObjectName("parameterSectionTitle")
        header_layout.addWidget(crystal_title)

        self.crystal_info_label = QLabel(
            "a = -- Å\nb = -- Å\nc = -- Å\nα = --°\nβ = --°\nγ = --°"
        )
        self.crystal_info_label.setObjectName("parameterText")
        self.crystal_info_label.setWordWrap(True)
        header_layout.addWidget(self.crystal_info_label)

        # X-ray section
        xray_title = QLabel("X-ray Parameters")
        xray_title.setObjectName("parameterSectionTitle")
        header_layout.addWidget(xray_title)

        self.xray_info_label = QLabel("Energy: -- eV\nλ: -- Å\n|k|: -- Å⁻¹")
        self.xray_info_label.setObjectName("parameterText")
        self.xray_info_label.setWordWrap(True)
        header_layout.addWidget(self.xray_info_label)

        # Add stretch to push edit button to the bottom
        header_layout.addStretch()

        # Edit button
        edit_button = QPushButton("Reset Parameters")
        edit_button.setObjectName("editParametersButton")
        edit_button.setToolTip("Return to parameter initialization window")
        edit_button.clicked.connect(self._edit_parameters)
        edit_button.setFixedHeight(35)  # Reduced from 45 to 35
        header_layout.addWidget(edit_button)

        # Add header to main layout - right side
        self.layout.addWidget(header_frame, 0, 1)

        # Set column stretch so tab widget takes most space
        self.layout.setColumnStretch(0, 5)  # Tab widget gets more space
        self.layout.setColumnStretch(1, 1)  # Header gets less space

    def set_parameters(self, params: dict):
        """Set parameters from global settings."""
        if not params:
            return
        # Store parameters
        self.parameters = params

        # Update header display
        self._update_parameter_display()

        # Initialize functional objects
        for obj in self.funtional_objects:
            obj.initialize(params=params)

        # Initialize unit cell visualizers if CIF file is provided
        cif_file = params.get('cif_file')
        if cif_file:
            self._update_unitcell_visualizers(cif_file)
            
        # HKL scan visualizer uses trajectory-only mode, no structure factor calculator needed


    def _update_unitcell_visualizers(self, cif_file_path: str):
        """Update all unit cell visualizers with the CIF file."""
        try:
            unit_cell_vizs = [
                self.angles_to_hkl_unitcell_viz,
                self.hkl_to_angles_unitcell_viz,
                self.hk_fixed_tth_unitcell_viz
            ]
            
            for viz in unit_cell_vizs:
                viz.set_parameters({"cif_file": cif_file_path})
                viz.visualize_unitcell()
                
        except Exception as e:
            print(f"**Error** updating unit cell visualizers: {e}")

    def _update_parameter_display(self):
        """Update the parameter display in the header."""
        if not self.parameters:
            return

        # Update crystal structure display - vertical format
        crystal_text = (
            f"a = {self.parameters.get('a', 0):.2f} Å\n"
            f"b = {self.parameters.get('b', 0):.2f} Å\n"
            f"c = {self.parameters.get('c', 0):.2f} Å\n"
            f"α = {self.parameters.get('alpha', 0):.1f}°\n"
            f"β = {self.parameters.get('beta', 0):.1f}°\n"
            f"γ = {self.parameters.get('gamma', 0):.1f}°"
        )
        self.crystal_info_label.setText(crystal_text)

        # Update X-ray display - vertical format
        energy = self.parameters.get("energy", 0)
        # Convert eV to Angstrom: λ = hc/E = 12398.4 / E(eV)
        wavelength = 12398.4 / energy if energy > 0 else 0
        wavevector = 2 * 3.1415926 / wavelength if wavelength else 0
        xray_text = (
            f"Energy: {energy:.2f} eV\n"
            f"λ: {wavelength:.3f} Å\n"
            f"|k|: {wavevector:.3f} Å⁻¹"
        )
        self.xray_info_label.setText(xray_text)

    @pyqtSlot()
    def _edit_parameters(self):
        """Return to parameter initialization window."""
        if self.controller:
            self.controller.app_controller.reset_parameters()

    def _set_tip(self, widget, name):
        """Set the tooltip and status tip for a widget by the name"""
        set_tip(widget, self.tips.tip(name))

    def _create_angles_to_hkl_tab(self):
        """Create tab for angles to HKL calculation."""
        angles_tab = QWidget()
        angles_layout = QHBoxLayout(angles_tab)

        # Left column - Controls and Results
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)

        # Create controls widget
        self.angles_to_hkl_controls = AnglesToHKLControls(parent=self)
        self.angles_to_hkl_controls.calculateClicked.connect(self.calculate_hkl)
        self.angles_to_hkl_controls.anglesChanged.connect(self.calculate_hkl)  # Auto-calculate on angle change
        left_layout.addWidget(self.angles_to_hkl_controls)

        # Create results widget
        self.angles_to_hkl_results = AnglesToHKLResults(parent=self)
        left_layout.addWidget(self.angles_to_hkl_results)

        left_layout.addStretch()  # Add stretch to push content to top

        # Right column - Visualizers
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Scattering visualizer
        self.angles_to_hkl_visualizer.visualize_lab_system()
        self.angles_to_hkl_visualizer.visualize_scattering_geometry()
        right_layout.addWidget(self.angles_to_hkl_visualizer)
        
        # Unit cell visualizer
        right_layout.addWidget(self.angles_to_hkl_unitcell_viz)

        # Add columns to main layout
        angles_layout.addWidget(left_column, 1)  # Left column takes 1 part
        angles_layout.addWidget(right_column, 1.5)  # Right column takes 1.5 parts

        # Add to tab widget
        self.tab_widget.addTab(angles_tab, "Angles → HKL")

    def _create_hkl_to_angles_tab(self):
        """Create tab for HKL to angles calculation."""
        hkl_tab = QWidget()
        hkl_layout = QHBoxLayout(hkl_tab)

        # Left column - Controls and Results
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)

        # Create controls widget
        self.hkl_to_angles_controls = HKLToAnglesControls(parent=self)
        self.hkl_to_angles_controls.calculateClicked.connect(self.calculate_angles)
        left_layout.addWidget(self.hkl_to_angles_controls)

        # Create results widget
        self.hkl_to_angles_results = HKLToAnglesResultsWidget(parent=self)
        # self.hkl_to_angles_results.solutionSelected.connect(self.on_angle_solution_selected)
        left_layout.addWidget(self.hkl_to_angles_results)

        left_layout.addStretch()  # Add stretch to push content to top

        # Right column - Visualizers
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Scattering visualizer
        self.hkl_to_angles_visualizer.visualize_lab_system()
        self.hkl_to_angles_visualizer.visualize_scattering_geometry()
        right_layout.addWidget(self.hkl_to_angles_visualizer)
        
        # Unit cell visualizer
        right_layout.addWidget(self.hkl_to_angles_unitcell_viz)

        # Add columns to main layout
        hkl_layout.addWidget(left_column, 1)  # Left column takes 1 part
        hkl_layout.addWidget(right_column, 1.5)  # Right column takes 1.5 parts

        # Add to tab widget
        self.tab_widget.addTab(hkl_tab, "HKL → Angles")

    def _create_hk_to_angles_tth_fixed_tab(self):
        """Create tab for HK to angles calculation with fixed tth."""
        hk_tab = QWidget()
        hk_layout = QHBoxLayout(hk_tab)

        # Left column - Controls and Results
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)

        # Create controls widget
        self.hk_angles_controls = HKAnglesControls(parent=self)
        self.hk_angles_controls.calculateClicked.connect(self.calculate_angles_tth_fixed)
        left_layout.addWidget(self.hk_angles_controls)

        # Create results widget
        self.hk_angles_results = HKAnglesResultsWidget(parent=self)
        # self.hk_angles_results.solutionSelected.connect(self.on_angle_solution_selected_tth)
        left_layout.addWidget(self.hk_angles_results)

        left_layout.addStretch()  # Add stretch to push content to top

        # Right column - Visualizers
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Scattering visualizer
        self.hk_fixed_tth_visualizer.visualize_lab_system()
        self.hk_fixed_tth_visualizer.visualize_scattering_geometry()
        right_layout.addWidget(self.hk_fixed_tth_visualizer)
        
        # Unit cell visualizer
        right_layout.addWidget(self.hk_fixed_tth_unitcell_viz)

        # Add columns to main layout
        hk_layout.addWidget(left_column, 1)  # Left column takes 1 part
        hk_layout.addWidget(right_column, 1.5)  # Right column takes 1.5 parts

        # Add to tab widget
        self.tab_widget.addTab(hk_tab, "HK to Angles | tth fixed")

    def _create_hkl_scan_tab(self):
        """Create tab for scanning a range of HKL values."""
        scan_tab = QWidget()
        scan_layout = QHBoxLayout(scan_tab)

        # Create controls widget
        self.hkl_scan_controls = HKLScanControls(parent=self)
        self.hkl_scan_controls.calculateClicked.connect(self.calculate_hkl_scan)
        scan_layout.addWidget(self.hkl_scan_controls, 1)

        # Create results table & 2d visualization
        results_layout = QVBoxLayout()

        # Results table
        self.hkl_scan_results_table = HKLScanResultsTable(parent=self)
        results_layout.addWidget(self.hkl_scan_results_table, 1)
        
        # 2D visualizer section
        self.hkl_scan_visualizer = HKLScan2DVisualizer(parent=self)
        results_layout.addWidget(self.hkl_scan_visualizer, 1)

        # Add to layout
        scan_layout.addLayout(results_layout, 2)
        # Add to tab widget
        self.tab_widget.addTab(scan_tab, "HKL Scan | tth fixed")

    @pyqtSlot()
    def calculate_hkl_scan(self):
        """Calculate angles for a range of HKL values."""
        try:
            # Check if calculator is initialized
            if not self.calculator.is_initialized():
                QMessageBox.warning(
                    self, "Warning", "Please initialize the calculator first!"
                )
                self.tab_widget.setCurrentIndex(0)
                return

            # Get parameters for scan
            params = self.hkl_scan_controls.get_scan_parameters()

            # Calculate angles for the scan
            result = self.calculator.calculate_angles_tth_fixed_scan(
                tth=params["tth"],
                start_points=params["start_points"],
                end_points=params["end_points"],
                num_points=params["num_points"],
                deactivated_index=params["deactivated_index"],
                fixed_angle_name=params["fixed_angle_name"],
                fixed_angle=params["fixed_angle"],
            )

            # Check for success
            success = result.get("success", False)
            if not success:
                QMessageBox.warning(
                    self, "Warning", result.get("error", "Unknown error")
                )
                return

            # Display results in table
            self.hkl_scan_results_table.display_results(result)
            
            # Update visualization
            self.update_hkl_visualization(result)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"**Error** calculating HKL scan: {str(e)}")

    @pyqtSlot()
    def update_hkl_visualization(self, scan_results=None):
        """Update the HKL scan visualization with auto-detected ranges and results."""
        try:
            # Structure factor calculator not needed for trajectory-only visualization
            
            # Use the provided scan results or the last stored results
            if scan_results is None:
                scan_results = getattr(self.hkl_scan_visualizer, 'last_scan_results', None)
            
            if scan_results:
                # Determine plane type from deactivated index
                deactivated_index = scan_results.get("deactivated_index", "L")
                if deactivated_index == "L":
                    plane_type = "HK"
                elif deactivated_index == "K":
                    plane_type = "HL"
                elif deactivated_index == "H":
                    plane_type = "KL"
                else:
                    plane_type = "HK"  # Default
                
                # Visualize results (ranges will be auto-detected)
                self.hkl_scan_visualizer.visualize_results(scan_results, plane_type)
            else:
                # No scan results yet, just clear the plot
                self.hkl_scan_visualizer.clear_plot()
                
        except Exception as e:
            print(f"**Error** updating HKL visualization: {e}")

    @pyqtSlot()
    def browse_cif_file(self):
        """Browse for CIF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CIF File", "", "CIF Files (*.cif);;All Files (*)"
        )

        if file_path:
            self.file_path_input.setText(file_path)

    @pyqtSlot()
    def calculate_hkl(self):
        """Calculate HKL from angles."""
        try:
            # Check if calculator is initialized
            if not self.calculator.is_initialized():
                QMessageBox.warning(
                    self, "Warning", "Please initialize the calculator first!"
                )
                self.tab_widget.setCurrentIndex(0)
                return

            # Get parameters from the controls component
            params = self.angles_to_hkl_controls.get_calculation_parameters()
            
            # Calculate HKL
            result = self.calculator.calculate_hkl(
                tth=params["tth"],
                theta=params["theta"],
                phi=params["phi"],
                chi=params["chi"],
            )
            roll, pitch, yaw = self.parameters["roll"], self.parameters["pitch"], self.parameters["yaw"]
            success = result.get("success", False)
            if not success:
                QMessageBox.warning(
                    self, "Warning", result.get("error", "Unknown error")
                )
                return
            
            # Display results using the new results widget
            self.angles_to_hkl_results.display_results(result)

            # Update visualization
            self.angles_to_hkl_visualizer.visualize_lab_system(
                chi=params["chi"], phi=params["phi"], plot_k_basis=True, plot_basis=False
            )
            self.angles_to_hkl_visualizer.visualize_scattering_geometry(
                scattering_angles=result
            )

            self.angles_to_hkl_unitcell_viz.visualize_unitcell()
            self.angles_to_hkl_unitcell_viz.visualize_scattering_geometry(
                scattering_angles=result
            ) 

        except Exception as e:
            QMessageBox.critical(self, "Error", f"**Error** calculating HKL: {str(e)}")
        
    @pyqtSlot()
    def _update_fixed_angle_ui(self):
        """Update UI based on which angle is fixed."""
        is_chi_fixed = self.fix_chi_radio.isChecked()
        self.chi_input.setEnabled(is_chi_fixed)
        self.phi_input.setEnabled(not is_chi_fixed)

    @pyqtSlot()
    def calculate_angles(self):
        """Calculate angles from HKL."""
        if not self.calculator.is_initialized():
            QMessageBox.warning(
                self, "Warning", "Please initialize the calculator first!"
            )
            self.tab_widget.setCurrentIndex(0)
            return

        # Get parameters from the controls component
        params = self.hkl_to_angles_controls.get_calculation_parameters()

        # Calculate angles
        result = self.calculator.calculate_angles(
            H=params["H"],
            K=params["K"],
            L=params["L"],
            fixed_angle=params["fixed_angle_value"],
            fixed_angle_name=params["fixed_angle_name"],
        )
        if not result["success"]:
            QMessageBox.warning(
                self, "Warning", result.get("error", "No solution found")
            )
            return
        self.hkl_to_angles_results.display_results(result)
        # Update visualization with the first solution
        self.hkl_to_angles_visualizer.visualize_lab_system(
            is_clear=True, chi=result["chi"], phi=result["phi"], plot_basis=False, plot_k_basis=True
        )
        self.hkl_to_angles_visualizer.visualize_scattering_geometry(
            scattering_angles=result, is_clear=False
        )
        self.hkl_to_angles_unitcell_viz.visualize_unitcell()
        self.hkl_to_angles_unitcell_viz.visualize_scattering_geometry(
            scattering_angles=result
        ) 
    @pyqtSlot()
    def calculate_angles_tth_fixed(self):
        """Calculate angles from HK with fixed tth."""
        # Check if calculator is initialized
        if not self.calculator.is_initialized():
            QMessageBox.warning(
                self, "Warning", "Please initialize the calculator first!"
            )
            self.tab_widget.setCurrentIndex(0)
            return

        # Get parameters from the controls component
        params = self.hk_angles_controls.get_calculation_parameters()
        
        # Extract values for calculation
        tth = params["tth"]
        H = params["H"]
        K = params["K"]
        L = params["L"]
        fixed_index = params["fixed_index"]
        fixed_angle_name = params["fixed_angle_name"]
        fixed_angle_value = params["fixed_angle_value"]

        # Calculate angles
        result = self.calculator.calculate_angles_tth_fixed(
            tth=tth,
            H=H,
            K=K,
            L=L,
            fixed_angle_name=fixed_angle_name,
            fixed_angle=fixed_angle_value,
        )
        print("result", result)
        if not result["success"]:
            QMessageBox.warning(
                self, "Warning", result.get("error", "No solution found")
            )
            return
        self.hk_angles_results.display_results(result)

        # Update visualization with the first solution
        self.hk_fixed_tth_visualizer.visualize_lab_system(
            is_clear=True, chi=result["chi"], phi=result["phi"], plot_basis=False, plot_k_basis=True
        )
        self.hk_fixed_tth_visualizer.visualize_scattering_geometry(
            scattering_angles=result, is_clear=False
        )
        self.hk_fixed_tth_unitcell_viz.visualize_unitcell()
        self.hk_fixed_tth_unitcell_viz.visualize_scattering_geometry(
            scattering_angles=result
        ) 
    @pyqtSlot()
    def on_angle_solution_selected(self, solution):
        """Handle selection of a specific angle solution from the results widget."""
        # Get HKL values from the controls component
        params = self.hkl_to_angles_controls.get_calculation_parameters()
        
        # Add HKL values to the solution for visualization
        complete_solution = dict(solution)
        complete_solution["H"] = params["H"]
        complete_solution["K"] = params["K"]
        complete_solution["L"] = params["L"]

        # Update visualization with the selected solution
        self.hkl_to_angles_visualizer.visualize_lab_system(
            is_clear=True, chi=solution["chi"], phi=solution["phi"]
        )
        self.hkl_to_angles_visualizer.visualize_scattering_geometry(
            scattering_angles=complete_solution, is_clear=False
        )

    @pyqtSlot()
    def on_angle_solution_selected_tth(self, solution):
        """Handle selection of a specific angle solution from the results widget."""
        # Get HKL values from the controls component
        params = self.hk_angles_controls.get_calculation_parameters()
        
        # Add HKL values to the solution for visualization
        complete_solution = dict(solution)
        complete_solution["H"] = params["H"] if params["H"] is not None else 0.0
        complete_solution["K"] = params["K"] if params["K"] is not None else 0.0
        complete_solution["L"] = params["L"] if params["L"] is not None else 0.0

        # Update visualization with the selected solution
        self.hk_fixed_tth_visualizer.visualize_lab_system(
            is_clear=True, chi=solution["chi"], phi=solution["phi"]
        )
        self.hk_fixed_tth_visualizer.visualize_scattering_geometry(
            scattering_angles=complete_solution, is_clear=False
        )

    @pyqtSlot()
    def clear_hkl_to_angles_results(self):
        """Clear all results from the HKL to angles table."""
        self.hkl_to_angles_results.clear_results()

    @pyqtSlot()
    def clear_hk_tth_fixed_results(self):
        """Clear all results from the HK to angles (tth fixed) table."""
        self.hk_angles_results.clear_results()

    def get_module_instance(self):
        """Get the backend module instance."""
        return self.calculator

    def get_state(self):
        """Get the current state for session saving."""
        return {
            "lattice": {
                "a": self.a_input.value(),
                "b": self.b_input.value(),
                "c": self.c_input.value(),
                "alpha": self.alpha_input.value(),
                "beta": self.beta_input.value(),
                "gamma": self.gamma_input.value(),
            },
            "energy": self.energy_input.value(),
            "file_path": self.file_path_input.text(),
            "current_tab": self.tab_widget.currentIndex(),
        }

    def set_state(self, state):
        """Restore tab state from saved session."""
        try:
            if "lattice" in state:
                lattice = state["lattice"]
                self.a_input.setValue(lattice.get("a", 5.0))
                self.b_input.setValue(lattice.get("b", 5.0))
                self.c_input.setValue(lattice.get("c", 5.0))
                self.alpha_input.setValue(lattice.get("alpha", 90.0))
                self.beta_input.setValue(lattice.get("beta", 90.0))
                self.gamma_input.setValue(lattice.get("gamma", 90.0))

            if "energy" in state:
                self.energy_input.setValue(state["energy"])

            if "file_path" in state and state["file_path"]:
                self.file_path_input.setText(state["file_path"])

            if "current_tab" in state:
                self.tab_widget.setCurrentIndex(state["current_tab"])

            return True
        except Exception:
            return False
