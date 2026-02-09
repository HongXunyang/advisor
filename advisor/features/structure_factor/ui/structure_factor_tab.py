#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=no-name-in-module, import-error
import os

import numpy as np
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QGridLayout, QMessageBox, QTabWidget, QWidget

from advisor.features.structure_factor.domain import StructureFactorCalculator
from advisor.ui.tab_interface import TabInterface
from advisor.ui.tips import Tips, set_tip

from .components import (CustomizedPlaneWidget, HKLPlane2DWidget,
                         HKLPlane3DWidget, HKLPlaneControls)


class StructureFactorTab(TabInterface):
    """Tab for calculating structure factors using X-ray scattering."""

    def __init__(self, controller=None, calculator=None):
        self.controller = controller
        self.calculator = calculator or StructureFactorCalculator()
        self.tips = Tips()

        # Initialize UI first
        main_window = controller.app_controller.main_window if controller else None
        super().__init__(controller=controller, main_window=main_window)
        self.setWindowTitle("Structure Factor Calculator")

    def init_ui(self):
        """Initialize UI components with subtabs."""
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget, 0, 0)

        self._create_hkl_plane_tab()
        self._create_customized_tab()

    def set_parameters(self, params: dict):
        """Set parameters from global lattice configuration.

        Note: Structure factor calculator requires CIF file and energy,
        which are not part of the global lattice parameters.
        """
        if not params:
            return
        # Initialize visualizers through components
        if hasattr(self, 'hkl_plane_3d'):
            self.hkl_plane_3d.initialize(params)
        
        # Clear all plots
        if hasattr(self, 'hkl_plane_2d'):
            self.hkl_plane_2d.clear_plots()
        if hasattr(self, 'customized_plane_widget'):
            self.customized_plane_widget.clear_plots()

        # Auto-populate U, V, Center, and energy from ub_data if exactly 2 entries
        ub_data = params.get("ub_data")
        if ub_data and len(ub_data) == 2 and hasattr(self, 'customized_plane_widget'):
            controls = self.customized_plane_widget.get_controls()
            try:
                d0 = ub_data[0]
                d1 = ub_data[1]
                h0, k0, l0 = d0["H"], d0["K"], d0["L"]
                h1, k1, l1 = d1["H"], d1["K"], d1["L"]

                controls.u_line.setText(f"{int(h0)},{int(k0)},{int(l0)}")
                controls.v_line.setText(f"{int(h1)},{int(k1)},{int(l1)}")

                # Center = mean of U and V, rounded to int
                ch = int(round((h0 + h1) / 2.0))
                ck = int(round((k0 + k1) / 2.0))
                cl = int(round((l0 + l1) / 2.0))
                controls.c_line.setText(f"{ch},{ck},{cl}")

                # Prefill X-ray energy from first test (energy is in eV)
                energy_ev = d0.get("energy")
                if energy_ev is not None:
                    controls.energy_input.energy_ev = float(energy_ev)
            except (KeyError, TypeError, ValueError):
                pass  # keep defaults if ub_data is malformed

    def _set_tip(self, widget, name):
        """Set the tooltip and status tip for a widget by the name"""
        set_tip(widget, self.tips.tip(name))

    def _create_hkl_plane_tab(self):
        """Create the HKL plane subtab using components."""
        hkl_tab = QWidget()
        main_layout = QGridLayout(hkl_tab)

        # Create components
        self.hkl_controls = HKLPlaneControls()
        self.hkl_plane_3d = HKLPlane3DWidget()
        self.hkl_plane_2d = HKLPlane2DWidget()

        # Layout components
        main_layout.addWidget(self.hkl_plane_3d, 0, 0)  # 3D top-left
        main_layout.addWidget(self.hkl_controls, 1, 0)  # Controls bottom-left
        main_layout.addWidget(self.hkl_plane_2d, 0, 1, 2, 1)  # 2D right side spanning both rows

        # Set layout proportions
        main_layout.setColumnStretch(0, 1)  # Left column
        main_layout.setColumnStretch(1, 1)  # Right column
        main_layout.setRowStretch(0, 3)     # More space for visualizers
        main_layout.setRowStretch(1, 1)     # Less space for controls

        # Connect signals
        self._connect_hkl_signals()

        # Add to tab widget
        self.tab_widget.addTab(hkl_tab, "HKL plane")

    def _connect_hkl_signals(self):
        """Connect signals for HKL plane tab."""
        # Initialize button
        self.hkl_controls.initializeClicked.connect(self.initialize_calculator_hkl)
        
        # Plane change
        self.hkl_controls.planeChanged.connect(self._on_plane_changed)
        
        # Connect 2D plane updates to calculator
        self.hkl_plane_2d.connect_value_changed_signals(
            lambda: self.hkl_plane_2d.update_hk_plane(self.calculator),
            lambda: self.hkl_plane_2d.update_hl_plane(self.calculator),
            lambda: self.hkl_plane_2d.update_kl_plane(self.calculator)
        )
        
        # Connect 2D controls to 3D plane updates
        self.hkl_plane_2d.connect_3d_plane_signals(self.hkl_plane_3d)

    def _create_customized_tab(self):
        """Create the customized plane subtab using components."""
        # Create the complete customized widget
        self.customized_plane_widget = CustomizedPlaneWidget()
        self.customized_plane_widget.set_calculator(self.calculator)
        
        # Connect initialize signal
        controls = self.customized_plane_widget.get_controls()
        controls.initializeClicked.connect(self.initialize_calculator_customized)

        # Connect check accessibility signal
        accessible_controls = self.customized_plane_widget.accessible_controls
        accessible_controls.checkAccessibilityClicked.connect(self._check_accessibility)

        # Add to tab widget
        self.tab_widget.addTab(self.customized_plane_widget, "Customized plane")

    @pyqtSlot()
    def initialize_calculator_hkl(self):
        """Initialize the structure factor calculator for HKL plane tab."""
        try:
            params = self.controller.app_controller.get_parameters() if self.controller else None
            cif_path = params.get("cif_file") if params else None
            if not cif_path:
                QMessageBox.warning(
                    self,
                    "Missing CIF",
                    "Please load a valid CIF file in the initialization window first.",
                )
                return

            energy_ev = self.hkl_controls.get_energy_ev()
            self.calculator.initialize(cif_path, energy_ev)

            self.hkl_controls.set_status("Calculator initialized successfully", "green")

            # Populate 3D using full HKL cube ranging 0..5
            hkl_list = self._generate_hkl_cube(5)
            results = self.calculator.calculate_structure_factors(hkl_list)
            self.hkl_plane_3d.visualize_structure_factors(hkl_list, results)

            # Initialize 2D slices
            self.hkl_plane_2d.update_hk_plane(self.calculator)
            self.hkl_plane_2d.update_hl_plane(self.calculator)
            self.hkl_plane_2d.update_kl_plane(self.calculator)

            # Initialize 3D planes based on current control values
            plane_values = self.hkl_plane_2d.get_plane_values()
            self.hkl_plane_3d.set_plane_values(**plane_values)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to initialize calculator: {str(e)}"
            )
            self.hkl_controls.set_status(f"Initialization failed - {str(e)}", "red")

    @pyqtSlot()
    def initialize_calculator_customized(self):
        """Initialize the structure factor calculator for customized plane tab."""
        try:
            params = self.controller.app_controller.get_parameters() if self.controller else None
            cif_path = params.get("cif_file") if params else None
            if not cif_path:
                QMessageBox.warning(
                    self,
                    "Missing CIF",
                    "Please load a valid CIF file in the initialization window first.",
                )
                return

            controls = self.customized_plane_widget.get_controls()
            energy_ev = controls.get_energy_ev()
            self.calculator.initialize(cif_path, energy_ev)

            controls.set_status("Calculator initialized successfully", "green")
            
            # Update plots
            self.customized_plane_widget.update_plots()

            # Auto-trigger accessibility check
            self._check_accessibility()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to initialize calculator: {str(e)}"
            )
            controls = self.customized_plane_widget.get_controls()
            controls.set_status(f"Initialization failed - {str(e)}", "red")

    @pyqtSlot()
    def _check_accessibility(self):
        """Gather UI parameters, delegate to controller, and display results."""
        try:
            # Gather plane parameters from configuration controls
            controls = self.customized_plane_widget.get_controls()
            U, V, C = controls.get_custom_vectors()
            u_range, v_range = controls.get_ranges()
            energy_ev = controls.get_energy_ev()

            plane_params = {
                "U": U, "V": V, "C": C,
                "u_range": u_range, "v_range": v_range,
            }

            # Gather accessibility constraints
            constraints = self.customized_plane_widget.accessible_controls.get_parameters()

            # Delegate to controller (which calls domain logic)
            result = self.controller.run_check_accessibility(
                plane_params, constraints, energy_ev
            )

            if not result["success"]:
                QMessageBox.warning(
                    self, "Not Initialized", result.get("error", "Unknown error")
                )
                return

            # Refresh the base 2D plot so previous overlay is cleared
            self.customized_plane_widget.update_plots()

            # Overlay inaccessible points on the 2D visualizer
            visualizer_2d = self.customized_plane_widget.plane_2d.visualizer2d
            inaccessible = result["inaccessible"]
            visualizer_2d.overlay_inaccessible_points(inaccessible)

            # Ensure the 2D axes range is correct even if SF calculator
            # is not yet initialised (update_plots would have skipped the
            # 2D draw in that case).
            uv_points = result["uv_points"]
            if uv_points:
                u_vals = np.array([p['u'] for p in uv_points])
                v_vals = np.array([p['v'] for p in uv_points])
                visualizer_2d.axes.set_xlim(u_vals.min() - 0.5, u_vals.max() + 0.5)
                visualizer_2d.axes.set_ylim(v_vals.min() - 0.5, v_vals.max() + 0.5)
                visualizer_2d.draw()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to check accessibility:\n{str(e)}",
            )

    @pyqtSlot(str)
    def _on_plane_changed(self, plane: str):
        """Handle plane change from controls."""
        # Update 2D widget to show the selected plane
        self.hkl_plane_2d.set_active_plane(plane)
        
        # Update 3D plane highlighting
        if plane == "HK":
            self.hkl_plane_3d.set_active_plane("L")  # HK plane means L constant
        elif plane == "HL":
            self.hkl_plane_3d.set_active_plane("K")
        elif plane == "KL":
            self.hkl_plane_3d.set_active_plane("H")
            
        # Update corresponding plot if initialized
        if self.calculator.is_initialized:
            if plane == "HK":
                self.hkl_plane_2d.update_hk_plane(self.calculator)
            elif plane == "HL":
                self.hkl_plane_2d.update_hl_plane(self.calculator)
            elif plane == "KL":
                self.hkl_plane_2d.update_kl_plane(self.calculator)

    def _generate_hkl_cube(self, max_index: int = 5):
        """Generate a full integer HKL grid from 0..max_index for 3D visualization."""
        cube = []
        for h in range(0, max_index + 1):
            for k in range(0, max_index + 1):
                for l in range(0, max_index + 1):
                    cube.append([h, k, l])
        return cube

    def get_module_instance(self):
        """Get the backend module instance."""
        return self.calculator

    def clear(self):
        """Clear all inputs and results."""
        # Clear visualizations
        if hasattr(self, 'hkl_plane_2d'):
            self.hkl_plane_2d.clear_plots()
        if hasattr(self, 'customized_plane_widget'):
            self.customized_plane_widget.clear_plots()

    def get_state(self):
        """Get the current state for session saving."""
        state = {}
        if hasattr(self, 'hkl_controls'):
            state["hkl_energy"] = self.hkl_controls.get_energy_ev()
        if hasattr(self, 'customized_plane_widget'):
            controls = self.customized_plane_widget.get_controls()
            state["custom_energy"] = controls.get_energy_ev()
        return state

    def set_state(self, state):
        """Restore tab state from saved session."""
        try:
            if "hkl_energy" in state and hasattr(self, 'hkl_controls'):
                self.hkl_controls.energy_input.energy_ev = state["hkl_energy"]
                
            if "custom_energy" in state and hasattr(self, 'customized_plane_widget'):
                controls = self.customized_plane_widget.get_controls()
                controls.energy_input.energy_ev = state["custom_energy"]

            # Try to reinitialize if we have the required data globally
            params = self.controller.app_controller.get_parameters() if self.controller else None
            if (
                params
                and params.get("cif_file")
                and os.path.exists(params.get("cif_file"))
            ):
                if hasattr(self, 'hkl_controls'):
                    self.initialize_calculator_hkl()
                if hasattr(self, 'customized_plane_widget'):
                    self.initialize_calculator_customized()

            return True
        except Exception:
            return False
