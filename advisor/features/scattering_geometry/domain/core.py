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
    2. Use optimization algorithm to find the theta and phi/chi angles that satisfy the condition
       for the given HKL indices while keeping one angle fixed.

    There could be more than one solution, so the function returns a list of solutions.

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
        tuple: Five values containing the calculated results:
            - tth_result (float/list): Scattering angle value(s) in degrees
            - theta_result (float/list): Sample theta rotation value(s) in degrees
            - phi_result (float/list): Sample phi rotation value(s) in degrees
            - chi_result (float/list): Sample chi rotation value(s) in degrees
            - momentum (float): Solved momentum transfer component (H, K, or L depending on which was None)
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

    tth_result, theta_result, phi_result, chi_result = calculate_angles(
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
    return tth_result, theta_result, phi_result, chi_result, momentum[0]


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
    target_objective=1e-7,
    num_steps=3000,
    learning_rate=100,
):
    """Calculate scattering angles with chi angle (in degrees) fixed.

    Uses optimization algorithm to find the theta and phi angles that satisfy the condition
    for the given HKL indices while keeping chi fixed at the specified value. There could be more
    than one solution, so the function returns a list of solutions.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        H, K, L (float): momentum transfer in reciprocal length unit (r.l.u.),
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): sample rotation angles in degrees
        roll, pitch, yaw (float): Lattice rotation Euler angles in degrees. We use ZYX convention.
        chi_fixed (float): Fixed chi angle in degrees
        target_objective (float, optional): Convergence criterion for optimization. Defaults to 1e-5.
        num_steps (int, optional): Maximum number of optimization steps. Defaults to 1000.
        learning_rate (float, optional): Learning rate for the gradient descent. Defaults to 100.

    Returns:
        tuple: Four lists containing the calculated values:
            - tth_result (list): Scattering angle values in degrees
            - theta_result (list): Sample theta rotation values in degrees
            - phi_result (list): Sample phi rotation values in degrees
            - chi_result (list): Fixed chi values in degrees (all equal to chi_fixed)
    """

    def objective_function(k_cal, k_target):
        """objective function for gradient decent"""
        return np.linalg.norm(k_cal - k_target)/np.linalg.norm(k_target)

    def get_k_cal(lab, theta_, phi_, chi_):
        lab.rotate(theta_, phi_, chi_)
        a_star_vec, b_star_vec, c_star_vec = lab.get_reciprocal_space_vectors()
        k_cal = H * a_star_vec + K * b_star_vec + L * c_star_vec
        return k_cal

    def is_valid_solution(phi):
        if phi is None:
            return False
        if (phi > 90) or (phi < -90):
            return False
        return True

    theta_best = None
    phi_best = None
    _is_valid_solution = False

    while not _is_valid_solution:
        lab = Lab()
        theta = np.random.uniform(0, 180)
        phi = np.random.uniform(-90, 90)

        lab.initialize(
            a, b, c, alpha, beta, gamma, roll, pitch, yaw, theta, phi, chi_fixed
        )

        k_cal = get_k_cal(lab, theta, phi, chi_fixed)
        k_magnitude = np.linalg.norm(k_cal)
        tth = calculate_tth_from_k_magnitude(k_in, k_magnitude)
        k_target = calculate_k_vector_in_lab(k_in, tth)
        objective = objective_function(k_cal, k_target)
        for i in range(num_steps):
            step_size = objective * learning_rate
            theta_new = theta + np.random.uniform(-step_size, step_size)
            phi_new = phi + np.random.uniform(-step_size, step_size)
            k_cal = get_k_cal(lab, theta_new, phi_new, chi_fixed)
            objective_new = objective_function(k_cal, k_target)
            if objective_new < objective:
                theta = theta_new
                phi = phi_new
                objective = objective_new
            if objective < target_objective:
                break
        # Normalize angles to (-180, 180] range
        theta = process_angle(theta)
        phi = process_angle(phi)

        theta_best = theta
        phi_best = phi
        _is_valid_solution = is_valid_solution(phi_best)

    theta_result = np.round(theta_best, 1)
    phi_result = np.round(phi_best, 1)
    tth_result = np.round(process_angle(tth), 1)
    chi_result = np.round(chi_fixed, 1)

    return tth_result, theta_result, phi_result, chi_result


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
    target_objective=1e-7,
    num_steps=3000,
    learning_rate=100,
):
    """Calculate scattering angles with phi angle fixed.

    Uses optimization algorithm to find the theta and chi angles that satisfy the condition
    for the given HKL indices while keeping phi fixed at the specified value. There could be more
    than one solution, so the function returns a list of solutions.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        H, K, L (float): momentum transfer in reciprocal length unit (r.l.u.),
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): sample rotation angles in degrees
        roll, pitch, yaw (float): Lattice rotation Euler angles in degrees. We use ZYX convention.
        phi_fixed (float): Fixed phi angle in degrees
        target_objective (float, optional): Convergence criterion for optimization. Defaults to 1e-5.
        num_steps (int, optional): Maximum number of optimization steps. Defaults to 1000.
        learning_rate (float, optional): Learning rate for the gradient descent. Defaults to 100.

    Returns:
        tuple: Four lists containing the calculated values:
            - tth_result (list): Scattering angle values in degrees
            - theta_result (list): Sample theta rotation values in degrees
            - phi_result (list): Fixed phi values in degrees (all equal to phi_fixed)
            - chi_result (list): Sample chi rotation values in degrees
    """

    def objective_function(k_cal, k_target):
        """objective function for gradient decent"""
        return np.linalg.norm(k_cal - k_target)

    def get_k_cal(lab, theta_, phi_, chi_):
        lab.rotate(theta_, phi_, chi_)
        a_star_vec, b_star_vec, c_star_vec = lab.get_reciprocal_space_vectors()
        k_cal = H * a_star_vec + K * b_star_vec + L * c_star_vec
        return k_cal
    
    def is_valid_solution(chi):
        if chi is None:
            return False
        if (chi > 90) or (chi < -90):
            return False
        return True
    
    theta_best = None
    chi_best = None
    _is_valid_solution = False
    while not _is_valid_solution:
        lab = Lab()
        theta = np.random.uniform(0, 180)
        chi = np.random.uniform(-90, 90)

        lab.initialize(
            a, b, c, alpha, beta, gamma, roll, pitch, yaw, theta, phi_fixed, chi
        )

        k_cal = get_k_cal(lab, theta, phi_fixed, chi)
        k_magnitude = np.linalg.norm(k_cal)
        tth = calculate_tth_from_k_magnitude(k_in, k_magnitude)
        k_target = calculate_k_vector_in_lab(k_in, tth)
        objective = objective_function(k_cal, k_target)
        for i in range(num_steps):
            step_size = objective * learning_rate
            theta_new = theta + np.random.uniform(-step_size, step_size)
            chi_new = chi + np.random.uniform(-step_size, step_size)
            k_cal = get_k_cal(lab, theta_new, phi_fixed, chi_new)
            objective_new = objective_function(k_cal, k_target)
            if objective_new < objective:
                theta = theta_new
                chi = chi_new
                objective = objective_new
            if objective < target_objective:
                break
        # Normalize angles to (0, 360) range
        theta = process_angle(theta)
        chi = process_angle(chi)
        theta_best = theta
        chi_best = chi
        _is_valid_solution = is_valid_solution(chi_best)

    # round up to 0.1, discard duplicates, theta and chi should match the order of the list
    theta_result = np.round(theta_best, 1)
    chi_result = np.round(chi_best, 1)
    tth_result = np.round(process_angle(tth), 1)
    phi_result = np.round(phi_fixed, 1)
    return tth_result, theta_result, phi_result, chi_result


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
