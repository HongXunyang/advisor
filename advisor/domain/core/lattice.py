"""This is a module for the lattice class."""

import numpy as np

from advisor.domain import (
    get_real_space_vectors,
    get_reciprocal_space_vectors,
)


class Lattice:
    """This is a class for the lattice."""

    def __init__(self):
        """Initialize the sample."""
        self.a = None
        self.b = None
        self.c = None
        self.alpha = None
        self.beta = None
        self.gamma = None

        # vectors in the lattice frame
        self.a_vec_lattice = None
        self.b_vec_lattice = None
        self.c_vec_lattice = None

        # reciprocal vectors in the lattice frame
        self.a_star_vec_lattice = None
        self.b_star_vec_lattice = None
        self.c_star_vec_lattice = None

    def initialize(self, a, b, c, alpha, beta, gamma):
        """Initialize the sample.

        Args:
            a, b, c (float): Lattice constants in Angstroms
            alpha, beta, gamma (float): Lattice angles in degrees
            roll, pitch, yaw (float): Euler angles in degrees
        """
        # First set the lattice parameters
        self.a = a
        self.b = b
        self.c = c
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        # Then calculate vectors in sample coordinate system
        self.a_vec_lattice, self.b_vec_lattice, self.c_vec_lattice = (
            get_real_space_vectors(a, b, c, alpha, beta, gamma)
        )
        self.a_star_vec_lattice, self.b_star_vec_lattice, self.c_star_vec_lattice = (
            get_reciprocal_space_vectors(a, b, c, alpha, beta, gamma)
        )

    def get_lattice_parameters(self):
        """Get the parameters of the sample. if None, raise "initialize the sample first"."""
        try:
            a, b, c = self.a, self.b, self.c
            alpha, beta, gamma = self.alpha, self.beta, self.gamma
            return a, b, c, alpha, beta, gamma
        except KeyError as exc:
            raise ValueError("initialize the sample first") from exc

    def get_real_space_vectors(self):
        """Get the real space vectors in the lattice frame."""
        return self.a_vec_lattice, self.b_vec_lattice, self.c_vec_lattice

    def get_reciprocal_space_vectors(self):
        """Get the reciprocal space vectors in the lattice frame."""
        return self.a_star_vec_lattice, self.b_star_vec_lattice, self.c_star_vec_lattice

    def get_lattice_basis(self):
        """Get the lattice orthogonal basis vectors, in the lattice frame."""
        ex_lattice_in_lattice = np.array([1, 0, 0])
        ey_lattice_in_lattice = np.array([0, 1, 0])
        ez_lattice_in_lattice = np.array([0, 0, 1])
        return ex_lattice_in_lattice, ey_lattice_in_lattice, ez_lattice_in_lattice
