#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Core calculation functions for Brillouin calculator.

This module contains the pure computational functions for Brillouin zone calculations
that don't depend on the BrillouinCalculator class.
"""

import numpy as np

from advisor.domain import angle_to_matrix, calculate_scattering_vector
from advisor.domain.core import Sample


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
    """calculate the scattering angle tth from the momentum transfer magnitude.

    Returns NaN (without raising or warning) if k_magnitude exceeds 2*k_in,
    i.e. the momentum transfer is not reachable at this energy.
    """
    ratio = k_magnitude / (2 * k_in)
    if abs(ratio) > 1.0:
        return float("nan")
    return 2 * np.degrees(np.arcsin(ratio))


def calculate_k_vector_in_lab(k_in, tth):
    """get the momentum transfer k vector in lab frame from the scattering angle tth

    Thin wrapper around the shared `advisor.domain.geometry.calculate_scattering_vector`
    primitive (kept here so existing call sites in this module don't need to change).
    """
    return calculate_scattering_vector(k_in, tth)


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


def _solve_sinusoidal_equation(A, B, D, tol=1e-9):
    """Solve A*cos(x) + B*sin(x) = D for x, in radians, over one period.

    This is the closed-form building block behind the chi/phi-fixed angle
    solvers below: matching one lab-frame component of a rotated vector to a
    fixed target always reduces to exactly this equation in the free "swept"
    angle. See paper/derivations/hkl_to_angles_analytic.tex for the derivation.

    Returns:
        None: R~=0 and D~=0 -- the equation is satisfied for every x (a
            continuum of solutions; the swept angle is physically undetermined).
        []: no real solution exists (either R~=0 and D is not ~0, or |D/R| > 1).
        [x]: exactly one root (tangent/double root).
        [x1, x2]: two distinct roots.
    """
    R = np.hypot(A, B)
    if R < tol:
        return None if abs(D) < tol else []

    m = D / R
    if abs(m) > 1.0:
        if abs(m) - 1.0 < 1e-6:
            # float overshoot right at tangency
            m = np.clip(m, -1.0, 1.0)
        else:
            return []

    phase = np.arctan2(B, A)
    delta = np.arccos(m)
    if delta < 1e-9 or (np.pi - delta) < 1e-9:
        return [phase + delta]
    return [phase + delta, phase - delta]


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
    tol=1e-9,
):
    """Calculate scattering angles from two of the three HKL indices, with tth (in degrees) fixed.

    Two steps involved, both closed-form:

    1. Solve for the missing momentum transfer component (H, K, or L) such that
       |Q| matches the target set by tth. This is quadratic in the missing
       component, giving up to 2 real roots.
    2. For each momentum root, solve for up to two (theta, phi/chi) angle
       solutions via the analytic chi/phi-fixed solver below. Up to 4 total
       solutions are possible.

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
            - momentum (list): Solved momentum transfer component (H, K, or L
              depending on which was None) for each solution
            - number_of_solutions (int): Total number of solutions found (0-4)
    """
    sample = Sample()
    sample.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw)
    a_star, b_star, c_star = sample.get_reciprocal_space_vectors()

    if H is None:
        index_to_solve = "H"
        basis = a_star
        known_vec = K * b_star + L * c_star
    elif K is None:
        index_to_solve = "K"
        basis = b_star
        known_vec = H * a_star + L * c_star
    else:
        index_to_solve = "L"
        basis = c_star
        known_vec = H * a_star + K * b_star

    k_target_mag = calculate_k_magnitude(k_in, tth)

    a_q = np.dot(basis, basis)
    b_q = 2.0 * np.dot(known_vec, basis)
    c_q = np.dot(known_vec, known_vec) - k_target_mag**2

    disc = b_q**2 - 4.0 * a_q * c_q
    disc_scale = max(abs(b_q**2), abs(4.0 * a_q * c_q), 1.0)

    if disc < -tol * disc_scale:
        momentum_roots = []
    elif disc < tol * disc_scale:
        momentum_roots = [-b_q / (2.0 * a_q)]
    else:
        sqrt_disc = np.sqrt(disc)
        momentum_roots = [
            (-b_q + sqrt_disc) / (2.0 * a_q),
            (-b_q - sqrt_disc) / (2.0 * a_q),
        ]

    calculate_angles = _calculate_angles_factory(fixed_angle_name)

    all_tth, all_theta, all_phi, all_chi, all_momentum = [], [], [], [], []

    for momentum in momentum_roots:
        H_i = momentum if index_to_solve == "H" else H
        K_i = momentum if index_to_solve == "K" else K
        L_i = momentum if index_to_solve == "L" else L

        sub_result = calculate_angles(
            k_in,
            H_i,
            K_i,
            L_i,
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

        n = sub_result["number_of_solutions"]
        all_tth.extend(sub_result["tth"])
        all_theta.extend(sub_result["theta"])
        all_phi.extend(sub_result["phi"])
        all_chi.extend(sub_result["chi"])
        all_momentum.extend([momentum] * n)

    return {
        "tth": all_tth,
        "theta": all_theta,
        "phi": all_phi,
        "chi": all_chi,
        "momentum": all_momentum,
        "number_of_solutions": len(all_tth),
    }


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
    tol=1e-9,
):
    """Calculate scattering angles with chi angle (in degrees) fixed.

    Closed-form solver: matching the lab-frame z-component of the rotated HKL
    vector to the target reduces to one sinusoidal equation in phi (see
    _solve_sinusoidal_equation and paper/derivations/hkl_to_angles_analytic.tex
    for the full derivation); theta then follows uniquely for each phi root.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        H, K, L (float): momentum transfer in reciprocal length unit (r.l.u.),
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): sample rotation angles in degrees
        roll, pitch, yaw (float): Lattice rotation Euler angles in degrees. We use ZYX convention.
        chi_fixed (float): Fixed chi angle in degrees
        tol (float, optional): Numerical tolerance for degeneracy/clipping checks.

    Returns:
        dict: Dictionary containing:
            - tth (list): Scattering angle values in degrees
            - theta (list): Sample theta rotation values in degrees
            - phi (list): Sample phi rotation values in degrees
            - chi (list): Fixed chi values in degrees
            - number_of_solutions (int): Number of distinct solutions found (0-2)
    """
    sample = Sample()
    sample.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw)
    a_star, b_star, c_star = sample.get_reciprocal_space_vectors()

    v = H * a_star + K * b_star + L * c_star
    vx, vy, vz = v

    k_magnitude = np.linalg.norm(v)
    tth = calculate_tth_from_k_magnitude(k_in, k_magnitude)

    if np.isnan(tth):
        return {"tth": [], "theta": [], "phi": [], "chi": [], "number_of_solutions": 0}

    tth_result = process_angle(tth)
    tx, ty, tz = calculate_k_vector_in_lab(k_in, tth)

    chi_rad = np.radians(chi_fixed)
    cos_chi = np.cos(chi_rad)
    sin_chi = np.sin(chi_rad)

    # w_z(phi) = -vx*sin(chi) + cos(chi)*(vy*sin(phi) + vz*cos(phi))
    #          = C0 + A*cos(phi) + B*sin(phi), solve A*cos(phi)+B*sin(phi) = tz - C0
    A = vz * cos_chi
    B = vy * cos_chi
    D = tz + vx * sin_chi

    phi_roots_rad = _solve_sinusoidal_equation(A, B, D, tol)

    if phi_roots_rad is None:
        # Degenerate: v lies along the rotation axis, phi is undetermined.
        # Any phi is physically valid; 0.0 is an arbitrary representative.
        phi_candidates_deg = [0.0]
    elif not phi_roots_rad:
        phi_candidates_deg = []
    else:
        phi_candidates_deg = [process_angle(np.degrees(r)) for r in phi_roots_rad]

    solutions = []  # list of (theta, phi) tuples
    for phi_deg in phi_candidates_deg:
        if not (-90.0 <= phi_deg <= 90.0):
            continue

        phi_rad = np.radians(phi_deg)
        uy = vy * np.cos(phi_rad) - vz * np.sin(phi_rad)
        uz = vy * np.sin(phi_rad) + vz * np.cos(phi_rad)
        wx = vx * cos_chi + sin_chi * uz
        wy = uy

        theta_deg = process_angle(
            np.degrees(np.arctan2(ty, tx) - np.arctan2(wy, wx))
        )

        if not any(
            abs(theta_deg - t) < 1e-6 and abs(phi_deg - p) < 1e-6
            for t, p in solutions
        ):
            solutions.append((theta_deg, phi_deg))

    if not solutions:
        return {"tth": [], "theta": [], "phi": [], "chi": [], "number_of_solutions": 0}

    return {
        "tth": [tth_result] * len(solutions),
        "theta": [sol[0] for sol in solutions],
        "phi": [sol[1] for sol in solutions],
        "chi": [chi_fixed] * len(solutions),
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
    tol=1e-9,
):
    """Calculate scattering angles with phi angle fixed.

    Closed-form solver, mirroring _calculate_angles_chi_fixed: the fixed phi
    rotation is applied first (fully determining an intermediate vector),
    then matching the lab-frame z-component reduces to one sinusoidal
    equation in chi; theta then follows uniquely for each chi root. See
    paper/derivations/hkl_to_angles_analytic.tex for the full derivation.

    Args:
        k_in (float): Incident wave vector magnitude, in 2π/Å
        H, K, L (float): momentum transfer in reciprocal length unit (r.l.u.),
        a, b, c (float): Lattice constants in Angstroms
        alpha, beta, gamma (float): sample rotation angles in degrees
        roll, pitch, yaw (float): Lattice rotation Euler angles in degrees. We use ZYX convention.
        phi_fixed (float): Fixed phi angle in degrees
        tol (float, optional): Numerical tolerance for degeneracy/clipping checks.

    Returns:
        dict: Dictionary containing:
            - tth (list): Scattering angle values in degrees
            - theta (list): Sample theta rotation values in degrees
            - phi (list): Fixed phi values in degrees
            - chi (list): Sample chi rotation values in degrees
            - number_of_solutions (int): Number of distinct solutions found (0-2)
    """
    sample = Sample()
    sample.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw)
    a_star, b_star, c_star = sample.get_reciprocal_space_vectors()

    v = H * a_star + K * b_star + L * c_star
    vx, vy, vz = v

    k_magnitude = np.linalg.norm(v)
    tth = calculate_tth_from_k_magnitude(k_in, k_magnitude)

    if np.isnan(tth):
        return {"tth": [], "theta": [], "phi": [], "chi": [], "number_of_solutions": 0}

    tth_result = process_angle(tth)
    tx, ty, tz = calculate_k_vector_in_lab(k_in, tth)

    phi_rad = np.radians(phi_fixed)
    cos_phi = np.cos(phi_rad)
    sin_phi = np.sin(phi_rad)

    # phi is fixed, so u = Rx(phi_fixed) @ v is a fully fixed vector.
    ux = vx
    uy = vy * cos_phi - vz * sin_phi
    uz = vy * sin_phi + vz * cos_phi

    # w_z(chi) = -ux*sin(chi) + uz*cos(chi) = A*cos(chi) + B*sin(chi), solve = tz
    A = uz
    B = -ux
    D = tz

    chi_roots_rad = _solve_sinusoidal_equation(A, B, D, tol)

    if chi_roots_rad is None:
        # Degenerate: u lies along the rotation axis, chi is undetermined.
        chi_candidates_deg = [0.0]
    elif not chi_roots_rad:
        chi_candidates_deg = []
    else:
        chi_candidates_deg = [process_angle(np.degrees(r)) for r in chi_roots_rad]

    solutions = []  # list of (theta, chi) tuples
    for chi_deg in chi_candidates_deg:
        if not (-90.0 <= chi_deg <= 90.0):
            continue

        chi_rad = np.radians(chi_deg)
        wx = ux * np.cos(chi_rad) + uz * np.sin(chi_rad)
        wy = uy  # constant, independent of chi

        theta_deg = process_angle(
            np.degrees(np.arctan2(ty, tx) - np.arctan2(wy, wx))
        )

        if not any(
            abs(theta_deg - t) < 1e-6 and abs(chi_deg - c_existing) < 1e-6
            for t, c_existing in solutions
        ):
            solutions.append((theta_deg, chi_deg))

    if not solutions:
        return {"tth": [], "theta": [], "phi": [], "chi": [], "number_of_solutions": 0}

    return {
        "tth": [tth_result] * len(solutions),
        "theta": [sol[0] for sol in solutions],
        "phi": [phi_fixed] * len(solutions),
        "chi": [sol[1] for sol in solutions],
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
        # momentum transfer at theta, phi, chi = 0
        k_vec_initial = calculate_scattering_vector(k_in, tth)

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
