#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
from PyQt5.QtWidgets import (
    QWidget,
    QGridLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QSpinBox,
    QLineEdit,
)
from PyQt5.QtCore import pyqtSignal, pyqtSlot
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from advisor.ui.visualizers import StructureFactorVisualizer3D, StructureFactorVisualizer2D
from .hkl_plane_components import EnergySpinBox


class CustomizedPlaneControls(QWidget):
    """Control panel for customized plane visualization with vector inputs."""
    
    initializeClicked = pyqtSignal()
    updatePlotsClicked = pyqtSignal()
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
        self.u_range_spin.setValue(3)
        
        self.v_range_spin = QSpinBox()
        self.v_range_spin.setRange(0, 35)
        self.v_range_spin.setValue(3)
        
        ranges_layout.addWidget(QLabel("U range"))
        ranges_layout.addWidget(self.u_range_spin)
        ranges_layout.addWidget(QLabel("V range"))
        ranges_layout.addWidget(self.v_range_spin)
        config_layout.addRow("", ranges_row)
        
        # Initialize button and status
        self.init_btn = QPushButton("Initialize Calculator")
        self.init_btn.clicked.connect(self.initializeClicked.emit)
        
        self.status_label = QLabel("Status: Provide CIF in initialization window, then initialize")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        config_layout.addRow("", self.status_label)
        
        # Update button (kept for manual refresh if needed)
        self.update_plane_btn = QPushButton("Update Plane & Plots")
        self.update_plane_btn.clicked.connect(self.updatePlotsClicked.emit)
        
        # Put init and update button on the same row
        buttons_row = QWidget()
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(self.init_btn)
        buttons_layout.addWidget(self.update_plane_btn)
        config_layout.addRow("", buttons_row)
        
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
        
        # Left panel: configuration
        self.controls = CustomizedPlaneControls()
        main_layout.addWidget(self.controls, 1, 0)
        
        # 2D plane visualizer below configuration for more space
        self.plane_2d = CustomizedPlane2DWidget()
        main_layout.addWidget(self.plane_2d, 0, 1, 1, 1)
        
        # Right panel: 3D spanning both rows
        self.plane_3d = CustomizedPlane3DWidget()
        main_layout.addWidget(self.plane_3d, 0, 0)

        # Set layout proportions
        main_layout.setColumnStretch(0, 1)  # Left column
        main_layout.setColumnStretch(1, 1)  # Right column
        main_layout.setRowStretch(0, 3)     # More space for visualizers
        main_layout.setRowStretch(1, 1)     # Less space for controls        


        # Connect signals
        self.controls.parametersChanged.connect(self.update_plots)
        self.controls.updatePlotsClicked.connect(self.update_plots)
        
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
        try:
            # Always update the plane overlay for immediate feedback
            U, V, C = self.controls.get_custom_vectors()
            u_max, v_max = self.controls.get_ranges()
            
            # Symmetric parameter ranges around 0; apply center offset in HKL
            u_min_param = -(u_max // 2)
            u_max_param = u_max - (u_max // 2)
            v_min_param = -(v_max // 2)
            v_max_param = v_max - (v_max // 2)
            
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
            
            # 2D: points on the plane using integer combinations of U and V in ranges
            uv_points = []
            hkl_points = []
            # symmetric parameter ranges around 0 with given max steps, shifted by center
            for u in range(u_min_param, u_max_param + 1):
                for v in range(v_min_param, v_max_param + 1):
                    H = C[0] + u * U[0] + v * V[0]
                    K = C[1] + u * U[1] + v * V[1]
                    L = C[2] + u * U[2] + v * V[2]
                    uv_points.append({"u": u, "v": v, "H": H, "K": K, "L": L})
                    hkl_points.append([H, K, L])
                    
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
