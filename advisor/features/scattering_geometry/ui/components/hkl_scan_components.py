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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QRadioButton,
    QButtonGroup,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
import csv
import os
import numpy as np

class RangeInputWidget(QWidget):
    """Widget for input range (start, end, num_points)."""

    def __init__(self, label, parent=None):
        super().__init__(parent)

        # Main layout
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create group with label but remove border styling
        group = QGroupBox(label)
        group.setStyleSheet("QGroupBox { border: none; font-weight: bold; }")
        group_layout = QHBoxLayout(group)
        group_layout.setContentsMargins(10, 10, 10, 10)

        # Start value input with label
        start_widget = QWidget()
        start_layout = QFormLayout(start_widget)
        start_layout.setContentsMargins(0, 0, 0, 0)

        self.start_input = QDoubleSpinBox()
        self.start_input.setRange(-100.0, 100)
        self.start_input.setDecimals(3)
        self.start_input.setValue(0.0)
        start_layout.addRow("Start:", self.start_input)

        group_layout.addWidget(start_widget)

        # End value input with label
        end_widget = QWidget()
        end_layout = QFormLayout(end_widget)
        end_layout.setContentsMargins(0, 0, 0, 0)

        self.end_input = QDoubleSpinBox()
        self.end_input.setRange(-100.0, 100)
        self.end_input.setDecimals(3)
        self.end_input.setValue(-0.3)
        end_layout.addRow("End:", self.end_input)

        group_layout.addWidget(end_widget)

        layout.addRow(group)

    def get_range(self):
        """Get start and end values."""
        return (
            self.start_input.value(),
            self.end_input.value(),
        )

    def set_range(self, start, end):
        """Set start and end values."""
        self.start_input.setValue(start)
        self.end_input.setValue(end)

    def set_enabled(self, enabled):
        """Enable or disable widget."""
        self.start_input.setEnabled(enabled)
        self.end_input.setEnabled(enabled)

    def set_visible(self, visible):
        """Show or hide widget."""
        self.setVisible(visible)


class HKLScanControls(QWidget):
    """Widget for HKL scan controls."""

    # Signal emitted when calculate button is clicked
    calculateClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        main_layout = QVBoxLayout(self)

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

        # HKL index selection
        hkl_group = QGroupBox("Choose a plane")
        hkl_layout = QVBoxLayout(hkl_group)

        # Plane selection - using plane-based naming like Structure Factor Calculator
        index_selection = QWidget()
        index_layout = QHBoxLayout(index_selection)
        index_layout.setContentsMargins(0, 0, 0, 0)

        self.hk_plane_toggle = QPushButton("HK plane")
        self.hl_plane_toggle = QPushButton("HL plane")
        self.kl_plane_toggle = QPushButton("KL plane")
        
        # Make buttons checkable for toggle behavior
        for btn in (self.hk_plane_toggle, self.hl_plane_toggle, self.kl_plane_toggle):
            btn.setCheckable(True)
        
        self.hk_plane_toggle.setChecked(True)  # Default to HK plane (L deactivated)

        # Create a button group for mutual exclusion
        index_button_group = QButtonGroup(self)
        index_button_group.addButton(self.hk_plane_toggle)
        index_button_group.addButton(self.hl_plane_toggle)
        index_button_group.addButton(self.kl_plane_toggle)

        index_layout.addWidget(self.hk_plane_toggle)
        index_layout.addWidget(self.hl_plane_toggle)
        index_layout.addWidget(self.kl_plane_toggle)

        hkl_layout.addWidget(index_selection)

        # Create range widgets for H, K, L
        ranges_widget = QWidget()
        ranges_layout = QVBoxLayout(ranges_widget)
        ranges_layout.setContentsMargins(0, 0, 0, 0)

        self.h_range = RangeInputWidget("H Range")
        self.k_range = RangeInputWidget("K Range")
        self.l_range = RangeInputWidget("L Range")

        ranges_layout.addWidget(self.h_range)
        ranges_layout.addWidget(self.k_range)
        ranges_layout.addWidget(self.l_range)

        hkl_layout.addWidget(ranges_widget)

        # Number of points
        points_widget = QWidget()
        points_layout = QFormLayout(points_widget)
        points_layout.setContentsMargins(0, 0, 0, 0)

        self.num_points = QSpinBox()
        self.num_points.setRange(2, 100)
        self.num_points.setValue(10)
        points_layout.addRow("Number of points:", self.num_points)

        hkl_layout.addWidget(points_widget)

        main_layout.addWidget(hkl_group)

        # Calculate button
        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculateClicked.emit)
        self.calculate_button.setObjectName("calculateButton")
        main_layout.addWidget(self.calculate_button)

        # Connect signals
        self.hk_plane_toggle.clicked.connect(lambda: self._set_active_plane("HK"))
        self.hl_plane_toggle.clicked.connect(lambda: self._set_active_plane("HL"))
        self.kl_plane_toggle.clicked.connect(lambda: self._set_active_plane("KL"))
        self.fix_chi_btn.clicked.connect(lambda: self._set_active_fixed_angle("chi"))
        self.fix_phi_btn.clicked.connect(lambda: self._set_active_fixed_angle("phi"))

        # Initialize widget states
        self._set_active_plane("HK")  # Set initial plane and apply styling
        self._set_active_fixed_angle("chi")  # Set initial fixed angle and apply styling

    def _update_widget_states(self):
        """Update visibility of widgets based on current plane selection.
        
        HK plane: H and K ranges visible, L range hidden
        HL plane: H and L ranges visible, K range hidden  
        KL plane: K and L ranges visible, H range hidden
        """
        if self.hk_plane_toggle.isChecked():
            # HK plane: H and K ranges visible, L range hidden
            self.h_range.set_visible(True)
            self.k_range.set_visible(True)
            self.l_range.set_visible(False)
        elif self.hl_plane_toggle.isChecked():
            # HL plane: H and L ranges visible, K range hidden
            self.h_range.set_visible(True)
            self.k_range.set_visible(False)
            self.l_range.set_visible(True)
        elif self.kl_plane_toggle.isChecked():
            # KL plane: K and L ranges visible, H range hidden
            self.h_range.set_visible(False)
            self.k_range.set_visible(True)
            self.l_range.set_visible(True)

    def _update_fixed_angle_ui(self):
        """Update UI based on which angle is fixed.
        
        If chi is fixed: Show chi input, hide phi input
        If phi is fixed: Show phi input, hide chi input
        """
        is_chi_fixed = self.fix_chi_btn.isChecked()
        # set both invisible first
        self.chi_widget.setVisible(False)
        self.phi_widget.setVisible(False)
        self.chi_widget.setVisible(is_chi_fixed)
        self.phi_widget.setVisible(not is_chi_fixed)
        self.phi_input.setEnabled(not is_chi_fixed)
        self.chi_input.setEnabled(is_chi_fixed)

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

    def _update_toggle_styles(self, active: str):
        """Update toggle button colors based on active plane."""
        mapping = {
            "HK": self.hk_plane_toggle,
            "HL": self.hl_plane_toggle,
            "KL": self.kl_plane_toggle,
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
        self._update_toggle_styles(plane)
        self._update_widget_states()

    def get_scan_parameters(self):
        """Get parameters for scan."""
        # Get deactivated index based on plane selection
        # HK plane means L is fixed (deactivated)
        # HL plane means K is fixed (deactivated)
        # KL plane means H is fixed (deactivated)
        deactivated_index = None
        if self.hk_plane_toggle.isChecked():
            deactivated_index = "L"  # HK plane: L is fixed
        elif self.hl_plane_toggle.isChecked():
            deactivated_index = "K"  # HL plane: K is fixed
        elif self.kl_plane_toggle.isChecked():
            deactivated_index = "H"  # KL plane: H is fixed

        # Get fixed angle
        fixed_angle_name = "chi" if self.fix_chi_btn.isChecked() else "phi"
        fixed_angle_value = (
            self.chi_input.value()
            if self.fix_chi_btn.isChecked()
            else self.phi_input.value()
        )

        # Get ranges
        h_start, h_end = self.h_range.get_range()
        k_start, k_end = self.k_range.get_range()
        l_start, l_end = self.l_range.get_range()

        return {
            "tth": self.tth_input.value(),
            "deactivated_index": deactivated_index,
            "fixed_angle_name": fixed_angle_name,
            "fixed_angle": fixed_angle_value,
            "start_points": (h_start, k_start, l_start),
            "end_points": (h_end, k_end, l_end),
            "num_points": self.num_points.value(),
        }


class HKLScanResultsTable(QTableWidget):
    """Table to display HKL scan results with multiple solutions."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set up table
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["H", "K", "L", "θ (°)", "φ (°)", "χ (°)", "β (°)"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Hide vertical header (row numbers)
        self.verticalHeader().setVisible(False)

        # Define colors for alternating groups white and gray
        self.group_colors = [
            QColor(255, 255, 255),  # White
            QColor(230, 230, 240),  # Gray
            QColor(166, 45, 45),  # Red
        ]

        # Enable sorting
        self.setSortingEnabled(True)

        # Add export button
        self.layout_wrapper = QVBoxLayout()
        self.layout_wrapper.setContentsMargins(0, 0, 0, 0)

        self.export_button = QPushButton("Export to CSV")
        self.export_button.clicked.connect(self.export_to_csv)
        self.export_button.setEnabled(False)  # Initially disabled until we have results

        self.layout_wrapper.addWidget(self)
        self.layout_wrapper.addWidget(self.export_button)

        # Store the last results for export
        self.last_results = None

    def display_results(self, results):
        """Display results in the table."""
        self.setSortingEnabled(False)  # Temporarily disable sorting
        self.setRowCount(0)  # Clear table

        # Check if we have results
        if not results or not results.get("success", False):
            self.export_button.setEnabled(False)
            self.last_results = None
            return

        # Store results for later export
        self.last_results = results
        # Get data from results
        h_values = results["H"]
        k_values = results["K"]
        l_values = results["L"]
        tth_values = results["tth"]
        theta_values = results["theta"]
        phi_values = results["phi"]
        chi_values = results["chi"]

        # Add a row for each result with alternating colors
        for i in range(len(h_values)):
            row_position = self.rowCount()
            self.insertRow(row_position)

            # Add HKL values
            self.setItem(row_position, 0, QTableWidgetItem(f"{h_values[i]:.4f}"))
            self.setItem(row_position, 1, QTableWidgetItem(f"{k_values[i]:.4f}"))
            self.setItem(row_position, 2, QTableWidgetItem(f"{l_values[i]:.4f}"))

            # Add angle values
            self.setItem(row_position, 3, QTableWidgetItem(f"{theta_values[i]:.1f}"))
            self.setItem(row_position, 4, QTableWidgetItem(f"{phi_values[i]:.1f}"))
            self.setItem(row_position, 5, QTableWidgetItem(f"{chi_values[i]:.1f}"))
            self.setItem(row_position, 6, QTableWidgetItem(f"{tth_values[0]-theta_values[i]:.1f}"))

            # Apply alternating row colors
            row_color = self.group_colors[i % 2] if results["feasible"][i] else self.group_colors[2]
            for col in range(self.columnCount()):
                item = self.item(row_position, col)
                if item:
                    item.setBackground(QBrush(row_color))

        # Re-enable sorting and export button
        self.setSortingEnabled(True)
        self.export_button.setEnabled(True)



    def export_to_csv(self):
        """Export results to a CSV file."""
        if not self.last_results:
            QMessageBox.warning(self, "Export Error", "No results to export.")
            return

        # Open file dialog to get save location
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "", "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return  # User cancelled

        # Add .csv extension if not present
        if not file_path.endswith(".csv"):
            file_path += ".csv"

        try:
            with open(file_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)

                # Write header
                writer.writerow(
                    [
                        "H",
                        "K",
                        "L",
                        "tth (deg)",
                        "theta (deg)",
                        "phi (deg)",
                        "chi (deg)",
                    ]
                )

                # Write data
                for i in range(len(self.last_results["tth"])):
                    writer.writerow(
                        [
                            f"{self.last_results['H'][i]:.6f}",
                            f"{self.last_results['K'][i]:.6f}",
                            f"{self.last_results['L'][i]:.6f}",
                            f"{self.last_results['tth'][i]:.6f}",
                            f"{self.last_results['theta'][i]:.6f}",
                            f"{self.last_results['phi'][i]:.6f}",
                            f"{self.last_results['chi'][i]:.6f}",
                        ]
                    )

            QMessageBox.information(
                self, "Export Success", f"Results exported to {file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error", f"Error exporting results: {str(e)}"
            )

    def get_widget(self):
        """Return the widget containing the table and export button."""
        container = QWidget()
        container.setLayout(self.layout_wrapper)
        return container

