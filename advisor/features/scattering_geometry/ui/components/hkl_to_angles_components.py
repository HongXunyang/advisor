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
    QDialog,
    QScrollArea,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont
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


class HistoryDialog(QDialog):
    """Dialog to display history of all calculation results."""

    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calculation History")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        if not history:
            no_history_label = QLabel("No history available.")
            no_history_label.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(no_history_label)
        else:
            # Display history in reverse order (newest first)
            for run_idx, entry in enumerate(reversed(history)):
                run_num = len(history) - run_idx
                run_frame = QFrame()
                run_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
                run_layout = QVBoxLayout(run_frame)
                
                # Header with HKL values
                header_label = QLabel(f"Run #{run_num}: H={entry['H']:.4f}, K={entry['K']:.4f}, L={entry['L']:.4f}")
                header_font = QFont()
                header_font.setBold(True)
                header_label.setFont(header_font)
                run_layout.addWidget(header_label)
                
                # Number of solutions
                num_solutions = entry.get('number_of_solutions', 1)
                solutions_label = QLabel(f"Solutions found: {num_solutions}")
                run_layout.addWidget(solutions_label)
                
                # Create table for solutions
                table = QTableWidget()
                table.setColumnCount(5)
                table.setHorizontalHeaderLabels(["#", "tth (°)", "θ (°)", "φ (°)", "χ (°)"])
                table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                table.verticalHeader().setVisible(False)
                table.setMaximumHeight(100)
                
                # Add rows for each solution
                tth_list = entry.get('tth', [])
                theta_list = entry.get('theta', [])
                phi_list = entry.get('phi', [])
                chi_list = entry.get('chi', [])
                feasible_list = entry.get('feasible', [])
                
                for i in range(len(tth_list)):
                    table.insertRow(i)
                    table.setItem(i, 0, QTableWidgetItem(f"{i + 1}"))
                    table.setItem(i, 1, QTableWidgetItem(f"{tth_list[i]:.2f}"))
                    table.setItem(i, 2, QTableWidgetItem(f"{theta_list[i]:.2f}"))
                    table.setItem(i, 3, QTableWidgetItem(f"{phi_list[i]:.2f}"))
                    table.setItem(i, 4, QTableWidgetItem(f"{chi_list[i]:.2f}"))
                    
                    # Color based on feasibility
                    feasible = feasible_list[i] if i < len(feasible_list) else True
                    color = QColor(198, 239, 206) if feasible else QColor(255, 199, 206)
                    for col in range(5):
                        item = table.item(i, col)
                        if item:
                            item.setBackground(QBrush(color))
                
                run_layout.addWidget(table)
                scroll_layout.addWidget(run_frame)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class HKLToAnglesResultsWidget(QWidget):
    """Results widget showing current solutions and history button."""

    # Signal emitted when a solution is selected
    solutionSelected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Store history of all results
        self.history = []
        self.current_result = None

        # Main layout
        layout = QVBoxLayout(self)

        # Results group
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        # Number of solutions label
        self.solutions_label = QLabel("No results yet")
        self.solutions_label.setAlignment(Qt.AlignCenter)
        results_layout.addWidget(self.solutions_label)

        # Current solutions display (table for up to 2 solutions)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["tth (°)", "θ (°)", "φ (°)", "χ (°)"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setMaximumHeight(90)
        self.results_table.itemSelectionChanged.connect(self._on_selection_changed)
        results_layout.addWidget(self.results_table)

        # Show history button
        self.history_button = QPushButton("Show History")
        self.history_button.clicked.connect(self._show_history)
        self.history_button.setObjectName("historyButton")
        results_layout.addWidget(self.history_button)

        layout.addWidget(results_group)

    def display_results(self, results):
        """Display current calculation results and add to history."""
        if not results or not results.get("success", False):
            return
        
        self.current_result = results
        
        # Add to history
        self.history.append(results)
        
        # Update solutions label
        num_solutions = results.get('number_of_solutions', 1)
        self.solutions_label.setText(f"Found {num_solutions} solution(s)")
        
        # Clear and populate table
        self.results_table.setRowCount(0)
        
        tth_list = results.get('tth', [])
        theta_list = results.get('theta', [])
        phi_list = results.get('phi', [])
        chi_list = results.get('chi', [])
        feasible_list = results.get('feasible', [])
        
        for i in range(len(tth_list)):
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            self.results_table.setItem(row, 0, QTableWidgetItem(f"{tth_list[i]:.2f}"))
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{theta_list[i]:.2f}"))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{phi_list[i]:.2f}"))
            self.results_table.setItem(row, 3, QTableWidgetItem(f"{chi_list[i]:.2f}"))
            
            # Color based on feasibility
            feasible = feasible_list[i] if i < len(feasible_list) else True
            color = QColor(198, 239, 206) if feasible else QColor(255, 199, 206)
            for col in range(4):
                item = self.results_table.item(row, col)
                if item:
                    item.setBackground(QBrush(color))

    def _on_selection_changed(self):
        """Handle selection change in the table."""
        current_row = self.results_table.currentRow()
        if current_row >= 0 and self.current_result:
            tth_list = self.current_result.get('tth', [])
            theta_list = self.current_result.get('theta', [])
            phi_list = self.current_result.get('phi', [])
            chi_list = self.current_result.get('chi', [])
            
            if current_row < len(tth_list):
                selected_solution = {
                    'tth': tth_list[current_row],
                    'theta': theta_list[current_row],
                    'phi': phi_list[current_row],
                    'chi': chi_list[current_row],
                    'H': self.current_result.get('H'),
                    'K': self.current_result.get('K'),
                    'L': self.current_result.get('L'),
                }
                self.solutionSelected.emit(selected_solution)

    def _show_history(self):
        """Show history dialog."""
        dialog = HistoryDialog(self.history, self)
        dialog.exec_()

    def clear_results(self):
        """Clear current results (but keep history)."""
        self.results_table.setRowCount(0)
        self.solutions_label.setText("No results yet")
        self.current_result = None
