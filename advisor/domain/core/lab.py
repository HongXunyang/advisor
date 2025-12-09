"""This is a class for the lab."""

import numpy as np

from advisor.domain import angle_to_matrix
from .sample import Sample



class Lab:
    """This is a class for the lab."""

    def __init__(self):
        """Initialize the lab."""
        self.sample = Sample()

        self.theta = 0
        self.phi = 0
        self.chi = 0
        self.a_vec_lab = None
        self.b_vec_lab = None
        self.c_vec_lab = None
        self.a_star_vec_lab = None
        self.b_star_vec_lab = None
        self.c_star_vec_lab = None

    def initialize(
        self, a, b, c, alpha, beta, gamma, roll, pitch, yaw, theta, phi, chi
    ):
        """Initialize the lab."""
        self.sample.initialize(a, b, c, alpha, beta, gamma, roll, pitch, yaw)
        self.theta = theta
        self.phi = phi
        self.chi = chi
        self.calculate_real_space_vectors()
        self.calculate_reciprocal_space_vectors()

    def get_sample_angles(self):
        """Get the sample angles."""
        return self.theta, self.phi, self.chi

    def get_lattice_angles(self):
        """get the lattice euler angles: roll pitch and yaw"""
        return self.sample.get_lattice_angles()

    def get_lattice_parameters(self):
        """Get the parameters of the sample."""
        return self.sample.get_lattice_parameters()

    def get_real_space_vectors(self, is_normalized=False):
        """Get the real space vectors in the lab frame."""
        if is_normalized:
            return self.a_vec_lab / np.linalg.norm(self.a_vec_lab), self.b_vec_lab / np.linalg.norm(self.b_vec_lab), self.c_vec_lab / np.linalg.norm(self.c_vec_lab)
        return self.a_vec_lab, self.b_vec_lab, self.c_vec_lab

    def get_reciprocal_space_vectors(self, is_normalized=False):
        """Get the reciprocal space vectors in the lab frame."""
        if is_normalized:
            return self.a_star_vec_lab / np.linalg.norm(self.a_star_vec_lab), self.b_star_vec_lab / np.linalg.norm(self.b_star_vec_lab), self.c_star_vec_lab / np.linalg.norm(self.c_star_vec_lab)
        return self.a_star_vec_lab, self.b_star_vec_lab, self.c_star_vec_lab

    def calculate_real_space_vectors(self):
        """Get the real space vectors in the lab frame."""
        a_vec_sample, b_vec_sample, c_vec_sample = self.sample.get_real_space_vectors()
        rotation_matrix = angle_to_matrix(self.theta, self.phi, self.chi)
        self.a_vec_lab = rotation_matrix @ a_vec_sample
        self.b_vec_lab = rotation_matrix @ b_vec_sample
        self.c_vec_lab = rotation_matrix @ c_vec_sample

    def calculate_reciprocal_space_vectors(self):
        """Get the reciprocal space vectors in the lab frame."""
        a_star_vec_sample, b_star_vec_sample, c_star_vec_sample = (
            self.sample.get_reciprocal_space_vectors()
        )
        rotation_matrix = angle_to_matrix(self.theta, self.phi, self.chi)
        self.a_star_vec_lab = rotation_matrix @ a_star_vec_sample
        self.b_star_vec_lab = rotation_matrix @ b_star_vec_sample
        self.c_star_vec_lab = rotation_matrix @ c_star_vec_sample

    def get_lab_basis(self):
        """Get the lab orthogonal basis vectors, in the lab frame."""
        ex_lab = np.array([1, 0, 0])
        ey_lab = np.array([0, 1, 0])
        ez_lab = np.array([0, 0, 1])
        return ex_lab, ey_lab, ez_lab

    def get_sample_basis(self):
        """Get the sample orthogonal basis vectors, in the lab frame."""
        ex_sample_in_sample, ey_sample_in_sample, ez_sample_in_sample = (
            self.sample.get_sample_basis()
        )  # sample basis in the sample frame

        rotation_matrix = angle_to_matrix(self.theta, self.phi, self.chi)

        # sample basis in the lab frame
        ex_sample_in_lab = rotation_matrix @ ex_sample_in_sample
        ey_sample_in_lab = rotation_matrix @ ey_sample_in_sample
        ez_sample_in_lab = rotation_matrix @ ez_sample_in_sample
        return ex_sample_in_lab, ey_sample_in_lab, ez_sample_in_lab

    def get_lattice_basis(self):
        """Get the lattice orthogonal basis vectors, in the lab frame."""
        ex_lattice_in_sample, ey_lattice_in_sample, ez_lattice_in_sample = (
            self.sample.get_lattice_basis()
        )  # lattice basis in the sample frame

        rotation_matrix = angle_to_matrix(self.theta, self.phi, self.chi)

        # lattice basis in the lab frame
        ex_lattice_in_lab = rotation_matrix @ ex_lattice_in_sample
        ey_lattice_in_lab = rotation_matrix @ ey_lattice_in_sample
        ez_lattice_in_lab = rotation_matrix @ ez_lattice_in_sample
        return ex_lattice_in_lab, ey_lattice_in_lab, ez_lattice_in_lab

    def rotate(self, theta, phi, chi):
        """Rotate the lab."""
        self.theta = theta
        self.phi = phi
        self.chi = chi
        self.calculate_real_space_vectors()
        self.calculate_reciprocal_space_vectors()
