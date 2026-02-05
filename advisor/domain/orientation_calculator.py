#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight calculator for orientation fitting.

This module provides a minimal calculator class that can compute HKL values
from scattering angles, used specifically for orientation fitting.
It avoids importing from feature modules to prevent circular dependencies.
"""

import numpy as np

from advisor.domain import angle_to_matrix
from advisor.domain.core import Lab


class OrientationCalculator:
    """Lightweight calculator for orientation fitting.

    This class provides only the methods needed for fitting crystal orientation
    from diffraction test data. It uses the Lab class directly and avoids
    dependencies on feature-specific modules.
    """

    # Physical constants
    EV_TO_LAMBDA = 12398.42  # eV to Angstrom conversion

    def __init__(self):
        """Initialize the calculator."""
        self._initialized = False
        self.lab = Lab()
        self.energy = None
        self.lambda_A = None
        self.k_in = None

    def initialize(self, params: dict) -> bool:
        """Initialize with lattice parameters.

        Args:
            params: Dictionary containing:
                - a, b, c (float): Lattice constants in Angstroms
                - alpha, beta, gamma (float): Lattice angles in degrees
                - energy (float): X-ray energy in eV
                - roll, pitch, yaw (float, optional): Euler angles in degrees

        Returns:
            bool: True if initialization was successful
        """
        try:
            a = params.get("a", 4.0)
            b = params.get("b", 4.0)
            c = params.get("c", 12.0)
            alpha = params.get("alpha", 90.0)
            beta = params.get("beta", 90.0)
            gamma = params.get("gamma", 90.0)
            roll = params.get("roll", 0.0)
            pitch = params.get("pitch", 0.0)
            yaw = params.get("yaw", 0.0)
            self.energy = params["energy"]

            # Initialize lab with default sample rotation (0, 0, 0)
            self.lab.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw, 0, 0, 0)

            # Calculate wavelength and wavevector
            self.lambda_A = self.EV_TO_LAMBDA / self.energy
            self.k_in = 2 * np.pi / self.lambda_A

            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing OrientationCalculator: {e}")
            return False

    def change_energy(self, energy: float) -> bool:
        """Change the X-ray energy.

        Args:
            energy: X-ray energy in eV

        Returns:
            bool: True if successful
        """
        self.energy = energy
        self.lambda_A = self.EV_TO_LAMBDA / self.energy
        self.k_in = 2 * np.pi / self.lambda_A
        return True

    def reorient_sample(self, roll: float, pitch: float, yaw: float) -> bool:
        """Reorient the sample (change Euler angles).

        Args:
            roll, pitch, yaw: Euler angles in degrees

        Returns:
            bool: True if successful
        """
        self.lab.reorient(roll, pitch, yaw)
        return True

    def calculate_hkl(
        self, tth: float, theta: float, phi: float, chi: float
    ) -> dict:
        """Calculate HKL from scattering angles.

        Args:
            tth: Scattering angle 2θ in degrees
            theta: Sample theta rotation in degrees
            phi: Sample phi rotation in degrees
            chi: Sample chi rotation in degrees

        Returns:
            dict: Dictionary containing:
                - H, K, L (float): Miller indices
                - tth, theta, phi, chi (float): Input angles
                - success (bool): Whether calculation succeeded
                - error (str or None): Error message if any
        """
        if not self._initialized:
            return {
                "H": None, "K": None, "L": None,
                "tth": tth, "theta": theta, "phi": phi, "chi": chi,
                "success": False,
                "error": "Calculator not initialized",
            }

        try:
            # Get real space vectors in lab frame
            a_vec_lab, b_vec_lab, c_vec_lab = self.lab.get_real_space_vectors()

            # Calculate momentum transfer magnitude
            k_magnitude = 2.0 * self.k_in * np.sin(np.radians(tth / 2.0))

            # Calculate delta angle
            delta = 90 - (tth / 2.0)
            sin_delta = np.sin(np.radians(delta))
            cos_delta = np.cos(np.radians(delta))

            # Momentum transfer at theta, phi, chi = 0
            k_vec_initial = np.array(
                [-k_magnitude * sin_delta, -k_magnitude * cos_delta, 0.0]
            )

            # Rotation of the beam is the reverse rotation of the sample
            rotation_matrix = angle_to_matrix(theta, phi, chi).T

            # Momentum transfer at the given angles
            k_vec_lab = rotation_matrix @ k_vec_initial

            # Calculate HKL by projecting onto real space vectors
            H = np.dot(k_vec_lab, a_vec_lab) / (2 * np.pi)
            K = np.dot(k_vec_lab, b_vec_lab) / (2 * np.pi)
            L = np.dot(k_vec_lab, c_vec_lab) / (2 * np.pi)

            return {
                "H": H,
                "K": K,
                "L": L,
                "tth": tth,
                "theta": theta,
                "phi": phi,
                "chi": chi,
                "success": True,
                "error": None,
            }
        except Exception as e:
            return {
                "H": None, "K": None, "L": None,
                "tth": tth, "theta": theta, "phi": phi, "chi": chi,
                "success": False,
                "error": str(e),
            }

    def is_initialized(self) -> bool:
        """Check if the calculator is initialized."""
        return self._initialized
