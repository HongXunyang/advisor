#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dialog for importing orientation from diffraction test data."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QDoubleSpinBox, QFormLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QVBoxLayout)

from advisor.domain.orientation import fit_orientation_from_diffraction_tests


class DiffractionTestDialog(QDialog):
    """Dialog for entering diffraction test data and calculating orientation.

    This dialog allows users to input multiple diffraction tests (H, K, L, energy,
    tth, theta, phi, chi) and calculates the optimal Euler angles (roll, pitch, yaw)
    that best fit the data.
    """

    def __init__(self, lattice_params: dict, parent=None):
        """Initialize the dialog.

        Args:
            lattice_params: Dictionary containing lattice parameters (a, b, c, alpha, beta, gamma)
            parent: Parent widget
        """
        super().__init__(parent)
        self.lattice_params = lattice_params
        self.result = None  # Will store (roll, pitch, yaw) on success

        self.setWindowTitle("Import Orientation from Diffraction Tests")
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)

        # Instructions label
        instructions = QLabel(
            "Enter diffraction test data below. Each row represents a measurement "
            "with known HKL indices and measured angles. At least one test is required."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Table for diffraction tests
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["H", "K", "L", "Energy (eV)", "tth (°)", "θ (°)", "φ (°)", "χ (°)"]
        )

        # Set column resize mode
        header = self.table.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        # Add initial empty rows
        self._add_row()
        self._add_row()

        layout.addWidget(self.table)

        # Row management buttons
        row_buttons_layout = QHBoxLayout()

        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(self._add_row)
        row_buttons_layout.addWidget(add_row_btn)

        remove_row_btn = QPushButton("Remove Selected Row")
        remove_row_btn.clicked.connect(self._remove_selected_row)
        row_buttons_layout.addWidget(remove_row_btn)

        row_buttons_layout.addStretch()
        layout.addLayout(row_buttons_layout)

        # Results display area
        self.results_group = QGroupBox("Calculated Orientation")
        results_layout = QFormLayout(self.results_group)

        self.roll_result = QDoubleSpinBox()
        self.roll_result.setRange(-180, 180)
        self.roll_result.setDecimals(4)
        self.roll_result.setReadOnly(True)
        self.roll_result.setSuffix(" °")
        results_layout.addRow("Roll:", self.roll_result)

        self.pitch_result = QDoubleSpinBox()
        self.pitch_result.setRange(-180, 180)
        self.pitch_result.setDecimals(4)
        self.pitch_result.setReadOnly(True)
        self.pitch_result.setSuffix(" °")
        results_layout.addRow("Pitch:", self.pitch_result)

        self.yaw_result = QDoubleSpinBox()
        self.yaw_result.setRange(-180, 180)
        self.yaw_result.setDecimals(4)
        self.yaw_result.setReadOnly(True)
        self.yaw_result.setSuffix(" °")
        results_layout.addRow("Yaw:", self.yaw_result)

        self.error_label = QLabel("Residual Error: --")
        results_layout.addRow(self.error_label)

        self.results_group.setVisible(False)
        layout.addWidget(self.results_group)

        # Action buttons
        button_layout = QHBoxLayout()

        self.calculate_btn = QPushButton("Calculate Orientation")
        self.calculate_btn.clicked.connect(self._calculate_orientation)
        button_layout.addWidget(self.calculate_btn)

        self.apply_btn = QPushButton("Apply and Close")
        self.apply_btn.clicked.connect(self._apply_and_close)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _add_row(self):
        """Add a new empty row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Set default values
        defaults = [0.0, 0.0, 0.0, 930.0, 90.0, 45.0, 0.0, 0.0]
        for col, default in enumerate(defaults):
            item = QTableWidgetItem(str(default))
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

    def _get_diffraction_tests(self) -> list:
        """Extract diffraction test data from the table.

        Returns:
            List of dictionaries containing test data, or None if validation fails.
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
                    "phi": float(self.table.item(row, 6).text()),
                    "chi": float(self.table.item(row, 7).text()),
                }
                tests.append(test)
            except (ValueError, AttributeError) as e:
                QMessageBox.warning(
                    self,
                    "Invalid Input",
                    f"Row {row + 1} contains invalid data. Please enter numeric values.\n\nError: {e}",
                )
                return None

        if not tests:
            QMessageBox.warning(
                self,
                "No Data",
                "Please enter at least one diffraction test.",
            )
            return None

        return tests

    def _calculate_orientation(self):
        """Calculate the optimal orientation from the entered data."""
        tests = self._get_diffraction_tests()
        if tests is None:
            return

        # Run the fitting algorithm
        result = fit_orientation_from_diffraction_tests(
            self.lattice_params, tests
        )

        if not result["success"]:
            QMessageBox.warning(
                self,
                "Calculation Failed",
                f"Failed to calculate orientation:\n\n{result.get('message', 'Unknown error')}",
            )
            return

        # Display results
        self.roll_result.setValue(result["roll"])
        self.pitch_result.setValue(result["pitch"])
        self.yaw_result.setValue(result["yaw"])
        self.error_label.setText(f"Residual Error: {result['residual_error']:.6f}")

        self.results_group.setVisible(True)
        self.apply_btn.setEnabled(True)

        # Store result for later retrieval
        self.result = {
            "roll": result["roll"],
            "pitch": result["pitch"],
            "yaw": result["yaw"],
        }

        # Show detailed errors if available
        if result.get("individual_errors"):
            error_text = "Individual test errors:\n"
            for i, err in enumerate(result["individual_errors"]):
                error_text += (
                    f"  Test {i+1}: ΔH={err['H_error']:.4f}, "
                    f"ΔK={err['K_error']:.4f}, ΔL={err['L_error']:.4f}\n"
                )
            QMessageBox.information(
                self,
                "Calculation Complete",
                f"Orientation calculated successfully!\n\n"
                f"Roll: {result['roll']:.4f}°\n"
                f"Pitch: {result['pitch']:.4f}°\n"
                f"Yaw: {result['yaw']:.4f}°\n\n"
                f"Residual Error: {result['residual_error']:.6f}\n\n"
                f"{error_text}",
            )

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

    def get_result(self) -> dict:
        """Get the calculated orientation.

        Returns:
            Dictionary with roll, pitch, yaw values, or None if not calculated.
        """
        return self.result
