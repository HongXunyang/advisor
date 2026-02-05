#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orientation fitting from diffraction tests.

This module provides functions to determine the optimal Euler angles (roll, pitch, yaw)
that align a crystal lattice orientation with observed diffraction data.
"""

import numpy as np
from scipy.optimize import minimize

from .orientation_calculator import OrientationCalculator

# Default number of random restarts for optimization
DEFAULT_N_RESTARTS = 20
# Target residual error - stop early if achieved
TARGET_RESIDUAL = 1e-10


def fit_orientation_from_diffraction_tests(
    lattice_params: dict,
    diffraction_tests: list,
    initial_guess: tuple = (0.0, 0.0, 0.0),
    n_restarts: int = DEFAULT_N_RESTARTS,
) -> dict:
    """Fit crystal orientation from diffraction test data.

    Given lattice parameters and a list of diffraction tests (each containing
    known HKL values and measured angles), find the Euler angles (roll, pitch, yaw)
    that best explain the observations.

    Uses multiple random restarts to avoid local minima.

    Args:
        lattice_params: Dictionary containing lattice parameters:
            - a, b, c (float): Lattice constants in Angstroms
            - alpha, beta, gamma (float): Lattice angles in degrees
        diffraction_tests: List of dictionaries, each containing:
            - H, K, L (float): Expected Miller indices
            - energy (float): X-ray energy in eV
            - tth (float): Scattering angle 2θ in degrees
            - theta (float): Sample theta rotation in degrees
            - phi (float): Sample phi rotation in degrees
            - chi (float): Sample chi rotation in degrees
        initial_guess: Initial guess for (roll, pitch, yaw) in degrees
        n_restarts: Number of random restarts to try (default: 20)

    Returns:
        dict: Dictionary containing:
            - roll, pitch, yaw (float): Optimized Euler angles in degrees
            - residual_error (float): Final residual error (sum of squared HKL differences)
            - individual_errors (list): Per-test HKL errors
            - success (bool): Whether optimization converged
            - message (str): Status message
    """

    if not diffraction_tests:
        return {
            "success": False,
            "message": "No diffraction tests provided",
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
        }

    # Validate diffraction tests
    required_keys = ["H", "K", "L", "energy", "tth", "theta", "phi", "chi"]
    for i, test in enumerate(diffraction_tests):
        missing = [k for k in required_keys if k not in test]
        if missing:
            return {
                "success": False,
                "message": f"Test {i+1} is missing required keys: {missing}",
                "roll": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
            }

    # Initialize calculator with lattice parameters (using initial roll, pitch, yaw = 0)
    calculator = OrientationCalculator()
    init_params = {
        "a": lattice_params["a"],
        "b": lattice_params["b"],
        "c": lattice_params["c"],
        "alpha": lattice_params["alpha"],
        "beta": lattice_params["beta"],
        "gamma": lattice_params["gamma"],
        "energy": diffraction_tests[0]["energy"],  # Will be updated per test
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": 0.0,
    }

    if not calculator.initialize(init_params):
        return {
            "success": False,
            "message": "Failed to initialize calculator with given lattice parameters",
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
        }

    def objective(params):
        """Objective function: sum of squared HKL errors."""
        roll, pitch, yaw = params
        calculator.reorient_sample(roll, pitch, yaw)

        total_error = 0.0
        for test in diffraction_tests:
            # Update energy for this test
            calculator.change_energy(test["energy"])

            # Calculate HKL from angles
            result = calculator.calculate_hkl(
                test["tth"], test["theta"], test["phi"], test["chi"]
            )

            # Compute squared error
            dH = result["H"] - test["H"]
            dK = result["K"] - test["K"]
            dL = result["L"] - test["L"]
            total_error += dH**2 + dK**2 + dL**2

        return total_error

    def run_optimization(start_point):
        """Run a single optimization from a starting point."""
        return minimize(
            objective,
            start_point,
            method="L-BFGS-B",
            bounds=[(-180, 180), (-180, 180), (-180, 180)],
            options={"ftol": 1e-12, "gtol": 1e-10, "maxiter": 1000},
        )

    # Multiple random restarts to find global minimum
    best_result = None
    best_error = float("inf")

    # First try the user-provided initial guess
    initial_points = [initial_guess]

    # Add random starting points
    rng = np.random.default_rng(seed=42)  # Reproducible results
    for _ in range(n_restarts - 1):
        # Random angles in [-180, 180]
        random_point = tuple(rng.uniform(-180, 180, 3))
        initial_points.append(random_point)

    # Also add some structured starting points
    structured_points = [
        (0, 0, 0),
        (90, 0, 0), (-90, 0, 0),
        (0, 90, 0), (0, -90, 0),
        (0, 0, 90), (0, 0, -90),
    ]
    for pt in structured_points:
        if pt not in initial_points:
            initial_points.append(pt)

    # Run optimization from each starting point
    for start_point in initial_points:
        try:
            result = run_optimization(start_point)
            if result.fun < best_error:
                best_error = result.fun
                best_result = result

            # Early stopping if we found a very good solution
            if best_error < TARGET_RESIDUAL:
                break
        except Exception:
            # Skip failed optimizations
            continue

    if best_result is None:
        return {
            "success": False,
            "message": "All optimization attempts failed",
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
        }

    # Extract optimized parameters
    roll_opt, pitch_opt, yaw_opt = best_result.x

    # Calculate individual errors at optimal orientation
    calculator.reorient_sample(roll_opt, pitch_opt, yaw_opt)
    individual_errors = []
    for test in diffraction_tests:
        calculator.change_energy(test["energy"])
        calc_result = calculator.calculate_hkl(
            test["tth"], test["theta"], test["phi"], test["chi"]
        )
        error = {
            "H_expected": test["H"],
            "K_expected": test["K"],
            "L_expected": test["L"],
            "H_calculated": calc_result["H"],
            "K_calculated": calc_result["K"],
            "L_calculated": calc_result["L"],
            "H_error": calc_result["H"] - test["H"],
            "K_error": calc_result["K"] - test["K"],
            "L_error": calc_result["L"] - test["L"],
        }
        individual_errors.append(error)

    return {
        "success": best_result.success,
        "message": best_result.message if hasattr(best_result, "message") else "Optimization completed",
        "roll": float(roll_opt),
        "pitch": float(pitch_opt),
        "yaw": float(yaw_opt),
        "residual_error": float(best_result.fun),
        "individual_errors": individual_errors,
        "n_iterations": best_result.nit if hasattr(best_result, "nit") else None,
        "n_restarts_used": len(initial_points),
    }
