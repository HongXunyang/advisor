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
    QSlider,
    QStackedLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from advisor.ui.visualizers import StructureFactorVisualizer3D, StructureFactorVisualizer2D


class EnergySpinBox(QWidget):
    """Custom spinbox that displays keV but stores/returns eV internally."""
    
    valueChanged = pyqtSignal(float)  # Emits energy in eV
    
    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt5.QtWidgets import QDoubleSpinBox
        
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(0.001, 1000.0)  # keV range: 1 eV to 100 keV
        self.spinbox.setDecimals(3)  # More precision for keV
        self.spinbox.setSuffix(" keV")
        self.spinbox.setValue(100.0)  # 10 keV default
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spinbox)
        
        # Connect signal
        self.spinbox.valueChanged.connect(lambda v: self.valueChanged.emit(v * 1000.0))
    
    @property
    def energy_ev(self):
        """Get energy value in eV (internal storage unit)."""
        return self.spinbox.value() * 1000.0
    
    @energy_ev.setter
    def energy_ev(self, value_ev):
        """Set energy value from eV (converts to keV for display)."""
        self.spinbox.setValue(value_ev / 1000.0)


class HKLPlaneControls(QWidget):
    """Control panel for HKL plane visualization with energy input and plane toggles."""
    
    initializeClicked = pyqtSignal()
    planeChanged = pyqtSignal(str)  # Emits "HK", "HL", or "KL"
    energyChanged = pyqtSignal(float)  # Emits energy in eV
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the control panel UI."""
        layout = QVBoxLayout(self)
        
        # Configuration group
        config_group = QGroupBox("Configuration")
        config_layout = QFormLayout(config_group)
        
        # Energy input
        self.energy_input = EnergySpinBox()
        self.energy_input.valueChanged.connect(self.energyChanged.emit)
        config_layout.addRow("X-ray Energy:", self.energy_input)
        
        # Plane toggle buttons
        self.hk_toggle_btn = QPushButton("HK plane")
        self.hl_toggle_btn = QPushButton("HL plane")
        self.kl_toggle_btn = QPushButton("KL plane")
        
        for btn in (self.hk_toggle_btn, self.hl_toggle_btn, self.kl_toggle_btn):
            btn.setCheckable(True)
            
        self.hk_toggle_btn.clicked.connect(lambda: self._on_plane_clicked("HK"))
        self.hl_toggle_btn.clicked.connect(lambda: self._on_plane_clicked("HL"))
        self.kl_toggle_btn.clicked.connect(lambda: self._on_plane_clicked("KL"))
        
        # Add plane toggle row
        toggle_row = QWidget()
        toggle_layout = QHBoxLayout(toggle_row)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.addWidget(self.hk_toggle_btn)
        toggle_layout.addWidget(self.hl_toggle_btn)
        toggle_layout.addWidget(self.kl_toggle_btn)
        config_layout.addRow("Plane:", toggle_row)
        
        # Initialize button
        self.init_btn = QPushButton("Initialize Calculator")
        self.init_btn.clicked.connect(self.initializeClicked.emit)
        config_layout.addRow("", self.init_btn)
        
        # Status label
        self.status_label = QLabel("Status: Provide CIF in initialization window, then initialize")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        config_layout.addRow("", self.status_label)
        
        layout.addWidget(config_group)
        
        # Default to HK plane
        self._on_plane_clicked("HK")
        
    def _on_plane_clicked(self, plane: str):
        """Handle plane toggle button clicks."""
        self._update_toggle_styles(plane)
        self.planeChanged.emit(plane)
        
    def _update_toggle_styles(self, active: str):
        """Update toggle button colors based on active plane."""
        active_css = "background-color: #2ecc71; color: white; font-weight: bold;"
        inactive_css = "background-color: #bdc3c7; color: #333333;"
        mapping = {
            "HK": self.hk_toggle_btn,
            "HL": self.hl_toggle_btn,
            "KL": self.kl_toggle_btn,
        }
        for name, btn in mapping.items():
            if name == active:
                btn.setChecked(True)
                btn.setStyleSheet(active_css)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(inactive_css)
                
    def set_status(self, message: str, color: str = "orange"):
        """Update status label."""
        self.status_label.setText(f"Status: {message}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    def get_energy_ev(self):
        """Get current energy in eV."""
        return self.energy_input.energy_ev


class HKLPlane3DWidget(QWidget):
    """3D visualization widget for HKL structure factors with plane overlays."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the 3D widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.visualizer3d = StructureFactorVisualizer3D()
        layout.addWidget(self.visualizer3d)
        
    def initialize(self, params):
        """Initialize the 3D visualizer."""
        self.visualizer3d.initialize(params)
        
    def visualize_structure_factors(self, hkl_list, sf_values):
        """Visualize structure factors in 3D."""
        self.visualizer3d.visualize_structure_factors(hkl_list, np.abs(sf_values))
        
    def set_plane_values(self, **kwargs):
        """Set plane overlay values."""
        self.visualizer3d.set_plane_values(**kwargs)
        
    def set_active_plane(self, plane_axis: str):
        """Set which plane is highlighted."""
        self.visualizer3d.set_active_plane(plane_axis)


class FixedIndexControls(QWidget):
    """Controls for a single fixed index (spin box + slider)."""
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, label_prefix: str, fixed_name: str, default_value: int = 0, parent=None):
        super().__init__(parent)
        self.fixed_name = fixed_name
        self.init_ui(label_prefix, fixed_name, default_value)
        
    def init_ui(self, label_prefix: str, fixed_name: str, default_value: int):
        """Initialize the controls."""
        layout = QVBoxLayout(self)
        
        # Group box
        self.group = QGroupBox(f"{label_prefix}")
        group_layout = QFormLayout(self.group)
        
        # Controls row
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Spin box
        self.spin = QSpinBox()
        self.spin.setRange(0, 35)
        self.spin.setValue(default_value)
        
        # Slider
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setRange(0, 35)
        self.slider.setValue(default_value)
        
        row_layout.addWidget(self.spin)
        row_layout.addWidget(self.slider)
        group_layout.addRow(f"{fixed_name}:", row)
        
        layout.addWidget(self.group)
        
        # Connect signals
        self.spin.valueChanged.connect(self._on_spin_changed)
        self.slider.valueChanged.connect(self._on_slider_changed)
        
    def _on_spin_changed(self, value):
        """Handle spin box value change."""
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.valueChanged.emit(value)
        
    def _on_slider_changed(self, value):
        """Handle slider value change."""
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self.valueChanged.emit(value)
        
    def get_value(self):
        """Get current value."""
        return self.spin.value()
        
    def set_value(self, value):
        """Set value programmatically."""
        self.spin.setValue(value)


class HKLPlane2DWidget(QWidget):
    """Widget containing stacked 2D plane visualizers with individual controls."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_max = 5  # inclusive max for varying integer indices
        self.init_ui()
        
    def init_ui(self):
        """Initialize the 2D widget with stacked layout."""
        main_layout = QGridLayout(self)
        
        # Create 2D visualizers
        self.hk_visualizer = StructureFactorVisualizer2D()
        self.hl_visualizer = StructureFactorVisualizer2D()
        self.kl_visualizer = StructureFactorVisualizer2D()
        
        # Create control widgets
        self.hk_controls = FixedIndexControls("HK plane", "L", 0)
        self.hl_controls = FixedIndexControls("HL plane", "K", 0)
        self.kl_controls = FixedIndexControls("KL plane", "H", 0)
        
        # Plane stack (top)
        self.plane_stack_container = QWidget()
        self.plane_stack = QStackedLayout(self.plane_stack_container)
        self.plane_stack.addWidget(self.hk_visualizer)
        self.plane_stack.addWidget(self.hl_visualizer)
        self.plane_stack.addWidget(self.kl_visualizer)
        main_layout.addWidget(self.plane_stack_container, 0, 0)
        
        # Control stack (bottom)
        self.ctrl_stack_container = QWidget()
        self.ctrl_stack = QStackedLayout(self.ctrl_stack_container)
        self.ctrl_stack.addWidget(self.hk_controls)
        self.ctrl_stack.addWidget(self.hl_controls)
        self.ctrl_stack.addWidget(self.kl_controls)
        main_layout.addWidget(self.ctrl_stack_container, 1, 0)
        
        # Set layout proportions
        main_layout.setRowStretch(0, 3)  # More space for visualizer
        main_layout.setRowStretch(1, 1)  # Less space for controls
        
        # Default to HK plane
        self.set_active_plane("HK")
        
    def set_active_plane(self, plane: str):
        """Set which plane is visible."""
        plane = plane.upper()
        index_map = {"HK": 0, "HL": 1, "KL": 2}
        idx = index_map.get(plane, 0)
        self.plane_stack.setCurrentIndex(idx)
        self.ctrl_stack.setCurrentIndex(idx)
        
    def connect_value_changed_signals(self, hk_callback, hl_callback, kl_callback):
        """Connect value changed signals to callbacks."""
        self.hk_controls.valueChanged.connect(hk_callback)
        self.hl_controls.valueChanged.connect(hl_callback)
        self.kl_controls.valueChanged.connect(kl_callback)
        
    def connect_3d_plane_signals(self, plane_3d_widget):
        """Connect control changes to 3D plane updates."""
        self.hk_controls.valueChanged.connect(
            lambda v: plane_3d_widget.set_plane_values(L=int(v))
        )
        self.hl_controls.valueChanged.connect(
            lambda v: plane_3d_widget.set_plane_values(K=int(v))
        )
        self.kl_controls.valueChanged.connect(
            lambda v: plane_3d_widget.set_plane_values(H=int(v))
        )
        
    def get_plane_values(self):
        """Get current plane control values."""
        return {
            "L": self.hk_controls.get_value(),
            "K": self.hl_controls.get_value(),
            "H": self.kl_controls.get_value(),
        }
        
    def _generate_plane_points(self, varying_a: str, varying_b: str, fixed_name: str, fixed_value: int):
        """Create integer HKL points for a plane with two varying indices in [0, grid_max]."""
        points = []
        for a in range(0, self.grid_max + 1):
            for b in range(0, self.grid_max + 1):
                values = {"H": 0, "K": 0, "L": 0}
                values[varying_a] = a
                values[varying_b] = b
                values[fixed_name] = fixed_value
                points.append([values["H"], values["K"], values["L"]])
        return points
        
    def update_hk_plane(self, calculator):
        """Update HK plane visualization."""
        if not calculator.is_initialized:
            return
        L_val = self.hk_controls.get_value()
        hkl_list = self._generate_plane_points("H", "K", "L", L_val)
        results = calculator.calculate_structure_factors(hkl_list)
        # Reference value for color scale
        ref = calculator.calculate_structure_factors([[0, 0, 0]])
        value_max = float(np.abs(ref[0])) if len(ref) > 0 else None
        arr = np.array(hkl_list)
        self.hk_visualizer.visualize_plane(
            arr[:, 0], arr[:, 1], np.abs(results), "H", "K", "L", L_val, value_max
        )
        
    def update_hl_plane(self, calculator):
        """Update HL plane visualization."""
        if not calculator.is_initialized:
            return
        K_val = self.hl_controls.get_value()
        hkl_list = self._generate_plane_points("H", "L", "K", K_val)
        results = calculator.calculate_structure_factors(hkl_list)
        # Reference value for color scale
        ref = calculator.calculate_structure_factors([[0, 0, 0]])
        value_max = float(np.abs(ref[0])) if len(ref) > 0 else None
        arr = np.array(hkl_list)
        self.hl_visualizer.visualize_plane(
            arr[:, 0], arr[:, 2], np.abs(results), "H", "L", "K", K_val, value_max
        )
        
    def update_kl_plane(self, calculator):
        """Update KL plane visualization."""
        if not calculator.is_initialized:
            return
        H_val = self.kl_controls.get_value()
        hkl_list = self._generate_plane_points("K", "L", "H", H_val)
        results = calculator.calculate_structure_factors(hkl_list)
        # Reference value for color scale
        ref = calculator.calculate_structure_factors([[0, 0, 0]])
        value_max = float(np.abs(ref[0])) if len(ref) > 0 else None
        arr = np.array(hkl_list)
        self.kl_visualizer.visualize_plane(
            arr[:, 1], arr[:, 2], np.abs(results), "K", "L", "H", H_val, value_max
        )
        
    def clear_plots(self):
        """Clear all plane visualizations."""
        self.hk_visualizer.clear_plot()
        self.hl_visualizer.clear_plot()
        self.kl_visualizer.clear_plot()
