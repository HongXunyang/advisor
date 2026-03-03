#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
import numpy as np
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (QButtonGroup, QDoubleSpinBox, QFormLayout,
                             QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSpinBox, QVBoxLayout,
                             QWidget)

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
    """Control panel for checking accessibility of diffraction points."""

    checkAccessibilityClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the accessible region control panel UI."""
        layout = QVBoxLayout(self)

        group = QGroupBox("Accessibility Check")
        group_layout = QVBoxLayout(group)

        # --- Fix chi / Fix phi toggle buttons at the very top ---
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
        group_layout.addWidget(angle_sel)

        # --- Grid layout for all angle rows (ensures column alignment) ---
        # Columns: 0=label  1="min"/spinbox  2=spinbox  3="max"  4=spinbox
        grid = QGridLayout()
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(4, 1)
        group_layout.addLayout(grid)

        r = 0  # row counter

        # Row 0 — 2θ range (always visible)
        self.tth_min = QDoubleSpinBox()
        self.tth_min.setRange(0.0, 180.0)
        self.tth_min.setValue(0.0)
        self.tth_min.setSuffix(" °")
        self.tth_max = QDoubleSpinBox()
        self.tth_max.setRange(0.0, 180.0)
        self.tth_max.setValue(180.0)
        self.tth_max.setSuffix(" °")
        grid.addWidget(QLabel("tth range:"), r, 0)
        grid.addWidget(QLabel("min"), r, 1)
        grid.addWidget(self.tth_min, r, 2)
        grid.addWidget(QLabel("max"), r, 3)
        grid.addWidget(self.tth_max, r, 4)

        r += 1  # Row 1 — θ range (always visible)
        self.theta_min = QDoubleSpinBox()
        self.theta_min.setRange(-180.0, 180.0)
        self.theta_min.setValue(0.0)
        self.theta_min.setSuffix(" °")
        self.theta_max = QDoubleSpinBox()
        self.theta_max.setRange(-180.0, 180.0)
        self.theta_max.setValue(180.0)
        self.theta_max.setSuffix(" °")
        grid.addWidget(QLabel("θ range:"), r, 0)
        grid.addWidget(QLabel("min"), r, 1)
        grid.addWidget(self.theta_min, r, 2)
        grid.addWidget(QLabel("max"), r, 3)
        grid.addWidget(self.theta_max, r, 4)

        r += 1  # Row 2 — χ fixed value (shown when fix chi)
        self.chi_input = QDoubleSpinBox()
        self.chi_input.setRange(-180.0, 180.0)
        self.chi_input.setValue(0.0)
        self.chi_input.setSuffix(" °")
        self._chi_fixed_label = QLabel("χ:")
        grid.addWidget(self._chi_fixed_label, r, 0)
        grid.addWidget(self.chi_input, r, 1, 1, 4)  # span cols 1-4
        self._chi_fixed_widgets = [self._chi_fixed_label, self.chi_input]

        r += 1  # Row 3 — χ range (shown when fix phi)
        self.chi_range_min = QDoubleSpinBox()
        self.chi_range_min.setRange(-180.0, 180.0)
        self.chi_range_min.setValue(0.0)
        self.chi_range_min.setSuffix(" °")
        self.chi_range_max = QDoubleSpinBox()
        self.chi_range_max.setRange(-180.0, 180.0)
        self.chi_range_max.setValue(180.0)
        self.chi_range_max.setSuffix(" °")
        self._chi_range_label = QLabel("χ range:")
        self._chi_range_min_label = QLabel("min")
        self._chi_range_max_label = QLabel("max")
        grid.addWidget(self._chi_range_label, r, 0)
        grid.addWidget(self._chi_range_min_label, r, 1)
        grid.addWidget(self.chi_range_min, r, 2)
        grid.addWidget(self._chi_range_max_label, r, 3)
        grid.addWidget(self.chi_range_max, r, 4)
        self._chi_range_widgets = [
            self._chi_range_label, self._chi_range_min_label,
            self.chi_range_min, self._chi_range_max_label, self.chi_range_max,
        ]

        r += 1  # Row 4 — φ range (shown when fix chi)
        self.phi_range_min = QDoubleSpinBox()
        self.phi_range_min.setRange(-180.0, 180.0)
        self.phi_range_min.setValue(0.0)
        self.phi_range_min.setSuffix(" °")
        self.phi_range_max = QDoubleSpinBox()
        self.phi_range_max.setRange(-180.0, 180.0)
        self.phi_range_max.setValue(180.0)
        self.phi_range_max.setSuffix(" °")
        self._phi_range_label = QLabel("φ range:")
        self._phi_range_min_label = QLabel("min")
        self._phi_range_max_label = QLabel("max")
        grid.addWidget(self._phi_range_label, r, 0)
        grid.addWidget(self._phi_range_min_label, r, 1)
        grid.addWidget(self.phi_range_min, r, 2)
        grid.addWidget(self._phi_range_max_label, r, 3)
        grid.addWidget(self.phi_range_max, r, 4)
        self._phi_range_widgets = [
            self._phi_range_label, self._phi_range_min_label,
            self.phi_range_min, self._phi_range_max_label, self.phi_range_max,
        ]

        r += 1  # Row 5 — φ fixed value (shown when fix phi)
        self.phi_input = QDoubleSpinBox()
        self.phi_input.setRange(-180.0, 180.0)
        self.phi_input.setValue(0.0)
        self.phi_input.setSuffix(" °")
        self._phi_fixed_label = QLabel("φ:")
        grid.addWidget(self._phi_fixed_label, r, 0)
        grid.addWidget(self.phi_input, r, 1, 1, 4)  # span cols 1-4
        self._phi_fixed_widgets = [self._phi_fixed_label, self.phi_input]

        # Check Accessibility button
        self.check_btn = QPushButton("Check Accessibility")
        self.check_btn.clicked.connect(self.checkAccessibilityClicked.emit)
        group_layout.addWidget(self.check_btn)

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

        # Fix chi → show χ fixed + φ range, hide χ range + φ fixed
        for w in self._chi_fixed_widgets:
            w.setVisible(is_chi)
        for w in self._phi_range_widgets:
            w.setVisible(is_chi)
        for w in self._chi_range_widgets:
            w.setVisible(not is_chi)
        for w in self._phi_fixed_widgets:
            w.setVisible(not is_chi)

    def get_parameters(self):
        """Return the current accessibility check parameters.

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
        
    @staticmethod
    def _generate_hkl_cube(h_range, k_range, l_range):
        """Generate a full integer HKL grid covering the given ranges.

        Args:
            h_range: (min, max) inclusive range for H.
            k_range: (min, max) inclusive range for K.
            l_range: (min, max) inclusive range for L.
        """
        cube = []
        for h in range(h_range[0], h_range[1] + 1):
            for k in range(k_range[0], k_range[1] + 1):
                for l in range(l_range[0], l_range[1] + 1):
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

            # Compute the plane HKL points first so we can derive 3D axis ranges
            uv_points, hkl_points = generate_hkl_points_on_plane(U, V, C, u_range, v_range)

            # Determine H, K, L extents from the plane points
            if len(hkl_points) > 0:
                hkl_arr = np.array(hkl_points)
                h_min, k_min, l_min = int(hkl_arr[:, 0].min()), int(hkl_arr[:, 1].min()), int(hkl_arr[:, 2].min())
                h_max, k_max, l_max = int(hkl_arr[:, 0].max()), int(hkl_arr[:, 1].max()), int(hkl_arr[:, 2].max())
            else:
                h_min, k_min, l_min = 0, 0, 0
                h_max, k_max, l_max = 5, 5, 5

            # 3D: generate HKL cube covering the plane extents
            hkl_list = self._generate_hkl_cube(
                (h_min, h_max), (k_min, k_max), (l_min, l_max)
            )
            sf_values = self.calculator.calculate_structure_factors(hkl_list)
            self.plane_3d.visualize_structure_factors(hkl_list, sf_values)

            # Re-apply plane overlay after replot
            self.plane_3d.set_custom_plane(
                U, V, u_min_param, u_max_param, v_min_param, v_max_param, steps=2, center=C
            )

            # 2D: structure factors on the plane
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