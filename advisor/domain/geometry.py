"""
here includes the translation functions
"""

import numpy as np


def get_real_space_vectors(a, b, c, alpha, beta, gamma):
    """Get the real space vectors a_vec, b_vec, c_vec from the lattice parameters.
    - a_vec is by-default along x-axis (a, 0, 0)
    - b_vec is by-default (b cos gamma, b sin gamma, 0) on the x-y plane,
    - c_vec is then calculated
    The above convention defines the lattice coordinate system.

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


def get_reciprocal_space_vectors(a, b, c, alpha, beta, gamma):
    """Get the reciprocal space vectors a_star_vec, b_star_vec, c_star_vec from the lattice
    parameters, angles in degrees. These vectors are in the crystal coordinate system.
    """
    a_vec, b_vec, c_vec = get_real_space_vectors(a, b, c, alpha, beta, gamma)
    volumn = abs(np.dot(a_vec, np.cross(b_vec, c_vec)))
    a_star_vec = 2 * np.pi * np.cross(b_vec, c_vec) / volumn
    b_star_vec = 2 * np.pi * np.cross(c_vec, a_vec) / volumn
    c_star_vec = 2 * np.pi * np.cross(a_vec, b_vec) / volumn
    return a_star_vec, b_star_vec, c_star_vec


def euler_to_matrix(roll, pitch, yaw):
    """Convert Euler angles to rotation matrix. We follows the ZYX convention.
    Remember we are using a right-hand rule.

    Args:
        roll (float): rotation about the new X axis in degrees
        pitch (float): rotation about the new Y axis in degrees
        yaw (float): rotation about the original z axis in degrees

    Returns:
        rotation_matrix (np.ndarray): Rotation matrix
    """
    roll_rad, pitch_rad, yaw_rad = (
        np.radians(roll),
        np.radians(pitch),
        np.radians(yaw),
    )
    Rx = np.array(
        [
            [1, 0, 0],
            [0, np.cos(roll_rad), -np.sin(roll_rad)],
            [0, np.sin(roll_rad), np.cos(roll_rad)],
        ]
    )
    # remember this is a right-hand rule
    Ry = np.array(
        [
            [np.cos(pitch_rad), 0, np.sin(pitch_rad)],
            [0, 1, 0],
            [-np.sin(pitch_rad), 0, np.cos(pitch_rad)],
        ]
    )

    Rz = np.array(
        [
            [np.cos(yaw_rad), -np.sin(yaw_rad), 0],
            [np.sin(yaw_rad), np.cos(yaw_rad), 0],
            [0, 0, 1],
        ]
    )

    return Rz @ Ry @ Rx  # ZYX order


def angle_to_matrix(theta, phi, chi, is_inverse = False):
    """Convert angles theta, phi, chi to rotation matrix.
    Pay attention to the direction of the rotation.
    
    Updated for x-y scattering plane (z-axis is normal to scattering plane).

    Args:
        theta (float): rotation about the z-axis in degrees, right-hand rule
        phi (float): rotation about the x-axis in degrees, right-hand rule
        chi (float): rotation about the y-axis in degrees, right-hand rule

    Returns:
        rotation_matrix (np.ndarray): Rotation matrix
    """
    theta_rad, phi_rad, chi_rad = (np.radians(theta), np.radians(phi), np.radians(chi))

    # theta rotation around the z-axis (perpendicular to scattering plane)
    theta_mat = np.array(
        [
            [np.cos(theta_rad), -np.sin(theta_rad), 0],
            [np.sin(theta_rad), np.cos(theta_rad), 0],
            [0, 0, 1],
        ]
    )
    # chi rotation around the y-axis (in scattering plane)
    chi_mat = np.array(
        [
            [np.cos(chi_rad), 0, np.sin(chi_rad)],
            [0, 1, 0],
            [-np.sin(chi_rad), 0, np.cos(chi_rad)],
        ]
    )

    # phi rotation around the x-axis (in scattering plane)
    phi_mat = np.array(
        [
            [1, 0, 0],
            [0, np.cos(phi_rad), -np.sin(phi_rad)],
            [0, np.sin(phi_rad), np.cos(phi_rad)],
        ]
    )

    matrix = theta_mat @ chi_mat @ phi_mat
    if is_inverse:
        matrix = matrix.T
    return matrix


def get_rotation(phi, chi, is_inverse = False):
    """get the rotational matrix that rotates the sample with respect to the scattering plane.
    
    Updated for x-y scattering plane (z-axis is normal to scattering plane).
    phi: rotation about x-axis (in scattering plane)
    chi: rotation about y-axis (in scattering plane)
    """
    # Convert angles to radians
    phi_rad = np.radians(phi)
    chi_rad = np.radians(chi)

    # chi rotation about y-axis (in scattering plane)
    chi_mat_sample = np.array(
        [
            [np.cos(chi_rad), 0, np.sin(chi_rad)],
            [0, 1, 0],
            [-np.sin(chi_rad), 0, np.cos(chi_rad)],
        ]
    )
    # phi rotation about x-axis (in scattering plane)
    phi_mat_sample = np.array(
        [
            [1, 0, 0],
            [0, np.cos(phi_rad), -np.sin(phi_rad)],
            [0, np.sin(phi_rad), np.cos(phi_rad)],
        ]
    )
    matrix = chi_mat_sample @ phi_mat_sample 
    if is_inverse:
        matrix = matrix.T
    return matrix




def sample_to_lab_conversion(
    a_vec_sample, b_vec_sample, c_vec_sample, roll, pitch, yaw
):
    """Convert vectors from sample coordinate system to lab coordinate system.

    Args:
        a_vec_sample, b_vec_sample, c_vec_sample (np.ndarray): Vectors in sample coordinate system
        roll, pitch, yaw (float): Euler angles in degrees

    Returns:
        a_vec_lab, b_vec_lab, c_vec_lab (np.ndarray): Vectors in lab coordinate system
    """
    rotation_matrix = euler_to_matrix(roll, pitch, yaw)
    a_vec_lab = rotation_matrix @ a_vec_sample
    b_vec_lab = rotation_matrix @ b_vec_sample
    c_vec_lab = rotation_matrix @ c_vec_sample
    return a_vec_lab, b_vec_lab, c_vec_lab


def lab_to_sample_conversion(a_vec_lab, b_vec_lab, c_vec_lab, roll, pitch, yaw):
    """Convert vectors from lab coordinate system to sample coordinate system.

    Args:
        a_vec_lab, b_vec_lab, c_vec_lab (np.ndarray): Vectors in lab coordinate system
        roll, pitch, yaw (float): Euler angles in degrees

    Returns:
        a_vec_sample, b_vec_sample, c_vec_sample (np.ndarray): Vectors in sample coordinate system
    """
    rotation_matrix = euler_to_matrix(roll, pitch, yaw)
    a_vec_sample = rotation_matrix.T @ a_vec_lab
    b_vec_sample = rotation_matrix.T @ b_vec_lab
    c_vec_sample = rotation_matrix.T @ c_vec_lab
    return a_vec_sample, b_vec_sample, c_vec_sample
