"""Tests for advisor.domain.core: Lattice, Sample, Lab classes."""
import numpy as np
import pytest

from advisor.domain.core import Lattice, Sample, Lab
from advisor.domain.geometry import euler_to_matrix, angle_to_matrix

from tests.conftest import LATTICE_CONFIGS, ALL_CRYSTAL_TYPES


class TestLattice:
    """Tests for the Lattice class."""

    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_initialize_stores_parameters(self, crystal_type):
        cfg = LATTICE_CONFIGS[crystal_type]
        lattice = Lattice()
        lattice.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"])
        a, b, c, alpha, beta, gamma = lattice.get_lattice_parameters()
        assert (a, b, c, alpha, beta, gamma) == (
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )

    def test_real_and_reciprocal_vectors_are_conjugate(self):
        cfg = LATTICE_CONFIGS["orthorhombic"]
        lattice = Lattice()
        lattice.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"])
        a_vec, b_vec, c_vec = lattice.get_real_space_vectors()
        a_star, b_star, c_star = lattice.get_reciprocal_space_vectors()
        assert np.dot(a_star, a_vec) == pytest.approx(2 * np.pi)
        assert np.dot(a_star, b_vec) == pytest.approx(0.0, abs=1e-9)

    def test_lattice_basis_is_identity(self):
        lattice = Lattice()
        ex, ey, ez = lattice.get_lattice_basis()
        assert ex == pytest.approx([1, 0, 0])
        assert ey == pytest.approx([0, 1, 0])
        assert ez == pytest.approx([0, 0, 1])


class TestSample:
    """Tests for the Sample class."""

    def test_no_rotation_sample_vectors_match_lattice_vectors(self):
        cfg = LATTICE_CONFIGS["tetragonal"]
        sample = Sample()
        sample.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], 0, 0, 0)
        a_lattice, b_lattice, c_lattice = sample.lattice.get_real_space_vectors()
        a_sample, b_sample, c_sample = sample.get_real_space_vectors()
        assert a_sample == pytest.approx(a_lattice)
        assert b_sample == pytest.approx(b_lattice)
        assert c_sample == pytest.approx(c_lattice)

    def test_rotation_applies_euler_to_matrix(self):
        cfg = LATTICE_CONFIGS["cubic"]
        roll, pitch, yaw = 10.0, 20.0, 30.0
        sample = Sample()
        sample.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], roll, pitch, yaw)
        a_lattice, _, _ = sample.lattice.get_real_space_vectors()
        a_sample, _, _ = sample.get_real_space_vectors()
        expected = euler_to_matrix(roll, pitch, yaw) @ a_lattice
        assert a_sample == pytest.approx(expected)

    def test_get_lattice_angles_returns_roll_pitch_yaw(self):
        cfg = LATTICE_CONFIGS["cubic"]
        sample = Sample()
        sample.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], 5.0, 6.0, 7.0)
        assert sample.get_lattice_angles() == (5.0, 6.0, 7.0)

    def test_reorient_updates_vectors(self):
        cfg = LATTICE_CONFIGS["cubic"]
        sample = Sample()
        sample.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], 0, 0, 0)
        a_before, _, _ = sample.get_real_space_vectors()

        sample.reorient(0.0, 90.0, 0.0)
        a_after, _, _ = sample.get_real_space_vectors()

        assert sample.get_lattice_angles() == (0.0, 90.0, 0.0)
        assert not np.allclose(a_before, a_after)
        expected = euler_to_matrix(0.0, 90.0, 0.0) @ a_before
        assert a_after == pytest.approx(expected)

    def test_sample_basis_is_identity(self):
        sample = Sample()
        ex, ey, ez = sample.get_sample_basis()
        assert ex == pytest.approx([1, 0, 0])
        assert ey == pytest.approx([0, 1, 0])
        assert ez == pytest.approx([0, 0, 1])


class TestLab:
    """Tests for the Lab class."""

    def test_no_rotation_lab_vectors_match_sample_vectors(self):
        cfg = LATTICE_CONFIGS["hexagonal"]
        lab = Lab()
        lab.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], 0, 0, 0, 0, 0, 0)
        a_sample, b_sample, c_sample = lab.sample.get_real_space_vectors()
        a_lab, b_lab, c_lab = lab.get_real_space_vectors()
        assert a_lab == pytest.approx(a_sample)
        assert b_lab == pytest.approx(b_sample)
        assert c_lab == pytest.approx(c_sample)

    def test_rotate_applies_angle_to_matrix(self):
        cfg = LATTICE_CONFIGS["cubic"]
        lab = Lab()
        lab.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], 0, 0, 0, 0, 0, 0)
        a_sample, _, _ = lab.sample.get_real_space_vectors()

        lab.rotate(theta=45.0, phi=10.0, chi=-5.0)
        a_lab, _, _ = lab.get_real_space_vectors()

        assert lab.get_sample_angles() == (45.0, 10.0, -5.0)
        expected = angle_to_matrix(45.0, 10.0, -5.0) @ a_sample
        assert a_lab == pytest.approx(expected)

    def test_reorient_delegates_to_sample_and_recomputes(self):
        cfg = LATTICE_CONFIGS["cubic"]
        lab = Lab()
        lab.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], 0, 0, 0, 0, 0, 0)

        lab.reorient(roll=15.0, pitch=0.0, yaw=0.0)

        assert lab.get_lattice_angles() == (15.0, 0.0, 0.0)
        a_sample, _, _ = lab.sample.get_real_space_vectors()
        a_lab, _, _ = lab.get_real_space_vectors()
        assert a_lab == pytest.approx(a_sample)  # theta=phi=chi still 0

    def test_normalized_real_space_vectors_are_unit_length(self):
        cfg = LATTICE_CONFIGS["orthorhombic"]
        lab = Lab()
        lab.initialize(cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"], 0, 0, 0, 30, 40, 50)
        a_lab, b_lab, c_lab = lab.get_real_space_vectors(is_normalized=True)
        assert np.linalg.norm(a_lab) == pytest.approx(1.0)
        assert np.linalg.norm(b_lab) == pytest.approx(1.0)
        assert np.linalg.norm(c_lab) == pytest.approx(1.0)

    def test_lab_basis_is_identity(self):
        lab = Lab()
        ex, ey, ez = lab.get_lab_basis()
        assert ex == pytest.approx([1, 0, 0])
        assert ey == pytest.approx([0, 1, 0])
        assert ez == pytest.approx([0, 0, 1])
