#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QLineEdit,
)
from PyQt5.QtCore import pyqtSignal


class AnglesToHKLControls(QWidget):
    """Widget for Angles to HKL calculation controls."""

    # Signal emitted when calculate button is clicked
    calculateClicked = pyqtSignal()
    # Signal emitted when any angle value changes
    anglesChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Input form
        form_group = QGroupBox("Scattering Angles")
        form_layout = QFormLayout(form_group)

        # tth input
        self.tth_input = QDoubleSpinBox()
        self.tth_input.setRange(0.0, 180.0)
        self.tth_input.setValue(150.0)
        self.tth_input.setSuffix(" °")
        self.tth_input.valueChanged.connect(self.anglesChanged.emit)
        form_layout.addRow("tth:", self.tth_input)

        # theta input
        self.theta_input = QDoubleSpinBox()
        self.theta_input.setRange(-180.0, 180.0)
        self.theta_input.setValue(50.0)
        self.theta_input.setSuffix(" °")
        self.theta_input.valueChanged.connect(self.anglesChanged.emit)
        form_layout.addRow("θ:", self.theta_input)

        # phi input
        self.phi_input = QDoubleSpinBox()
        self.phi_input.setRange(-180.0, 180.0)
        self.phi_input.setValue(0.0)
        self.phi_input.setSuffix(" °")
        self.phi_input.valueChanged.connect(self.anglesChanged.emit)
        form_layout.addRow("φ:", self.phi_input)

        # chi input
        self.chi_input = QDoubleSpinBox()
        self.chi_input.setRange(-180.0, 180.0)
        self.chi_input.setValue(0.0)
        self.chi_input.setSuffix(" °")
        self.chi_input.valueChanged.connect(self.anglesChanged.emit)
        form_layout.addRow("χ:", self.chi_input)

        main_layout.addWidget(form_group)

        # Calculate button
        self.calculate_button = QPushButton("Calculate HKL")
        self.calculate_button.clicked.connect(self.calculateClicked.emit)
        self.calculate_button.setObjectName("calculateHKLButton")
        main_layout.addWidget(self.calculate_button)

    def get_calculation_parameters(self):
        """Get parameters for HKL calculation."""
        return {
            "tth": self.tth_input.value(),
            "theta": self.theta_input.value(),
            "phi": self.phi_input.value(),
            "chi": self.chi_input.value(),
        }

    def set_values(self, tth=None, theta=None, phi=None, chi=None):
        """Set input values programmatically."""
        if tth is not None:
            self.tth_input.setValue(tth)
        if theta is not None:
            self.theta_input.setValue(theta)
        if phi is not None:
            self.phi_input.setValue(phi)
        if chi is not None:
            self.chi_input.setValue(chi)


class AnglesToHKLResults(QWidget):
    """Widget for displaying Angles to HKL calculation results."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Results group
        results_group = QGroupBox("Results")
        results_layout = QFormLayout(results_group)

        # H result
        self.H_result = QLineEdit()
        self.H_result.setReadOnly(True)
        results_layout.addRow("H:", self.H_result)

        # K result
        self.K_result = QLineEdit()
        self.K_result.setReadOnly(True)
        results_layout.addRow("K:", self.K_result)

        # L result
        self.L_result = QLineEdit()
        self.L_result.setReadOnly(True)
        results_layout.addRow("L:", self.L_result)

        main_layout.addWidget(results_group)

    def display_results(self, results):
        """Display calculation results."""
        if results and results.get("success", False):
            self.H_result.setText(f"{results['H']:.4f}")
            self.K_result.setText(f"{results['K']:.4f}")
            self.L_result.setText(f"{results['L']:.4f}")
        else:
            self.clear_results()

    def clear_results(self):
        """Clear all results."""
        self.H_result.clear()
        self.K_result.clear()
        self.L_result.clear()

    def get_results(self):
        """Get current results as a dictionary."""
        try:
            return {
                "H": float(self.H_result.text()) if self.H_result.text() else None,
                "K": float(self.K_result.text()) if self.K_result.text() else None,
                "L": float(self.L_result.text()) if self.L_result.text() else None,
            }
        except ValueError:
            return {"H": None, "K": None, "L": None}
