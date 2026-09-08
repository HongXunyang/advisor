#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
import matplotlib
from PyQt5.QtCore import QMimeData, Qt, pyqtSlot
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (QButtonGroup, QComboBox, QDoubleSpinBox,
                             QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                             QMessageBox, QPushButton, QRadioButton,
                             QTableWidget, QTableWidgetItem, QTabWidget, QSplitter,
                             QVBoxLayout, QWidget)

# Tell matplotlib to render plots using the Qt5 framework with the Agg backend for drawing
matplotlib.use("Qt5Agg")

from advisor.features.scattering_geometry.domain import BrillouinCalculator
from advisor.ui.dialogs.change_structure_dialog import ChangeStructureDialog, change_structure_icon
from advisor.ui.tab_interface import TabInterface
from advisor.ui.components.workspace_presentation import (
    control_rail, fit_atomic_preview, plot_tabs, polish_workspace,
)
from advisor.ui.tips import Tips, set_tip
from advisor.ui.visualizers import (HKLScan2DVisualizer, ScatteringVisualizer,
                                    UnitcellVisualizer)

from .components import (AnglesToHKLControls, AnglesToHKLResults,
                         HKAnglesControls, HKAnglesResultsWidget,
                         HKLScanControls, HKLScanResultsTable,
                         HKLToAnglesControls, HKLToAnglesResultsWidget)


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
        self.layout.addWidget(self.tab_widget, 0, 0)
        self.layout.setRowStretch(0, 1)

        # Keep parameters in the right-hand information panel.
        self._create_parameter_header()

        # Create tabs for different functionalities
        self._create_angles_to_hkl_tab()
        self._create_hkl_to_angles_tab()
        self._create_hk_to_angles_tth_fixed_tab()
        self._create_hkl_scan_tab()  # Add the new HKL scan tab
        polish_workspace(self)

    def _create_parameter_header(self):
        """Create parameter display header."""
        # Create main header frame
        header_frame = QFrame()
        header_frame.setObjectName("workspaceContext")
        header_frame.setFixedWidth(165)

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(12, 14, 12, 14)
        header_layout.setSpacing(12)
        crystal_title = QLabel("Crystal")
        crystal_title.setProperty("workRole", "heading")
        header_layout.addWidget(crystal_title)

        self.crystal_info_label = QLabel(
            "a = -- Å\nb = -- Å\nc = -- Å\nα = --°\nβ = --°\nγ = --°", header_frame
        )
        self.crystal_info_label.setObjectName("parameterText")
        self.crystal_info_label.setWordWrap(True)
        header_layout.addWidget(self.crystal_info_label)
        self.context_label = QLabel("Crystal and beam parameters")
        self.context_label.setTextFormat(Qt.PlainText)
        self.context_label.setParent(header_frame)
        self.context_label.hide()

        beam_title = QLabel("X-ray beam")
        beam_title.setProperty("workRole", "heading")
        header_layout.addWidget(beam_title)

        self.xray_info_label = QLabel("Energy: -- eV\nλ: -- Å\n|k|: -- Å⁻¹", header_frame)
        self.xray_info_label.setObjectName("parameterText")
        self.xray_info_label.setWordWrap(True)
        header_layout.addWidget(self.xray_info_label)
        header_layout.addStretch(1)

        details_button = QPushButton("Parameters…")
        details_button.clicked.connect(self._show_parameter_details)
        header_layout.addWidget(details_button)

        # Change structure / start over button -- opens the same dialog as
        # the toolbar/menu action, reachable from this tab too.
        change_structure_button = QPushButton("Change structure…")
        change_structure_button.setObjectName("changeStructureButton")
        change_structure_button.setToolTip("Pick a different CIF, or start over from a blank setup")
        change_structure_button.clicked.connect(self._open_change_structure_dialog)
        header_layout.addWidget(change_structure_button)

        self.layout.addWidget(header_frame, 0, 1)

        # Set column stretch so tab widget takes most space
        self.layout.setColumnStretch(0, 1)

    def _show_parameter_details(self):
        QMessageBox.information(self, "Crystal and beam parameters",
                                self.crystal_info_label.text() + "\n\n" + self.xray_info_label.text())

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

        # Initialize unit cell visualizers if a CIF file is provided AND its
        # atomic data is actually usable -- a geometry-only structure (valid
        # cell, no usable atoms) must not render Dans_Diffraction's
        # silently-fabricated default atom. Reset (no stale/fabricated
        # preview) otherwise.
        cif_file = params.get('cif_file')
        if cif_file and self._structure_factor_capability_ok():
            self._update_unitcell_visualizers(cif_file)
        else:
            for viz in (
                self.angles_to_hkl_unitcell_viz,
                self.hkl_to_angles_unitcell_viz,
                self.hk_fixed_tth_unitcell_viz,
            ):
                viz.reset()

        # HKL scan visualizer uses trajectory-only mode, no structure factor calculator needed

    def _structure_factor_capability_ok(self) -> bool:
        """Whether the accepted structure's atomic data supports rendering
        real atoms in the unit-cell preview, not just a valid cell.

        Reached via the app controller (same pattern as
        StructureFactorTab._capability_block_message()) rather than
        widening the params dict. Fails open (True) when there's no
        reachable structure_source -- e.g. a standalone tab built directly
        in a test with controller=None -- since that's not a case this
        check is meant to guard.
        """
        if not self.controller:
            return True
        source = getattr(self.controller.app_controller, "structure_source", None)
        if source is None:
            return True
        return source.capabilities.structure_factor_ok

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
                fit_atomic_preview(viz)
                
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
        self.context_label.setText(
            f"Crystal  a {self.parameters.get('a', 0):.3f} · "
            f"b {self.parameters.get('b', 0):.3f} · "
            f"c {self.parameters.get('c', 0):.3f} Å    |    Beam {energy:g} eV"
        )

    @pyqtSlot()
    def _open_change_structure_dialog(self):
        """Same single entry point as the main window's toolbar/menu action --
        pick a different CIF, or use the dialog's own "Start over" button
        for the full destructive reset."""
        if not self.controller:
            return
        dialog = ChangeStructureDialog(self.controller.app_controller, self)
        dialog.exec_()

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
        left_layout.addWidget(control_rail(self.angles_to_hkl_controls,
            pin_action=self.angles_to_hkl_controls.calculate_button), 1)

        # Create results widget
        self.angles_to_hkl_results = AnglesToHKLResults(parent=self)
        left_layout.addWidget(self.angles_to_hkl_results)


        # Right column - Visualizers
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Scattering visualizer
        self.angles_to_hkl_visualizer.visualize_lab_system()
        self.angles_to_hkl_visualizer.visualize_scattering_geometry()
        right_layout.addWidget(plot_tabs(
            ("Geometry", self.angles_to_hkl_visualizer),
            ("Atomic structure", self.angles_to_hkl_unitcell_viz)))

        # Add columns to main layout
        angles_layout.addWidget(left_column, 3)
        angles_layout.addWidget(right_column, 2)

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
        left_layout.addWidget(control_rail(self.hkl_to_angles_controls,
            pin_action=self.hkl_to_angles_controls.calculate_button), 1)

        # Create results widget
        self.hkl_to_angles_results = HKLToAnglesResultsWidget(parent=self)
        # self.hkl_to_angles_results.solutionSelected.connect(self.on_angle_solution_selected)
        left_layout.addWidget(self.hkl_to_angles_results)


        # Right column - Visualizers
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Scattering visualizer
        self.hkl_to_angles_visualizer.visualize_lab_system()
        self.hkl_to_angles_visualizer.visualize_scattering_geometry()
        right_layout.addWidget(plot_tabs(
            ("Geometry", self.hkl_to_angles_visualizer),
            ("Atomic structure", self.hkl_to_angles_unitcell_viz)))

        # Add columns to main layout
        hkl_layout.addWidget(left_column, 3)
        hkl_layout.addWidget(right_column, 2)

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
        left_layout.addWidget(control_rail(self.hk_angles_controls,
            pin_action=self.hk_angles_controls.calculate_button), 1)

        # Create results widget
        self.hk_angles_results = HKAnglesResultsWidget(parent=self)
        # self.hk_angles_results.solutionSelected.connect(self.on_angle_solution_selected_tth)
        left_layout.addWidget(self.hk_angles_results)


        # Right column - Visualizers
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Scattering visualizer
        self.hk_fixed_tth_visualizer.visualize_lab_system()
        self.hk_fixed_tth_visualizer.visualize_scattering_geometry()
        right_layout.addWidget(plot_tabs(
            ("Geometry", self.hk_fixed_tth_visualizer),
            ("Atomic structure", self.hk_fixed_tth_unitcell_viz)))

        # Add columns to main layout
        hk_layout.addWidget(left_column, 3)
        hk_layout.addWidget(right_column, 2)

        # Add to tab widget
        self.tab_widget.addTab(hk_tab, "Plane → Angles · fixed tth")

    def _create_hkl_scan_tab(self):
        """Create tab for scanning a range of HKL values."""
        scan_tab = QWidget()
        scan_layout = QVBoxLayout(scan_tab)
        upper_panel = QWidget()
        upper_layout = QHBoxLayout(upper_panel)

        # Create controls widget
        self.hkl_scan_controls = HKLScanControls(parent=self)
        self.hkl_scan_controls.calculateClicked.connect(self.calculate_hkl_scan)
        self.hkl_scan_controls.calculate_button.setText("Calculate scan")
        controls = control_rail(self.hkl_scan_controls,
            pin_action=self.hkl_scan_controls.calculate_button)
        controls.setMinimumWidth(400)
        upper_layout.addWidget(controls, 1)

        # Create results table & 2d visualization
        results_splitter = QSplitter(Qt.Vertical)
        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Results table
        self.hkl_scan_results_table = HKLScanResultsTable(parent=self)
        results_layout.addWidget(self.hkl_scan_results_table.get_widget(), 1)
        
        # Reminder notes below results table
        notes_layout = QVBoxLayout()
        notes_layout.setSpacing(2)
        note1 = QLabel("Solutions are grouped by scan point.")
        note1.setStyleSheet("color: gray; font-size: 11px; font-style: italic;")
        note2 = QLabel("Some HKL points may be unreachable due to the momentum transfer limit at current energy.")
        note2.setWordWrap(True)
        note2.setStyleSheet("color: gray; font-size: 11px; font-style: italic;")
        notes_layout.addWidget(note1)
        notes_layout.addWidget(note2)
        results_layout.addLayout(notes_layout)
        
        # 2D visualizer section
        self.hkl_scan_visualizer = HKLScan2DVisualizer(parent=self)
        upper_layout.addWidget(self.hkl_scan_visualizer, 1)
        results_splitter.addWidget(upper_panel)
        results_splitter.addWidget(results_panel)
        results_splitter.setSizes([360, 240])
        results_splitter.setChildrenCollapsible(False)

        # Add to layout
        scan_layout.addWidget(results_splitter)
        # Add to tab widget
        self.tab_widget.addTab(scan_tab, "HKL Scan · fixed tth")

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

                # plot the accessible area in k-space
                params = self.hkl_scan_controls.get_scan_parameters() 
                tth = params["tth"]
                accessible_area = self.calculator.get_max_hkl_values(tth)
                h_max, k_max, l_max = accessible_area["h_max"], accessible_area["k_max"], accessible_area["l_max"]
                success, message = accessible_area["success"], accessible_area["message"]
                self.hkl_scan_visualizer.plot_accessible_area(plane_type, h_max, k_max, l_max, message)
            else:
                # No scan results yet, just clear the plot
                self.hkl_scan_visualizer.clear_plot()
                
        except Exception as e:
            print(f"**Error** updating HKL visualization: {e}")

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
            fit_atomic_preview(self.angles_to_hkl_unitcell_viz)
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
        try:
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

            if result["number_of_solutions"] == 0:
                QMessageBox.warning(
                    self,
                    "No Solution",
                    "No feasible angle solution exists for this HKL point with the "
                    "given fixed angle. The point may be unreachable at this energy, "
                    "or unreachable with this particular fixed angle value.",
                )
                return

            # Update visualization with the first solution
            # Extract first solution for visualization
            first_solution = {
                "tth": result["tth"][0],
                "theta": result["theta"][0],
                "phi": result["phi"][0],
                "chi": result["chi"][0],
                "H": result["H"],
                "K": result["K"],
                "L": result["L"],
            }
            self.hkl_to_angles_visualizer.visualize_lab_system(
                is_clear=True, chi=first_solution["chi"], phi=first_solution["phi"], plot_basis=False, plot_k_basis=True
            )
            self.hkl_to_angles_visualizer.visualize_scattering_geometry(
                scattering_angles=first_solution, is_clear=False
            )
            self.hkl_to_angles_unitcell_viz.visualize_unitcell()
            fit_atomic_preview(self.hkl_to_angles_unitcell_viz)
            self.hkl_to_angles_unitcell_viz.visualize_scattering_geometry(
                scattering_angles=first_solution
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"**Error** calculating angles: {str(e)}")

    @pyqtSlot()
    def calculate_angles_tth_fixed(self):
        """Calculate angles from HK with fixed tth."""
        try:
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
            if not result["success"]:
                QMessageBox.warning(
                    self, "Warning", result.get("error", "No solution found")
                )
                return
            self.hk_angles_results.display_results(result)

            if result["number_of_solutions"] == 0:
                QMessageBox.warning(
                    self,
                    "No Solution",
                    "No feasible angle solution exists for this HK point with the "
                    "given fixed tth/fixed angle. The point may be unreachable at "
                    "this energy, or unreachable with this particular fixed angle value.",
                )
                return

            # Update visualization with the first solution
            # Extract first solution for visualization
            first_solution = {
                "tth": result["tth"][0],
                "theta": result["theta"][0],
                "phi": result["phi"][0],
                "chi": result["chi"][0],
                "H": result["H"][0],
                "K": result["K"][0],
                "L": result["L"][0],
            }
            self.hk_fixed_tth_visualizer.visualize_lab_system(
                is_clear=True, chi=first_solution["chi"], phi=first_solution["phi"], plot_basis=False, plot_k_basis=True
            )
            self.hk_fixed_tth_visualizer.visualize_scattering_geometry(
                scattering_angles=first_solution, is_clear=False
            )
            self.hk_fixed_tth_unitcell_viz.visualize_unitcell()
            fit_atomic_preview(self.hk_fixed_tth_unitcell_viz)
            self.hk_fixed_tth_unitcell_viz.visualize_scattering_geometry(
                scattering_angles=first_solution
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"**Error** calculating angles (tth fixed): {str(e)}")

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

    def clear(self):
        """Discard all structure-dependent results/plots for a structure
        change (replace, remove, or reset) -- called by
        ScatteringGeometryController.invalidate_structure() after it has
        already rebound self.calculator to a fresh, uninitialized instance.

        Re-syncs funtional_objects[0] (used by set_parameters()'s
        initialize loop) to the new calculator, clears displayed results and
        their accumulated history, resets all three unit-cell previews, and
        clears the HKL-scan table/plot -- so nothing left over from the
        previous structure can be mistaken for a result of the new one.
        """
        if self.funtional_objects:
            self.funtional_objects[0] = self.calculator

        self.clear_hkl_to_angles_results()
        self.clear_hk_tth_fixed_results()
        self.hkl_to_angles_results.clear_history()
        self.hk_angles_results.clear_history()
        if hasattr(self, "angles_to_hkl_results"):
            self.angles_to_hkl_results.clear_results()

        for viz in (
            self.angles_to_hkl_unitcell_viz,
            self.hkl_to_angles_unitcell_viz,
            self.hk_fixed_tth_unitcell_viz,
        ):
            viz.reset()

        if hasattr(self, "hkl_scan_results_table"):
            self.hkl_scan_results_table.setRowCount(0)
        if hasattr(self, "hkl_scan_visualizer"):
            self.hkl_scan_visualizer.clear_plot()
