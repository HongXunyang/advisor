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
    QRadioButton,
    QButtonGroup,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
class HKLToAnglesControls(QWidget):
    """Widget for HKL to Angles calculation controls."""

    # Signal emitted when calculate button is clicked
    calculateClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        main_layout = QVBoxLayout(self)

        # HKL Input form
        form_group = QGroupBox("HKL Indices")
        form_layout = QVBoxLayout(form_group)

        # Create HKL inputs horizontally aligned
        hkl_inputs_widget = QWidget()
        hkl_inputs_layout = QHBoxLayout(hkl_inputs_widget)
        hkl_inputs_layout.setContentsMargins(0, 0, 0, 0)

        # H input
        h_form = QWidget()
        h_form_layout = QFormLayout(h_form)
        h_form_layout.setContentsMargins(0, 0, 0, 0)
        self.H_input = QDoubleSpinBox()
        self.H_input.setRange(-100.0, 100)
        self.H_input.setDecimals(4)
        self.H_input.setValue(0.15)
        h_form_layout.addRow("H:", self.H_input)
        hkl_inputs_layout.addWidget(h_form)

        # K input
        k_form = QWidget()
        k_form_layout = QFormLayout(k_form)
        k_form_layout.setContentsMargins(0, 0, 0, 0)
        self.K_input = QDoubleSpinBox()
        self.K_input.setRange(-100.0, 100)
        self.K_input.setDecimals(4)
        self.K_input.setValue(0.1)
        k_form_layout.addRow("K:", self.K_input)
        hkl_inputs_layout.addWidget(k_form)

        # L input
        l_form = QWidget()
        l_form_layout = QFormLayout(l_form)
        l_form_layout.setContentsMargins(0, 0, 0, 0)
        self.L_input = QDoubleSpinBox()
        self.L_input.setRange(-100.0, 100)
        self.L_input.setDecimals(4)
        self.L_input.setValue(-0.5)
        l_form_layout.addRow("L:", self.L_input)
        hkl_inputs_layout.addWidget(l_form)

        form_layout.addWidget(hkl_inputs_widget)

        main_layout.addWidget(form_group)

        # Constraints group - using the same style as other tabs
        constraints_group = QGroupBox("Constraints")
        constraints_layout = QVBoxLayout(constraints_group)

        # Fixed angle selection buttons - top row like other tabs
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

        constraints_layout.addWidget(angle_selection)

        # Create angle value inputs - bottom row like other tabs
        angles_row = QWidget()
        angles_layout = QHBoxLayout(angles_row)
        angles_layout.setContentsMargins(0, 0, 0, 0)

        # Chi input
        self.chi_widget = QWidget()
        chi_layout = QFormLayout(self.chi_widget)
        chi_layout.setContentsMargins(0, 0, 0, 0)
        self.chi_input = QDoubleSpinBox()
        self.chi_input.setRange(-180.0, 180.0)
        self.chi_input.setValue(0.0)
        self.chi_input.setSuffix(" °")
        chi_layout.addRow("χ:", self.chi_input)
        angles_layout.addWidget(self.chi_widget)

        # Phi input
        self.phi_widget = QWidget()
        phi_layout = QFormLayout(self.phi_widget)
        phi_layout.setContentsMargins(0, 0, 0, 0)
        self.phi_input = QDoubleSpinBox()
        self.phi_input.setRange(-180.0, 180.0)
        self.phi_input.setValue(0.0)
        self.phi_input.setSuffix(" °")
        phi_layout.addRow("φ:", self.phi_input)
        angles_layout.addWidget(self.phi_widget)

        constraints_layout.addWidget(angles_row)
        main_layout.addWidget(constraints_group)

        # Calculate button
        self.calculate_button = QPushButton("Calculate Angles")
        self.calculate_button.clicked.connect(self.calculateClicked.emit)
        self.calculate_button.setObjectName("calculateButton")
        main_layout.addWidget(self.calculate_button)

        # Connect signals
        self.fix_chi_btn.clicked.connect(lambda: self._set_active_fixed_angle("chi"))
        self.fix_phi_btn.clicked.connect(lambda: self._set_active_fixed_angle("phi"))

        # Initialize widget states
        self._set_active_fixed_angle("chi")  # Set initial fixed angle and apply styling

    def _update_fixed_angle_ui(self):
        """Update UI based on which angle is fixed.
        
        If chi is fixed: Show chi input, hide phi input
        If phi is fixed: Show phi input, hide chi input
        """
        is_chi_fixed = self.fix_chi_btn.isChecked()
        self.chi_widget.setVisible(is_chi_fixed)
        self.phi_widget.setVisible(not is_chi_fixed)

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

    def _set_active_fixed_angle(self, angle: str):
        """Set the active fixed angle and update widget states and styling."""
        angle = angle.lower()
        self._update_fixed_angle_styles(angle)
        self._update_fixed_angle_ui()

    def get_calculation_parameters(self):
        """Get parameters for angle calculation."""
        # Get fixed angle
        fixed_angle_name = "chi" if self.fix_chi_btn.isChecked() else "phi"
        fixed_angle_value = (
            self.chi_input.value()
            if self.fix_chi_btn.isChecked()
            else self.phi_input.value()
        )

        return {
            "H": self.H_input.value(),
            "K": self.K_input.value(),
            "L": self.L_input.value(),
            "fixed_angle_name": fixed_angle_name,
            "fixed_angle_value": fixed_angle_value,
        }

    def set_hkl_values(self, H=None, K=None, L=None):
        """Set HKL input values programmatically."""
        if H is not None:
            self.H_input.setValue(H)
        if K is not None:
            self.K_input.setValue(K)
        if L is not None:
            self.L_input.setValue(L)


class HKLToAnglesResultsTable(QTableWidget):
    """Table to display HKL to Angles calculation results."""

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

    def display_results(self, results):
        """Append calculation results to the table."""
        # Don't clear table - append new results
        self.last_results = results

        # Check if we have results
        if not results or not results.get("success", False):
            return



        # Add rows for each new solution
        row_position = self.rowCount()
        self.insertRow(row_position)

        # Add solution data
        self.setItem(row_position, 0, QTableWidgetItem(f"{results['tth']:.1f}"))
        self.setItem(row_position, 1, QTableWidgetItem(f"{results['theta']:.1f}"))
        self.setItem(row_position, 2, QTableWidgetItem(f"{results['phi']:.1f}"))
        self.setItem(row_position, 3, QTableWidgetItem(f"{results['chi']:.1f}"))

        # Highlight new solutions with light blue background
        feasible_brush = QBrush(QColor(198, 239, 206))  # light green
        infeasible_brush = QBrush(QColor(255, 199, 206))  # light red
        row_color = feasible_brush if results["feasible"] else infeasible_brush
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


class HKLToAnglesResultsWidget(QWidget):
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
        self.results_table = HKLToAnglesResultsTable(self)
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
