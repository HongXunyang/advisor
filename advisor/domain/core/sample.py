"""This is a module for the sample class."""

import numpy as np

from advisor.domain import euler_to_matrix
from .lattice import Lattice

class Sample:
    """This is a class for the sample."""

    def __init__(self):
        """Initialize the sample."""
        self.lattice = Lattice()
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.a_vec_sample = None
        self.b_vec_sample = None
        self.c_vec_sample = None
        self.a_star_vec_sample = None
        self.b_star_vec_sample = None
        self.c_star_vec_sample = None

    def initialize(self, a, b, c, alpha, beta, gamma, roll, pitch, yaw):
        """Initialize the sample.

        Args:
            a, b, c (float): Lattice constants in Angstroms
            alpha, beta, gamma (float): Lattice angles in degrees
            roll, pitch, yaw (float): Euler angles in degrees
        """
        self.lattice.initialize(a, b, c, alpha, beta, gamma)
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.calculate_real_space_vectors()
        self.calculate_reciprocal_space_vectors()

    def get_lattice_parameters(self):
        """Get the parameters of the sample. if None, raise "initialize the sample first"."""
        try:
            return self.lattice.get_lattice_parameters()
        except KeyError as exc:
            raise ValueError("initialize the sample first") from exc

    def get_lattice_angles(self):
        """get the lattice euler angles: roll pitch and yaw"""
        return self.roll, self.pitch, self.yaw

    def get_real_space_vectors(self):
        """Get the real space vectors in the sample frame."""
        return self.a_vec_sample, self.b_vec_sample, self.c_vec_sample

    def get_reciprocal_space_vectors(self):
        """Get the reciprocal space vectors in the sample frame."""
        return self.a_star_vec_sample, self.b_star_vec_sample, self.c_star_vec_sample

    def get_reciprocal_sample_basis(self):
        """Get the reciprocal sample basis vectors."""
        return self.a_star_vec_sample, self.b_star_vec_sample, self.c_star_vec_sample

    def get_sample_basis(self):
        """Get the sample orthogonal basis vectors, in the sample frame."""
        ex_sample_in_sample = np.array([1, 0, 0])
        ey_sample_in_sample = np.array([0, 1, 0])
        ez_sample_in_sample = np.array([0, 0, 1])
        return ex_sample_in_sample, ey_sample_in_sample, ez_sample_in_sample

    def get_lattice_basis(self):
        """Get the lattice orthogonal basis vectors, in sample frame."""
        ex_lattice_in_lattice, ey_lattice_in_lattice, ez_lattice_in_lattice = (
            self.lattice.get_lattice_basis()
        )
        rotation_matrix = euler_to_matrix(self.roll, self.pitch, self.yaw)
        ex_lattice = rotation_matrix @ ex_lattice_in_lattice
        ey_lattice = rotation_matrix @ ey_lattice_in_lattice
        ez_lattice = rotation_matrix @ ez_lattice_in_lattice
        return ex_lattice, ey_lattice, ez_lattice

    def calculate_real_space_vectors(self):
        """Get the real space vectors in the sample frame."""
        a_vec_lattice, b_vec_lattice, c_vec_lattice = (
            self.lattice.get_real_space_vectors()
        )
        rotation_matrix = euler_to_matrix(self.roll, self.pitch, self.yaw)
        self.a_vec_sample = rotation_matrix @ a_vec_lattice
        self.b_vec_sample = rotation_matrix @ b_vec_lattice
        self.c_vec_sample = rotation_matrix @ c_vec_lattice

    def calculate_reciprocal_space_vectors(self):
        """Get the reciprocal space vectors in the sample frame."""
        a_star_vec_lattice, b_star_vec_lattice, c_star_vec_lattice = (
            self.lattice.get_reciprocal_space_vectors()
        )
        rotation_matrix = euler_to_matrix(self.roll, self.pitch, self.yaw)
        self.a_star_vec_sample = rotation_matrix @ a_star_vec_lattice
        self.b_star_vec_sample = rotation_matrix @ b_star_vec_lattice
        self.c_star_vec_sample = rotation_matrix @ c_star_vec_lattice

    def rotate(self, theta, phi, chi):
        """Rotate the sample."""
