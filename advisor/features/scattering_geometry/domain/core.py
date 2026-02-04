#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core calculation functions for Brillouin calculator.

This module contains the pure computational functions for Brillouin zone calculations
that don't depend on the BrillouinCalculator class.
"""

import numpy as np
from scipy.optimize import fsolve

from advisor.domain import angle_to_matrix
from advisor.domain.core import Lab


def _get_real_space_vectors(a, b, c, alpha, beta, gamma):
    """Get the real space vectors a_vec, b_vec, c_vec from the lattice parameters.
    - a_vec is by-default along x-axis (a, 0, 0)
    - b_vec is by-default (b cos gamma, b sin gamma, 0) on the x-y plane,
    - c_vec is then calculated
    The above convention defines the crystal coordinate system.

    Args:
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): Lattice angles in degrees

    Returns:
        a_vec, b_vec, c_vec (np.ndarray): Real space vectors
    """
    alpha_rad, beta_rad, gamma_rad = (
        np.radians(alpha),
        np.radians(beta),
        np.radians(gamma),
    )
    a_vec = np.array([a, 0, 0])
    b_vec = np.array([b * np.cos(gamma_rad), b * np.sin(gamma_rad), 0])
    c_vec_x = c * np.cos(beta_rad)
    c_vec_y = (
        c
        * (np.cos(alpha_rad) - np.cos(beta_rad) * np.cos(gamma_rad))
        / np.sin(gamma_rad)
    )
    c_vec_z = np.sqrt(c**2 - c_vec_x**2 - c_vec_y**2)
    c_vec = np.array([c_vec_x, c_vec_y, c_vec_z])
    return a_vec, b_vec, c_vec


def _get_reciprocal_space_vectors(a, b, c, alpha, beta, gamma):
    """Get the reciprocal space vectors a_star_vec, b_star_vec, c_star_vec from the lattice
    parameters, angles in degrees. These vectors are in the crystal coordinate system.
    """
    a_vec, b_vec, c_vec = _get_real_space_vectors(a, b, c, alpha, beta, gamma)
    volumn = abs(np.dot(a_vec, np.cross(b_vec, c_vec)))
    a_star_vec = 2 * np.pi * np.cross(b_vec, c_vec) / volumn
    b_star_vec = 2 * np.pi * np.cross(c_vec, a_vec) / volumn
    c_star_vec = 2 * np.pi * np.cross(a_vec, b_vec) / volumn
    return a_star_vec, b_star_vec, c_star_vec


def _get_norm_vector(h, k, l, a, b, c, alpha, beta, gamma):
    """Get the norm vector of the plane defined by the Miller indices (h, k, l)."""
    a_star_vec, b_star_vec, c_star_vec = _get_reciprocal_space_vectors(
        a, b, c, alpha, beta, gamma
    )
    norm_vec = (
        h * a_star_vec / (2 * np.pi)
        + k * b_star_vec / (2 * np.pi)
        + l * c_star_vec / (2 * np.pi)
    )
    return norm_vec


def _get_d_spacing(h, k, l, a, b, c, alpha, beta, gamma):
    """Get the d-spacing of the plane defined by the Miller indices (h, k, l)."""
    norm_vec = _get_norm_vector(h, k, l, a, b, c, alpha, beta, gamma)
    d_spacing = 1 / np.linalg.norm(norm_vec)
    return d_spacing


def _get_momentum_diffraction(h, k, l, a, b, c, alpha, beta, gamma):
    """Get the momentum transfer vector of the plane defined by the Miller indices (h, k, l)."""
    norm_vec = _get_norm_vector(h, k, l, a, b, c, alpha, beta, gamma)
    return 2 * np.pi * norm_vec


def _get_HKL_from_momentum_scattering(momentum, a_vec, b_vec, c_vec):
    """Get the HKL (r.l.u.) from the momentum transfer vector."""
    H = np.dot(momentum, a_vec) / (2 * np.pi)
    K = np.dot(momentum, b_vec) / (2 * np.pi)
    L = np.dot(momentum, c_vec) / (2 * np.pi)
    return H, K, L


def calculate_k_magnitude(k_in, tth):
    """Calculate the momentum transfer magnitude from the scattering angle."""
    return 2 * k_in * np.sin(np.radians(tth / 2.0))


def calculate_tth_from_k_magnitude(k_in, k_magnitude):
    """calculate the scattering angle tth from the momentum transfer magnitude"""
    return 2 * np.degrees(np.arcsin(k_magnitude / (2 * k_in)))


def calculate_k_vector_in_lab(k_in, tth):
    """get the momentum transfer k vector in lab frame from the scattering angle tth"""
    eta = 90 - tth / 2
    eta_rad = np.radians(eta)
    k_magnitude = calculate_k_magnitude(k_in, tth)
    #k_vector = k_magnitude * np.array([-np.cos(eta_rad), 0, -np.sin(eta_rad)])
    k_vector = k_magnitude * np.array([-np.sin(eta_rad), -np.cos(eta_rad), 0])
    return k_vector


def derivative(fun, x, delta_x=1e-6):
    """calculate the derivative of the function fun at the point x"""
    return (fun(x + delta_x) - fun(x - delta_x)) / (2 * delta_x)


def process_angle(angle):
    """process the angle to be in the range of (-180, 180]"""
    angle = angle % 360
    if angle > 180:
        angle -= 360
    return angle


def _calculate_angles_factory(fixed_angle_name):
    if fixed_angle_name == "chi":
        return _calculate_angles_chi_fixed
    elif fixed_angle_name == "phi":
        return _calculate_angles_phi_fixed


def _calculate_angles_tth_fixed(
    k_in,
    tth,
    a,
    b,
    c,
    alpha,
    beta,
    gamma,
    roll,
    pitch,
    yaw,
    H=0.15,
    K=0.1,
    L=None,
    fixed_angle_name="chi",
    fixed_angle=0.0,
):
    """Calculate scattering angles from two of the three HKL indices, with tth (in degrees) fixed.

    Two steps involved:

    1. Use fsolve to find the missing momentum transfer component (H, K, or L). IT IS POSSIBLE THAT
       THERE ARE MULTIPLE SOLUTIONS, BUT HERE WE ONLY RETURN THE ONE CLOSE TO THE NEGATIVE VALUE.
    2. Use root-finding to find up to two theta and phi/chi angles that satisfy the condition
       for the given HKL indices while keeping one angle fixed.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        tth (float): Scattering angle in degrees
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): sample rotation angles in degrees
        roll, pitch, yaw (float): Lattice rotation Euler angles in degrees. We use ZYX convention.
        H (float, optional): momentum transfer in reciprocal length unit (r.l.u.). Defaults to 0.15.
        K (float, optional): momentum transfer in reciprocal length unit (r.l.u.). Defaults to 0.1.
        L (float, optional): momentum transfer in reciprocal length unit (r.l.u.). Defaults to None.
        fixed_angle_name (str, optional): Name of the angle to fix ("chi" or "phi"). Defaults to "chi".
        fixed_angle (float, optional): Value of the fixed angle in degrees. Defaults to 0.0.

    Returns:
        dict: Dictionary containing:
            - tth (list): Scattering angle values in degrees
            - theta (list): Sample theta rotation values in degrees
            - phi (list): Sample phi rotation values in degrees
            - chi (list): Sample chi rotation values in degrees
            - momentum (float): Solved momentum transfer component (H, K, or L depending on which was None)
            - number_of_solutions (int): Number of distinct solutions found
    """
    # initial k_vec_lab when sample has not rotated
    k_magnitude_target = calculate_k_magnitude(k_in, tth)
    lab = Lab()
    lab.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw, 0, 0, 0)
    a_star_vec_lab, b_star_vec_lab, c_star_vec_lab = lab.get_reciprocal_space_vectors()

    # Define which index is None and will be solved for
    index_to_solve = None
    if H is None:
        index_to_solve = "H"
    elif K is None:
        index_to_solve = "K"
    elif L is None:
        index_to_solve = "L"

    def fun_to_solve(momentum):
        h_val = momentum if index_to_solve == "H" else H
        k_val = momentum if index_to_solve == "K" else K
        l_val = momentum if index_to_solve == "L" else L
        k = h_val * a_star_vec_lab + k_val * b_star_vec_lab + l_val * c_star_vec_lab
        k_magnitude = np.linalg.norm(k)
        return k_magnitude - k_magnitude_target

    momentum = fsolve(fun_to_solve, -1.0)

    # Update the appropriate index
    if index_to_solve == "H":
        H = momentum[0]
    elif index_to_solve == "K":
        K = momentum[0]
    elif index_to_solve == "L":
        L = momentum[0]

    calculate_angles = _calculate_angles_factory(fixed_angle_name)

    result = calculate_angles(
        k_in,
        H,
        K,
        L,
        a,
        b,
        c,
        alpha,
        beta,
        gamma,
        roll,
        pitch,
        yaw,
        fixed_angle,
    )
    
    # Add momentum to the result
    result["momentum"] = momentum[0]
    
    return result


def _calculate_angles_chi_fixed(
    k_in,
    H,
    K,
    L,
    a,
    b,
    c,
    alpha,
    beta,
    gamma,
    roll,
    pitch,
    yaw,
    chi_fixed,
    target_objective=1e-10,
    max_restarts=20,
):
    """Calculate scattering angles with chi angle (in degrees) fixed.

    Uses root-finding (fsolve) to find up to two theta and phi angle solutions that satisfy
    the condition for the given HKL indices while keeping chi fixed at the specified value.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        H, K, L (float): momentum transfer in reciprocal length unit (r.l.u.),
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): sample rotation angles in degrees
        roll, pitch, yaw (float): Lattice rotation Euler angles in degrees. We use ZYX convention.
        chi_fixed (float): Fixed chi angle in degrees
        target_objective (float, optional): Convergence tolerance for fsolve. Defaults to 1e-10.
        max_restarts (int, optional): Maximum number of random restarts. Defaults to 20.

    Returns:
        dict: Dictionary containing:
            - tth (list): Scattering angle values in degrees
            - theta (list): Sample theta rotation values in degrees
            - phi (list): Sample phi rotation values in degrees
            - chi (list): Fixed chi values in degrees
            - number_of_solutions (int): Number of distinct solutions found (1 or 2)
    """
    # Initialize lab ONCE - reuse for all iterations
    lab = Lab()
    lab.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw, 0, 0, chi_fixed)

    # Compute k_target (constant throughout optimization)
    lab.rotate(45, 1, chi_fixed)
    a_star, b_star, c_star = lab.get_reciprocal_space_vectors()
    k_initial = H * a_star + K * b_star + L * c_star
    k_magnitude = np.linalg.norm(k_initial)
    tth = calculate_tth_from_k_magnitude(k_in, k_magnitude)
    k_target = calculate_k_vector_in_lab(k_in, tth)

    def equations(angles):
        """Return residuals: k_cal - k_target (2 components, 2 unknowns)."""
        theta, phi = angles
        lab.rotate(theta, phi, chi_fixed)
        a_star_vec, b_star_vec, c_star_vec = lab.get_reciprocal_space_vectors()
        k_cal = H * a_star_vec + K * b_star_vec + L * c_star_vec
        # 2 equations for 2 unknowns (3rd is redundant due to |k_cal|=|k_target|)
        return [k_cal[0] - k_target[0], k_cal[1] - k_target[1]]

    def is_valid_solution(phi):
        if phi is None:
            return False
        return -90 <= phi <= 90

    def is_distinct_solution(theta_new, phi_new, existing_solutions, tolerance=1.0):
        """Check if a solution is distinct from existing ones (differs by more than tolerance degrees)."""
        for theta_exist, phi_exist in existing_solutions:
            if abs(theta_new - theta_exist) < tolerance and abs(phi_new - phi_exist) < tolerance:
                return False
        return True

    solutions = []  # List of (theta, phi) tuples

    # Try different starting points to find up to 2 distinct solutions
    for _ in range(max_restarts):
        theta0 = np.random.uniform(0, 180)
        phi0 = np.random.uniform(-90, 90)

        solution, info, ier, msg = fsolve(
            equations,
            x0=[theta0, phi0],
            full_output=True,
            xtol=target_objective,
        )

        theta, phi = solution
        theta = process_angle(theta)
        phi = process_angle(phi)

        # Check if fsolve converged (ier=1) and solution is valid
        if ier == 1 and is_valid_solution(phi):
            # Verify solution quality
            residual = np.linalg.norm(equations([theta, phi]))
            if residual < 1e-6:
                # Check if this is a distinct solution
                if is_distinct_solution(theta, phi, solutions):
                    solutions.append((theta, phi))
                    # Stop if we found 2 solutions
                    if len(solutions) >= 2:
                        break

    # Build result lists
    tth_result = process_angle(tth)
    
    if len(solutions) == 0:
        # No valid solution found - return last attempted values
        return {
            "tth": [tth_result],
            "theta": [theta],
            "phi": [phi],
            "chi": [chi_fixed],
            "number_of_solutions": 0,
        }
    
    theta_list = [sol[0] for sol in solutions]
    phi_list = [sol[1] for sol in solutions]
    tth_list = [tth_result] * len(solutions)
    chi_list = [chi_fixed] * len(solutions)

    return {
        "tth": tth_list,
        "theta": theta_list,
        "phi": phi_list,
        "chi": chi_list,
        "number_of_solutions": len(solutions),
    }


def _calculate_angles_phi_fixed(
    k_in,
    H,
    K,
    L,
    a,
    b,
    c,
    alpha,
    beta,
    gamma,
    roll,
    pitch,
    yaw,
    phi_fixed,
    target_objective=1e-10,
    max_restarts=20,
):
    """Calculate scattering angles with phi angle fixed.

    Uses root-finding (fsolve) to find up to two theta and chi angle solutions that satisfy
    the condition for the given HKL indices while keeping phi fixed at the specified value.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        H, K, L (float): momentum transfer in reciprocal length unit (r.l.u.),
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): sample rotation angles in degrees
        roll, pitch, yaw (float): Lattice rotation Euler angles in degrees. We use ZYX convention.
        phi_fixed (float): Fixed phi angle in degrees
        target_objective (float, optional): Convergence tolerance for fsolve. Defaults to 1e-10.
        max_restarts (int, optional): Maximum number of random restarts. Defaults to 20.

    Returns:
        dict: Dictionary containing:
            - tth (list): Scattering angle values in degrees
            - theta (list): Sample theta rotation values in degrees
            - phi (list): Fixed phi values in degrees
            - chi (list): Sample chi rotation values in degrees
            - number_of_solutions (int): Number of distinct solutions found (1 or 2)
    """
    # Initialize lab ONCE - reuse for all iterations
    lab = Lab()
    lab.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw, 0, phi_fixed, 0)

    # Compute k_target (constant throughout optimization)
    lab.rotate(45, phi_fixed, 1)
    a_star, b_star, c_star = lab.get_reciprocal_space_vectors()
    k_initial = H * a_star + K * b_star + L * c_star
    k_magnitude = np.linalg.norm(k_initial)
    tth = calculate_tth_from_k_magnitude(k_in, k_magnitude)
    k_target = calculate_k_vector_in_lab(k_in, tth)

    def equations(angles):
        """Return residuals: k_cal - k_target (2 components, 2 unknowns)."""
        theta, chi = angles
        lab.rotate(theta, phi_fixed, chi)
        a_star_vec, b_star_vec, c_star_vec = lab.get_reciprocal_space_vectors()
        k_cal = H * a_star_vec + K * b_star_vec + L * c_star_vec
        # 2 equations for 2 unknowns (3rd is redundant due to |k_cal|=|k_target|)
        return [k_cal[0] - k_target[0], k_cal[1] - k_target[1]]

    def is_valid_solution(chi):
        if chi is None:
            return False
        return -90 <= chi <= 90

    def is_distinct_solution(theta_new, chi_new, existing_solutions, tolerance=1.0):
        """Check if a solution is distinct from existing ones (differs by more than tolerance degrees)."""
        for theta_exist, chi_exist in existing_solutions:
            if abs(theta_new - theta_exist) < tolerance and abs(chi_new - chi_exist) < tolerance:
                return False
        return True

    solutions = []  # List of (theta, chi) tuples

    # Try different starting points to find up to 2 distinct solutions
    for _ in range(max_restarts):
        theta0 = np.random.uniform(0, 180)
        chi0 = np.random.uniform(-90, 90)

        solution, info, ier, msg = fsolve(
            equations,
            x0=[theta0, chi0],
            full_output=True,
            xtol=target_objective,
        )

        theta, chi = solution
        theta = process_angle(theta)
        chi = process_angle(chi)

        # Check if fsolve converged (ier=1) and solution is valid
        if ier == 1 and is_valid_solution(chi):
            # Verify solution quality
            residual = np.linalg.norm(equations([theta, chi]))
            if residual < 1e-6:
                # Check if this is a distinct solution
                if is_distinct_solution(theta, chi, solutions):
                    solutions.append((theta, chi))
                    # Stop if we found 2 solutions
                    if len(solutions) >= 2:
                        break

    # Build result lists
    tth_result = process_angle(tth)
    
    if len(solutions) == 0:
        # No valid solution found - return last attempted values
        return {
            "tth": [tth_result],
            "theta": [theta],
            "phi": [phi_fixed],
            "chi": [chi],
            "number_of_solutions": 0,
        }
    
    theta_list = [sol[0] for sol in solutions]
    chi_list = [sol[1] for sol in solutions]
    tth_list = [tth_result] * len(solutions)
    phi_list = [phi_fixed] * len(solutions)

    return {
        "tth": tth_list,
        "theta": theta_list,
        "phi": phi_list,
        "chi": chi_list,
        "number_of_solutions": len(solutions),
    }


def _calculate_hkl(k_in, tth, theta, phi, chi, a_vec_lab, b_vec_lab, c_vec_lab):
    """Calculate HKL values from scattering angles.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        tth (float): Scattering angle in degrees
        theta (float): Sample theta rotation in degrees
        phi (float): Sample phi rotation in degrees
        chi (float): Sample chi rotation in degrees
        a_vec_lab (np.ndarray): Real space a vector in lab frame
        b_vec_lab (np.ndarray): Real space b vector in lab frame
        c_vec_lab (np.ndarray): Real space c vector in lab frame

    Returns:
        dict: Dictionary containing calculated values:
            - H, K, L (float): momentum transfer in reciprocal length unit (r.l.u.)
            - tth, theta, phi, chi (float): Input angles in degrees
            - success (bool): Whether calculation was successful
            - error (str or None): Error message if any
    """
    try:
        # Calculate momentum transfer magnitude
        k_magnitude = 2.0 * k_in * np.sin(np.radians(tth / 2.0))

        # Calculate delta = theta + 90 - (tth/2)
        delta = 90 -(tth / 2.0)
        sin_delta = np.sin(np.radians(delta))
        cos_delta = np.cos(np.radians(delta))

        # momentum transfer at theta, phi, chi = 0
        k_vec_initial = np.array(
            [-k_magnitude * sin_delta, -k_magnitude * cos_delta, 0.0]
        )

        # rotation of the beam is the reverse rotation of the sample, thus the transpose
        rotation_matrix = angle_to_matrix(theta, phi, chi).T

        # momentum transfer at non-zero theta, phi, chi
        k_vec_lab = rotation_matrix @ k_vec_initial

        # calculate HKL
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
            "H": None,
            "K": None,
            "L": None,
            "tth": tth,
            "theta": theta,
            "phi": phi,
            "chi": chi,
            "success": False,
            "error": str(e),
        }
