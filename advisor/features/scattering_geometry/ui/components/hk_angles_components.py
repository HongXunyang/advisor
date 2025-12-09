#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QButtonGroup,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush


class HKAnglesControls(QWidget):
    """Widget for HK to Angles calculation controls with fixed tth."""

    # Signal emitted when calculate button is clicked
    calculateClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        main_layout = QVBoxLayout(self)



        # HKL indices group
        hkl_group = QGroupBox("HKL Indices")
        hkl_layout = QFormLayout(hkl_group)

        # Plane selection buttons
        plane_selection = QWidget()
        plane_layout = QHBoxLayout(plane_selection)
        plane_layout.setContentsMargins(0, 0, 0, 0)

        self.hk_plane_btn = QPushButton("HK plane")
        self.hl_plane_btn = QPushButton("HL plane")
        self.kl_plane_btn = QPushButton("KL plane")
        
        # Make buttons checkable for toggle behavior
        for btn in (self.hk_plane_btn, self.hl_plane_btn, self.kl_plane_btn):
            btn.setCheckable(True)
        
        self.hk_plane_btn.setChecked(True)  # Default to HK plane (L fixed)

        # Create a button group for mutual exclusion
        self.hkl_plane_button_group = QButtonGroup(self)
        self.hkl_plane_button_group.addButton(self.hk_plane_btn)
        self.hkl_plane_button_group.addButton(self.hl_plane_btn)
        self.hkl_plane_button_group.addButton(self.kl_plane_btn)

        plane_layout.addWidget(self.hk_plane_btn)
        plane_layout.addWidget(self.hl_plane_btn)
        plane_layout.addWidget(self.kl_plane_btn)
        # stretch buttons to be evenly distributed
        plane_layout.addStretch()
        hkl_layout.addRow("Plane:", plane_selection)
        # Create HKL inputs
        hkl_inputs_widget = QWidget()
        hkl_inputs_layout = QHBoxLayout(hkl_inputs_widget)
        hkl_inputs_layout.setContentsMargins(0, 0, 0, 0)

        # H input row
        self.h_row = QWidget()
        h_layout = QHBoxLayout(self.h_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_form = QWidget()
        h_form_layout = QFormLayout(h_form)
        h_form_layout.setContentsMargins(0, 0, 0, 0)
        self.H_input = QDoubleSpinBox()
        self.H_input.setRange(-100.0, 100)
        self.H_input.setDecimals(4)
        self.H_input.setValue(0.15)
        h_form_layout.addRow("H:", self.H_input)
        h_layout.addWidget(h_form)
        hkl_inputs_layout.addWidget(self.h_row)

        # K input row
        self.k_row = QWidget()
        k_layout = QHBoxLayout(self.k_row)
        k_layout.setContentsMargins(0, 0, 0, 0)
        k_form = QWidget()
        k_form_layout = QFormLayout(k_form)
        k_form_layout.setContentsMargins(0, 0, 0, 0)
        self.K_input = QDoubleSpinBox()
        self.K_input.setRange(-100, 100)
        self.K_input.setDecimals(4)
        self.K_input.setValue(0.1)
        k_form_layout.addRow("K:", self.K_input)
        k_layout.addWidget(k_form)
        hkl_inputs_layout.addWidget(self.k_row)

        # L input row
        self.l_row = QWidget()
        l_layout = QHBoxLayout(self.l_row)
        l_layout.setContentsMargins(0, 0, 0, 0)
        l_form = QWidget()
        l_form_layout = QFormLayout(l_form)
        l_form_layout.setContentsMargins(0, 0, 0, 0)
        self.L_input = QDoubleSpinBox()
        self.L_input.setRange(-100, 100)
        self.L_input.setDecimals(4)
        self.L_input.setValue(-0.5)
        l_form_layout.addRow("L:", self.L_input)
        l_layout.addWidget(l_form)
        hkl_inputs_layout.addWidget(self.l_row)

        hkl_layout.addRow(hkl_inputs_widget)
        main_layout.addWidget(hkl_group)


        # Unified Fixed Angles panel
        fixed_angles_group = QGroupBox("Fixed Angles")
        fixed_angles_layout = QVBoxLayout(fixed_angles_group)

        # Top row: Fix χ/Fix φ buttons
        angle_selection = QWidget()
        angle_selection_layout = QHBoxLayout(angle_selection)
        angle_selection_layout.setContentsMargins(0, 0, 0, 0)

        self.fix_chi_btn = QPushButton("Fix χ")
        self.fix_phi_btn = QPushButton("Fix φ")
        
        # Make buttons checkable for toggle behavior
        for btn in (self.fix_chi_btn, self.fix_phi_btn):
            btn.setCheckable(True)
        
        self.fix_chi_btn.setChecked(True)  # Default to fixed chi

        # Create a button group for mutual exclusion
        self.angle_button_group = QButtonGroup(self)
        self.angle_button_group.addButton(self.fix_chi_btn)
        self.angle_button_group.addButton(self.fix_phi_btn)

        angle_selection_layout.addWidget(self.fix_chi_btn)
        angle_selection_layout.addWidget(self.fix_phi_btn)

        fixed_angles_layout.addWidget(angle_selection)

        # Bottom row: tth on left, chi/phi angles on right
        angle_values = QWidget()
        angle_values_layout = QHBoxLayout(angle_values)
        angle_values_layout.setContentsMargins(0, 0, 0, 0)

        # tth input (left side)
        self.tth_widget = QWidget()
        tth_layout = QFormLayout(self.tth_widget)
        tth_layout.setContentsMargins(0, 0, 0, 0)
        self.tth_input = QDoubleSpinBox()
        self.tth_input.setRange(0.0, 180.0)
        self.tth_input.setValue(150.0)
        self.tth_input.setSuffix(" °")
        tth_layout.addRow("tth:", self.tth_input)
        angle_values_layout.addWidget(self.tth_widget)
        
        # Chi input
        self.chi_widget = QWidget()
        chi_layout = QFormLayout(self.chi_widget)
        chi_layout.setContentsMargins(0, 0, 0, 0)
        self.chi_input = QDoubleSpinBox()
        self.chi_input.setRange(-180.0, 180.0)
        self.chi_input.setValue(0.0)
        self.chi_input.setSuffix(" °")
        chi_layout.addRow("χ:", self.chi_input)
        angle_values_layout.addWidget(self.chi_widget)

        # Phi input
        self.phi_widget = QWidget()
        phi_layout = QFormLayout(self.phi_widget)
        phi_layout.setContentsMargins(0, 0, 0, 0)
        self.phi_input = QDoubleSpinBox()
        self.phi_input.setRange(-180.0, 180.0)
        self.phi_input.setValue(0.0)
        self.phi_input.setSuffix(" °")
        phi_layout.addRow("φ:", self.phi_input)
        angle_values_layout.addWidget(self.phi_widget)

        fixed_angles_layout.addWidget(angle_values)

        main_layout.addWidget(fixed_angles_group) 


        # Calculate button
        self.calculate_button = QPushButton("Calculate Angles")
        self.calculate_button.clicked.connect(self.calculateClicked.emit)
        self.calculate_button.setObjectName("calculateButton")
        main_layout.addWidget(self.calculate_button)

        # Connect signals
        self.hk_plane_btn.clicked.connect(lambda: self._set_active_plane("HK"))
        self.hl_plane_btn.clicked.connect(lambda: self._set_active_plane("HL"))
        self.kl_plane_btn.clicked.connect(lambda: self._set_active_plane("KL"))
        self.fix_chi_btn.clicked.connect(lambda: self._set_active_fixed_angle("chi"))
        self.fix_phi_btn.clicked.connect(lambda: self._set_active_fixed_angle("phi"))

        # Initialize widget states
        self._set_active_plane("HK")  # Set initial plane and apply styling
        self._set_active_fixed_angle("chi")  # Set initial fixed angle and apply styling

    def _update_hkl_visibility(self):
        """Update visibility of HKL inputs based on current plane selection.
        
        HK plane: H and K inputs visible, L input hidden
        HL plane: H and L inputs visible, K input hidden  
        KL plane: K and L inputs visible, H input hidden
        """
        if self.hk_plane_btn.isChecked():
            # HK plane: H and K visible, L hidden
            self.h_row.setVisible(True)
            self.k_row.setVisible(True)
            self.l_row.setVisible(False)
        elif self.hl_plane_btn.isChecked():
            # HL plane: H and L visible, K hidden
            self.h_row.setVisible(True)
            self.k_row.setVisible(False)
            self.l_row.setVisible(True)
        elif self.kl_plane_btn.isChecked():
            # KL plane: K and L visible, H hidden
            self.h_row.setVisible(False)
            self.k_row.setVisible(True)
            self.l_row.setVisible(True)

    def _update_fixed_angle_ui(self):
        """Update UI based on which angle is fixed.
        
        If chi is fixed: Show chi input, hide phi input
        If phi is fixed: Show phi input, hide chi input
        """
        is_chi_fixed = self.fix_chi_btn.isChecked()
        self.chi_widget.setVisible(is_chi_fixed)
        self.phi_widget.setVisible(not is_chi_fixed)

    def _update_plane_styles(self, active: str):
        """Update plane button colors based on active plane."""
        mapping = {
            "HK": self.hk_plane_btn,
            "HL": self.hl_plane_btn,
            "KL": self.kl_plane_btn,
        }
        for name, btn in mapping.items():
            if name == active:
                btn.setChecked(True)
                btn.setProperty("class", "activeToggle")
            else:
                btn.setChecked(False)
                btn.setProperty("class", "inactiveToggle")
            # Force style refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _update_fixed_angle_styles(self, active: str):
        """Update fixed angle button colors based on active selection."""
        mapping = {
            "chi": self.fix_chi_btn,
            "phi": self.fix_phi_btn,
        }
        for name, btn in mapping.items():
            if name == active:
                btn.setChecked(True)
                btn.setProperty("class", "activeToggle")
            else:
                btn.setChecked(False)
                btn.setProperty("class", "inactiveToggle")
            # Force style refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _set_active_plane(self, plane: str):
        """Set the active plane and update widget states and styling."""
        plane = plane.upper()
        self._update_plane_styles(plane)
        self._update_hkl_visibility()

    def _set_active_fixed_angle(self, angle: str):
        """Set the active fixed angle and update widget states and styling."""
        angle = angle.lower()
        self._update_fixed_angle_styles(angle)
        self._update_fixed_angle_ui()

    def get_calculation_parameters(self):
        """Get parameters for angle calculation."""
        # Get fixed index based on plane selection
        # HK plane means L is fixed, HL plane means K is fixed, KL plane means H is fixed
        fixed_index = None
        if self.hk_plane_btn.isChecked():
            fixed_index = "L"  # HK plane: L is fixed
        elif self.hl_plane_btn.isChecked():
            fixed_index = "K"  # HL plane: K is fixed
        elif self.kl_plane_btn.isChecked():
            fixed_index = "H"  # KL plane: H is fixed

        # Get fixed angle
        fixed_angle_name = "chi" if self.fix_chi_btn.isChecked() else "phi"
        fixed_angle_value = (
            self.chi_input.value()
            if self.fix_chi_btn.isChecked()
            else self.phi_input.value()
        )

        # Get HKL values (None for fixed index)
        H = self.H_input.value() if fixed_index != "H" else None
        K = self.K_input.value() if fixed_index != "K" else None
        L = self.L_input.value() if fixed_index != "L" else None

        return {
            "tth": self.tth_input.value(),
            "H": H,
            "K": K,
            "L": L,
            "fixed_index": fixed_index,
            "fixed_angle_name": fixed_angle_name,
            "fixed_angle_value": fixed_angle_value,
        }


class HKAnglesResultsTable(QTableWidget):
    """Table to display HK to Angles calculation results."""

    # Signal emitted when a solution is selected
    solutionSelected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set up table
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["tth (°)", "θ (°)", "φ (°)", "χ (°)"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Hide vertical header (row numbers)
        self.verticalHeader().setVisible(False)

        # Connect selection change signal
        self.itemSelectionChanged.connect(self.on_selection_changed)

        # Store the last results for reference
        self.last_results = None

    def display_results(self, result):
        """Append calculation results to the table."""
        # Don't clear table - append new results
        self.last_results = result

        # Check if we have results
        if not result or not result.get("success", False):
            return


        # Add rows for each new solution
        row_position = self.rowCount()
        self.insertRow(row_position)

        # Add solution data
        self.setItem(row_position, 0, QTableWidgetItem(f"{result['tth']:.1f}"))
        self.setItem(row_position, 1, QTableWidgetItem(f"{result['theta']:.1f}"))
        self.setItem(row_position, 2, QTableWidgetItem(f"{result['phi']:.1f}"))
        self.setItem(row_position, 3, QTableWidgetItem(f"{result['chi']:.1f}"))

        # Highlight new solutions with light blue background
        feasible_brush = QBrush(QColor(198, 239, 206))  # light green
        infeasible_brush = QBrush(QColor(255, 199, 206))  # light red
        row_color = feasible_brush if result["feasible"] else infeasible_brush
        for col in range(self.columnCount()):
            item = self.item(row_position, col)
            if item:
                item.setBackground(row_color)

        # Scroll to the bottom to show the new results
        self.scrollToBottom()

    def on_selection_changed(self):
        """Handle selection change in the table."""
        current_row = self.currentRow()
        if current_row >= 0 and self.last_results:
            if current_row < 1:
                selected_solution = self.last_results
                self.solutionSelected.emit(selected_solution)

    def clear_results(self):
        """Clear all results from the table."""
        self.setRowCount(0)
        self.last_results = None


class HKAnglesResultsWidget(QWidget):
    """Complete results widget with table and clear button."""

    # Signal emitted when a solution is selected
    solutionSelected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        layout = QVBoxLayout(self)

        # Results group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        # Create table
        self.results_table = HKAnglesResultsTable(self)
        self.results_table.solutionSelected.connect(self.solutionSelected.emit)
        results_layout.addWidget(self.results_table)

        # Add clear button
        self.clear_button = QPushButton("Clear Results")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setObjectName("clearButton")
        results_layout.addWidget(self.clear_button)

        layout.addWidget(results_group)

    def display_results(self, results):
        """Display calculation results."""
        self.results_table.display_results(results)

    def clear_results(self):
        """Clear all results."""
        self.results_table.clear_results()
