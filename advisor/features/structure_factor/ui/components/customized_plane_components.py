#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
import os
import sys

import numpy as np
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (QButtonGroup, QDoubleSpinBox, QFormLayout,
                             QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QVBoxLayout,
                             QWidget)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from advisor.ui.visualizers import (StructureFactorVisualizer2D,
                                    StructureFactorVisualizer3D)

from .hkl_plane_components import EnergySpinBox


class CustomizedPlaneControls(QWidget):
    """Control panel for customized plane visualization with vector inputs."""
    
    initializeClicked = pyqtSignal()
    parametersChanged = pyqtSignal()  # Emitted when any parameter changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the control panel UI."""
        layout = QVBoxLayout(self)
        
        # Configuration group
        config_group = QGroupBox("Configuration")
        # set the width of the group box to 300px
        config_layout = QFormLayout(config_group)
        
        # Energy input (in keV, converted to eV internally)
        self.energy_input = EnergySpinBox()
        config_layout.addRow("X-ray Energy:", self.energy_input)
        
        # Compact U, V, Center in one row using text inputs like 110, 010, 000
        uvc_row = QWidget()
        uvc_layout = QHBoxLayout(uvc_row)
        uvc_layout.setContentsMargins(0, 0, 0, 0)
        
        self.u_line = QLineEdit()
        self.u_line.setPlaceholderText("1,1,0")
        self.u_line.setText("1,1,0")
        
        self.u_line.setFixedWidth(80)
        self.v_line = QLineEdit()
        self.v_line.setPlaceholderText("0,0,1")
        self.v_line.setText("0,0,1")
        self.v_line.setFixedWidth(80)
        
        self.c_line = QLineEdit()
        self.c_line.setPlaceholderText("0,0,0")
        self.c_line.setText("0,0,0")
        self.c_line.setFixedWidth(80)

        uvc_layout.addWidget(QLabel("U"))
        uvc_layout.addWidget(self.u_line)
        uvc_layout.addWidget(QLabel("V"))
        uvc_layout.addWidget(self.v_line)
        uvc_layout.addWidget(QLabel("Center"))
        uvc_layout.addWidget(self.c_line)
        config_layout.addRow("", uvc_row)
        
        # u,v range controls on the same row
        ranges_row = QWidget()
        ranges_layout = QHBoxLayout(ranges_row)
        ranges_layout.setContentsMargins(0, 0, 0, 0)
        
        self.u_range_spin = QSpinBox()
        self.u_range_spin.setRange(0, 35)
        self.u_range_spin.setValue(4)
        
        self.v_range_spin = QSpinBox()
        self.v_range_spin.setRange(0, 35)
        self.v_range_spin.setValue(4)
        
        ranges_layout.addWidget(QLabel("U range"))
        ranges_layout.addWidget(self.u_range_spin)
        ranges_layout.addWidget(QLabel("V range"))
        ranges_layout.addWidget(self.v_range_spin)
        config_layout.addRow("", ranges_row)
        
        # Calculate Structure Factor button and status
        self.init_btn = QPushButton("Calculate Structure Factor")
        self.init_btn.clicked.connect(self.initializeClicked.emit)
        
        self.status_label = QLabel("Status: Provide CIF in initialization window, then initialize")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        config_layout.addRow("", self.status_label)
        
        config_layout.addRow("", self.init_btn)
        
        layout.addWidget(config_group)
        
        # Connect parameter change signals
        self._connect_signals()
        
    def _connect_signals(self):
        """Connect signals for automatic updates."""
        self.u_range_spin.valueChanged.connect(self.parametersChanged.emit)
        self.v_range_spin.valueChanged.connect(self.parametersChanged.emit)
        self.u_line.textChanged.connect(self.parametersChanged.emit)
        self.v_line.textChanged.connect(self.parametersChanged.emit)
        self.c_line.textChanged.connect(self.parametersChanged.emit)
        
    def set_status(self, message: str, color: str = "orange"):
        """Update status label."""
        self.status_label.setText(f"Status: {message}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    def get_energy_ev(self):
        """Get current energy in eV."""
        return self.energy_input.energy_ev
        
    def get_custom_vectors(self):
        """Return U, V, and Center vectors parsed from text inputs.
        
        Expected format: comma-separated values like '1,3,11' for h=1, k=3, l=11.
        Negative values are supported, e.g. '-1,2,-3'.
        """
        def parse_hkl(text: str, default: tuple) -> tuple:
            try:
                # Remove all spaces and split by comma
                parts = text.strip().replace(" ", "").split(",")
                
                # Must have exactly 3 values
                if len(parts) != 3:
                    return default
                
                # Parse each part as an integer (supports negative values)
                vals = []
                for part in parts:
                    if not part:  # Empty string after split
                        return default
                    vals.append(int(part))
                
                return tuple(vals)
            except (ValueError, AttributeError):
                return default
                
        U = parse_hkl(self.u_line.text(), (1, 1, 0))
        V = parse_hkl(self.v_line.text(), (0, 0, 1))
        C = parse_hkl(self.c_line.text(), (0, 0, 0))
        return U, V, C
        
    def get_ranges(self):
        """Get u and v ranges."""
        return self.u_range_spin.value(), self.v_range_spin.value()


class AccessibleRegionControls(QWidget):
    """Control panel for finding accessible diffraction region given angle constraints."""

    findAccessibleClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the accessible region control panel UI."""
        layout = QVBoxLayout(self)

        group = QGroupBox("Accessible Region")
        form = QFormLayout(group)

        # --- tth range ---
        tth_row = QWidget()
        tth_layout = QHBoxLayout(tth_row)
        tth_layout.setContentsMargins(0, 0, 0, 0)
        self.tth_min = QDoubleSpinBox()
        self.tth_min.setRange(0.0, 180.0)
        self.tth_min.setValue(0.0)
        self.tth_min.setSuffix(" °")
        self.tth_max = QDoubleSpinBox()
        self.tth_max.setRange(0.0, 180.0)
        self.tth_max.setValue(180.0)
        self.tth_max.setSuffix(" °")
        tth_layout.addWidget(QLabel("min"))
        tth_layout.addWidget(self.tth_min)
        tth_layout.addWidget(QLabel("max"))
        tth_layout.addWidget(self.tth_max)
        form.addRow("2θ range:", tth_row)

        # --- theta range ---
        theta_row = QWidget()
        theta_layout = QHBoxLayout(theta_row)
        theta_layout.setContentsMargins(0, 0, 0, 0)
        self.theta_min = QDoubleSpinBox()
        self.theta_min.setRange(-180.0, 180.0)
        self.theta_min.setValue(0.0)
        self.theta_min.setSuffix(" °")
        self.theta_max = QDoubleSpinBox()
        self.theta_max.setRange(-180.0, 180.0)
        self.theta_max.setValue(180.0)
        self.theta_max.setSuffix(" °")
        theta_layout.addWidget(QLabel("min"))
        theta_layout.addWidget(self.theta_min)
        theta_layout.addWidget(QLabel("max"))
        theta_layout.addWidget(self.theta_max)
        form.addRow("θ range:", theta_row)

        # --- Fix chi / Fix phi toggle ---
        angle_sel = QWidget()
        angle_sel_layout = QHBoxLayout(angle_sel)
        angle_sel_layout.setContentsMargins(0, 0, 0, 0)

        self.fix_chi_btn = QPushButton("Fix χ")
        self.fix_phi_btn = QPushButton("Fix φ")
        for btn in (self.fix_chi_btn, self.fix_phi_btn):
            btn.setCheckable(True)
        self.fix_chi_btn.setChecked(True)

        self.angle_button_group = QButtonGroup(self)
        self.angle_button_group.addButton(self.fix_chi_btn)
        self.angle_button_group.addButton(self.fix_phi_btn)

        angle_sel_layout.addWidget(self.fix_chi_btn)
        angle_sel_layout.addWidget(self.fix_phi_btn)
        form.addRow("", angle_sel)

        # --- Chi fixed value / Chi range ---
        self.chi_fixed_widget = QWidget()
        chi_fixed_layout = QFormLayout(self.chi_fixed_widget)
        chi_fixed_layout.setContentsMargins(0, 0, 0, 0)
        self.chi_input = QDoubleSpinBox()
        self.chi_input.setRange(-180.0, 180.0)
        self.chi_input.setValue(0.0)
        self.chi_input.setSuffix(" °")
        chi_fixed_layout.addRow("χ:", self.chi_input)

        self.chi_range_widget = QWidget()
        chi_range_layout = QHBoxLayout(self.chi_range_widget)
        chi_range_layout.setContentsMargins(0, 0, 0, 0)
        self.chi_range_min = QDoubleSpinBox()
        self.chi_range_min.setRange(-180.0, 180.0)
        self.chi_range_min.setValue(-180.0)
        self.chi_range_min.setSuffix(" °")
        self.chi_range_max = QDoubleSpinBox()
        self.chi_range_max.setRange(-180.0, 180.0)
        self.chi_range_max.setValue(180.0)
        self.chi_range_max.setSuffix(" °")
        chi_range_layout.addWidget(QLabel("χ min"))
        chi_range_layout.addWidget(self.chi_range_min)
        chi_range_layout.addWidget(QLabel("max"))
        chi_range_layout.addWidget(self.chi_range_max)

        # --- Phi fixed value / Phi range ---
        self.phi_fixed_widget = QWidget()
        phi_fixed_layout = QFormLayout(self.phi_fixed_widget)
        phi_fixed_layout.setContentsMargins(0, 0, 0, 0)
        self.phi_input = QDoubleSpinBox()
        self.phi_input.setRange(-180.0, 180.0)
        self.phi_input.setValue(0.0)
        self.phi_input.setSuffix(" °")
        phi_fixed_layout.addRow("φ:", self.phi_input)

        self.phi_range_widget = QWidget()
        phi_range_layout = QHBoxLayout(self.phi_range_widget)
        phi_range_layout.setContentsMargins(0, 0, 0, 0)
        self.phi_range_min = QDoubleSpinBox()
        self.phi_range_min.setRange(-180.0, 180.0)
        self.phi_range_min.setValue(-180.0)
        self.phi_range_min.setSuffix(" °")
        self.phi_range_max = QDoubleSpinBox()
        self.phi_range_max.setRange(-180.0, 180.0)
        self.phi_range_max.setValue(180.0)
        self.phi_range_max.setSuffix(" °")
        phi_range_layout.addWidget(QLabel("φ min"))
        phi_range_layout.addWidget(self.phi_range_min)
        phi_range_layout.addWidget(QLabel("max"))
        phi_range_layout.addWidget(self.phi_range_max)

        # Container for the angle-dependent rows
        angle_values = QWidget()
        angle_values_layout = QVBoxLayout(angle_values)
        angle_values_layout.setContentsMargins(0, 0, 0, 0)
        angle_values_layout.addWidget(self.chi_fixed_widget)
        angle_values_layout.addWidget(self.chi_range_widget)
        angle_values_layout.addWidget(self.phi_fixed_widget)
        angle_values_layout.addWidget(self.phi_range_widget)
        form.addRow("", angle_values)

        # Find button
        self.find_btn = QPushButton("Find Accessible Region")
        self.find_btn.clicked.connect(self.findAccessibleClicked.emit)
        form.addRow("", self.find_btn)

        layout.addWidget(group)

        # Connect toggle buttons
        self.fix_chi_btn.clicked.connect(lambda: self._set_active_fixed_angle("chi"))
        self.fix_phi_btn.clicked.connect(lambda: self._set_active_fixed_angle("phi"))

        # Initialize UI state
        self._set_active_fixed_angle("chi")

    def _set_active_fixed_angle(self, angle: str):
        """Update visibility and button styles based on fixed angle selection."""
        is_chi = angle == "chi"

        # Update button styles
        for name, btn in [("chi", self.fix_chi_btn), ("phi", self.fix_phi_btn)]:
            if name == angle:
                btn.setChecked(True)
                btn.setProperty("class", "activeToggle")
            else:
                btn.setChecked(False)
                btn.setProperty("class", "inactiveToggle")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Fix chi → show chi single input, phi range
        self.chi_fixed_widget.setVisible(is_chi)
        self.phi_range_widget.setVisible(is_chi)
        # Fix phi → show phi single input, chi range
        self.phi_fixed_widget.setVisible(not is_chi)
        self.chi_range_widget.setVisible(not is_chi)

    def get_parameters(self):
        """Return the current accessible region parameters.

        Returns:
            dict with keys: tth_min, tth_max, theta_min, theta_max,
                fixed_angle_name, fixed_angle_value,
                chi_min, chi_max, phi_min, phi_max
        """
        is_chi_fixed = self.fix_chi_btn.isChecked()
        if is_chi_fixed:
            fixed_angle_name = "chi"
            fixed_angle_value = self.chi_input.value()
            chi_min = self.chi_input.value()
            chi_max = self.chi_input.value()
            phi_min = self.phi_range_min.value()
            phi_max = self.phi_range_max.value()
        else:
            fixed_angle_name = "phi"
            fixed_angle_value = self.phi_input.value()
            phi_min = self.phi_input.value()
            phi_max = self.phi_input.value()
            chi_min = self.chi_range_min.value()
            chi_max = self.chi_range_max.value()

        return {
            "tth_min": self.tth_min.value(),
            "tth_max": self.tth_max.value(),
            "theta_min": self.theta_min.value(),
            "theta_max": self.theta_max.value(),
            "fixed_angle_name": fixed_angle_name,
            "fixed_angle_value": fixed_angle_value,
            "chi_min": chi_min,
            "chi_max": chi_max,
            "phi_min": phi_min,
            "phi_max": phi_max,
        }


class CustomizedPlane3DWidget(QWidget):
    """3D visualization widget for customized plane with overlay."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the 3D widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create group box
        self.visualizer3d = StructureFactorVisualizer3D()
        
        layout.addWidget(self.visualizer3d)
        
    def visualize_structure_factors(self, hkl_list, sf_values):
        """Visualize structure factors in 3D."""
        self.visualizer3d.visualize_structure_factors(hkl_list, np.abs(sf_values))
        
    def set_custom_plane(self, U, V, u_min, u_max, v_min, v_max, steps=2, center=(0, 0, 0)):
        """Set custom plane overlay."""
        try:
            self.visualizer3d.set_custom_plane(
                U, V, u_min, u_max, v_min, v_max, steps, center
            )
        except Exception as e:
            print(f"Error setting custom plane: {e}")
            
    def clear_plot(self):
        """Clear the 3D plot."""
        self.visualizer3d.clear_plot()


class CustomizedPlane2DWidget(QWidget):
    """2D visualization widget for customized UV plane."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the 2D widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.visualizer2d = StructureFactorVisualizer2D()
        layout.addWidget(self.visualizer2d)
        
    def visualize_uv_plane_points(self, uv_points, sf_values, u_label, v_label, 
                                  vector_center=(0, 0, 0), value_max=None):
        """Visualize UV plane points."""
        self.visualizer2d.visualize_uv_plane_points(
            uv_points, sf_values, u_label, v_label, vector_center, value_max
        )
        
    def clear_plot(self):
        """Clear the 2D plot."""
        self.visualizer2d.clear_plot()


class CustomizedPlaneWidget(QWidget):
    """Complete customized plane widget combining controls and visualizations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.calculator = None  # Will be set by parent
        self.init_ui()
        
    def init_ui(self):
        """Initialize the complete widget."""
        main_layout = QGridLayout(self)
        
        # Left panel: configuration (bottom-left)
        self.controls = CustomizedPlaneControls()
        main_layout.addWidget(self.controls, 1, 0)
        
        # Right panel: accessible region controls (bottom-right)
        self.accessible_controls = AccessibleRegionControls()
        main_layout.addWidget(self.accessible_controls, 1, 1)
        
        # 2D plane visualizer (top-right)
        self.plane_2d = CustomizedPlane2DWidget()
        main_layout.addWidget(self.plane_2d, 0, 1, 1, 1)
        
        # 3D visualizer (top-left)
        self.plane_3d = CustomizedPlane3DWidget()
        main_layout.addWidget(self.plane_3d, 0, 0)

        # Set layout proportions
        main_layout.setColumnStretch(0, 1)  # Left column
        main_layout.setColumnStretch(1, 1)  # Right column
        main_layout.setRowStretch(0, 3)     # More space for visualizers
        main_layout.setRowStretch(1, 1)     # Less space for controls        

        # Connect signals
        self.controls.parametersChanged.connect(self.update_plots)
        
    def set_calculator(self, calculator):
        """Set the calculator instance."""
        self.calculator = calculator
        
    def get_controls(self):
        """Get the controls widget."""
        return self.controls
        
    def _generate_hkl_cube(self, max_index: int = 5):
        """Generate a full integer HKL grid from 0..max_index for 3D visualization."""
        cube = []
        for h in range(0, max_index + 1):
            for k in range(0, max_index + 1):
                for l in range(0, max_index + 1):
                    cube.append([h, k, l])
        return cube
        
    @pyqtSlot()
    def update_plots(self):
        """Update 3D scatter (all HKL) with a custom plane overlay and 2D uv plot."""
        from advisor.features.structure_factor.domain import \
            generate_hkl_points_on_plane

        try:
            # Always update the plane overlay for immediate feedback
            U, V, C = self.controls.get_custom_vectors()
            u_range, v_range = self.controls.get_ranges()

            # Symmetric parameter ranges around 0; apply center offset in HKL
            u_min_param = -(u_range // 2)
            u_max_param = u_range - (u_range // 2)
            v_min_param = -(v_range // 2)
            v_max_param = v_range - (v_range // 2)

            # Update plane overlay
            self.plane_3d.set_custom_plane(
                U, V, u_min_param, u_max_param, v_min_param, v_max_param, steps=2, center=C
            )

            if not self.calculator or not self.calculator.is_initialized:
                return

            # 3D: plot all HKL points 0..5
            hkl_list = self._generate_hkl_cube(5)
            sf_values = self.calculator.calculate_structure_factors(hkl_list)
            self.plane_3d.visualize_structure_factors(hkl_list, sf_values)

            # Re-apply plane overlay after replot
            self.plane_3d.set_custom_plane(
                U, V, u_min_param, u_max_param, v_min_param, v_max_param, steps=2, center=C
            )

            # 2D: points on the plane using shared domain function
            uv_points, hkl_points = generate_hkl_points_on_plane(U, V, C, u_range, v_range)

            if len(hkl_points) > 0:
                sf_plane = self.calculator.calculate_structure_factors(hkl_points)
                # Reference value for sizing: use |F(0,0,0)| for consistency
                ref = self.calculator.calculate_structure_factors([[0, 0, 0]])
                value_max = (
                    float(np.abs(ref[0]))
                    if len(ref) > 0
                    else (
                        float(np.max(np.abs(sf_plane))) if len(sf_plane) > 0 else None
                    )
                )
                u_label = f"[{U[0]} {U[1]} {U[2]}]"
                v_label = f"[{V[0]} {V[1]} {V[2]}]"
                self.plane_2d.visualize_uv_plane_points(
                    uv_points, np.abs(sf_plane), u_label, v_label, vector_center=C, value_max=value_max
                )

        except Exception as e:
            # Keep UI responsive
            print(f"Error updating customized plots: {e}")
            
    def clear_plots(self):
        """Clear all plots."""
        self.plane_2d.clear_plot()
        self.plane_3d.clear_plot()

    def get_energy_ev(self):
        """Get the energy in eV."""
        return self.controls.get_energy_ev()