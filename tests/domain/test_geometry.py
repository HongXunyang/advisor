"""Tests for advisor.domain.geometry: vector construction and rotation matrices."""
import numpy as np
import pytest

from advisor.domain.geometry import (
    get_real_space_vectors,
    get_reciprocal_space_vectors,
    euler_to_matrix,
    angle_to_matrix,
    get_rotation,
    sample_to_lab_conversion,
    lab_to_sample_conversion,
)

from tests.conftest import LATTICE_CONFIGS, ALL_CRYSTAL_TYPES


class TestRealSpaceVectors:
    """Tests for get_real_space_vectors."""

    def test_cubic_axes_are_orthogonal_unit_directions(self):
        cfg = LATTICE_CONFIGS["cubic"]
        a_vec, b_vec, c_vec = get_real_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )
        assert a_vec == pytest.approx([cfg["a"], 0, 0])
        assert b_vec == pytest.approx([0, cfg["b"], 0])
        assert c_vec == pytest.approx([0, 0, cfg["c"]])

    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_vector_lengths_match_lattice_constants(self, crystal_type):
        cfg = LATTICE_CONFIGS[crystal_type]
        a_vec, b_vec, c_vec = get_real_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )
        assert np.linalg.norm(a_vec) == pytest.approx(cfg["a"])
        assert np.linalg.norm(b_vec) == pytest.approx(cfg["b"])
        assert np.linalg.norm(c_vec) == pytest.approx(cfg["c"])

    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_interaxial_angles_match_lattice_angles(self, crystal_type):
        """The angle between real-space vectors should reproduce alpha/beta/gamma."""
        cfg = LATTICE_CONFIGS[crystal_type]
        a_vec, b_vec, c_vec = get_real_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )

        def angle_between(u, v):
            cos_angle = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
            return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))

        # alpha = angle(b, c), beta = angle(a, c), gamma = angle(a, b)
        assert angle_between(b_vec, c_vec) == pytest.approx(cfg["alpha"], abs=1e-6)
        assert angle_between(a_vec, c_vec) == pytest.approx(cfg["beta"], abs=1e-6)
        assert angle_between(a_vec, b_vec) == pytest.approx(cfg["gamma"], abs=1e-6)


class TestReciprocalSpaceVectors:
    """Tests for get_reciprocal_space_vectors."""

    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_orthogonality_to_non_conjugate_real_vectors(self, crystal_type):
        """a_star . b = a_star . c = 0 (and cyclic), the defining property of the
        reciprocal lattice."""
        cfg = LATTICE_CONFIGS[crystal_type]
        a_vec, b_vec, c_vec = get_real_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )
        a_star, b_star, c_star = get_reciprocal_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )
        assert np.dot(a_star, b_vec) == pytest.approx(0.0, abs=1e-9)
        assert np.dot(a_star, c_vec) == pytest.approx(0.0, abs=1e-9)
        assert np.dot(b_star, a_vec) == pytest.approx(0.0, abs=1e-9)
        assert np.dot(b_star, c_vec) == pytest.approx(0.0, abs=1e-9)
        assert np.dot(c_star, a_vec) == pytest.approx(0.0, abs=1e-9)
        assert np.dot(c_star, b_vec) == pytest.approx(0.0, abs=1e-9)

    @pytest.mark.parametrize("crystal_type", ALL_CRYSTAL_TYPES)
    def test_conjugate_dot_product_is_2pi(self, crystal_type):
        """a_star . a = 2*pi (and cyclic)."""
        cfg = LATTICE_CONFIGS[crystal_type]
        a_vec, b_vec, c_vec = get_real_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )
        a_star, b_star, c_star = get_reciprocal_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )
        assert np.dot(a_star, a_vec) == pytest.approx(2 * np.pi)
        assert np.dot(b_star, b_vec) == pytest.approx(2 * np.pi)
        assert np.dot(c_star, c_vec) == pytest.approx(2 * np.pi)

    def test_cubic_reciprocal_vectors_along_axes(self):
        cfg = LATTICE_CONFIGS["cubic"]
        a_star, b_star, c_star = get_reciprocal_space_vectors(
            cfg["a"], cfg["b"], cfg["c"], cfg["alpha"], cfg["beta"], cfg["gamma"]
        )
        assert a_star == pytest.approx([2 * np.pi / cfg["a"], 0, 0])
        assert b_star == pytest.approx([0, 2 * np.pi / cfg["b"], 0])
        assert c_star == pytest.approx([0, 0, 2 * np.pi / cfg["c"]])


class TestEulerToMatrix:
    """Tests for euler_to_matrix (ZYX convention, lattice roll/pitch/yaw)."""

    def test_identity_at_zero_angles(self):
        assert euler_to_matrix(0, 0, 0) == pytest.approx(np.eye(3))

    @pytest.mark.parametrize("roll,pitch,yaw", [
        (30, 0, 0), (0, 45, 0), (0, 0, 60), (15, -20, 35), (90, 90, 90),
    ])
    def test_orthogonal_rotation_matrix(self, roll, pitch, yaw):
        """Rotation matrices must be orthogonal with determinant 1."""
        R = euler_to_matrix(roll, pitch, yaw)
        assert R.T @ R == pytest.approx(np.eye(3), abs=1e-10)
        assert np.linalg.det(R) == pytest.approx(1.0)

    def test_yaw_rotates_x_towards_y(self):
        """Rz(90) applied to (1,0,0) should give (0,1,0) (right-hand rule)."""
        R = euler_to_matrix(0, 0, 90)
        assert R @ np.array([1, 0, 0]) == pytest.approx([0, 1, 0], abs=1e-10)

    def test_roll_rotates_y_towards_z(self):
        """Rx(90) applied to (0,1,0) should give (0,0,1) (right-hand rule)."""
        R = euler_to_matrix(90, 0, 0)
        assert R @ np.array([0, 1, 0]) == pytest.approx([0, 0, 1], abs=1e-10)

    def test_pitch_rotates_z_towards_x(self):
        """Ry(90) applied to (0,0,1) should give (1,0,0) (right-hand rule)."""
        R = euler_to_matrix(0, 90, 0)
        assert R @ np.array([0, 0, 1]) == pytest.approx([1, 0, 0], abs=1e-10)

    def test_zyx_order(self):
        """euler_to_matrix should equal Rz @ Ry @ Rx explicitly."""
        roll, pitch, yaw = 12.0, -34.0, 56.0
        roll_r, pitch_r, yaw_r = np.radians([roll, pitch, yaw])
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(roll_r), -np.sin(roll_r)],
            [0, np.sin(roll_r), np.cos(roll_r)],
        ])
        Ry = np.array([
            [np.cos(pitch_r), 0, np.sin(pitch_r)],
            [0, 1, 0],
            [-np.sin(pitch_r), 0, np.cos(pitch_r)],
        ])
        Rz = np.array([
            [np.cos(yaw_r), -np.sin(yaw_r), 0],
            [np.sin(yaw_r), np.cos(yaw_r), 0],
            [0, 0, 1],
        ])
        expected = Rz @ Ry @ Rx
        assert euler_to_matrix(roll, pitch, yaw) == pytest.approx(expected)


class TestAngleToMatrix:
    """Tests for angle_to_matrix (theta about Z, chi about Y, phi about X)."""

    def test_identity_at_zero_angles(self):
        assert angle_to_matrix(0, 0, 0) == pytest.approx(np.eye(3))

    @pytest.mark.parametrize("theta,phi,chi", [
        (30, 0, 0), (0, 45, 0), (0, 0, 60), (15, -20, 35), (-90, 90, -45),
    ])
    def test_orthogonal_rotation_matrix(self, theta, phi, chi):
        R = angle_to_matrix(theta, phi, chi)
        assert R.T @ R == pytest.approx(np.eye(3), abs=1e-10)
        assert np.linalg.det(R) == pytest.approx(1.0)

    def test_theta_rotates_x_towards_y(self):
        """theta rotates about Z: (1,0,0) -> (0,1,0) at theta=90."""
        R = angle_to_matrix(theta=90, phi=0, chi=0)
        assert R @ np.array([1, 0, 0]) == pytest.approx([0, 1, 0], abs=1e-10)

    def test_chi_rotates_about_y_axis(self):
        """chi rotates about Y: (0,0,1) -> (1,0,0) at chi=90 (with theta=phi=0)."""
        R = angle_to_matrix(theta=0, phi=0, chi=90)
        assert R @ np.array([0, 0, 1]) == pytest.approx([1, 0, 0], abs=1e-10)

    def test_phi_rotates_about_x_axis(self):
        """phi rotates about X: (0,1,0) -> (0,0,1) at phi=90 (with theta=chi=0)."""
        R = angle_to_matrix(theta=0, phi=90, chi=0)
        assert R @ np.array([0, 1, 0]) == pytest.approx([0, 0, 1], abs=1e-10)

    def test_is_inverse_returns_transpose(self):
        theta, phi, chi = 25.0, -40.0, 15.0
        R = angle_to_matrix(theta, phi, chi)
        R_inv = angle_to_matrix(theta, phi, chi, is_inverse=True)
        assert R_inv == pytest.approx(R.T)
        assert R_inv @ R == pytest.approx(np.eye(3), abs=1e-10)


class TestGetRotation:
    """Tests for get_rotation (chi about Y, phi about X, no theta component)."""

    def test_identity_at_zero_angles(self):
        assert get_rotation(0, 0) == pytest.approx(np.eye(3))

    @pytest.mark.parametrize("phi,chi", [(30, 0), (0, 45), (20, -35)])
    def test_orthogonal_rotation_matrix(self, phi, chi):
        R = get_rotation(phi, chi)
        assert R.T @ R == pytest.approx(np.eye(3), abs=1e-10)
        assert np.linalg.det(R) == pytest.approx(1.0)

    def test_matches_angle_to_matrix_with_zero_theta(self):
        """get_rotation(phi, chi) should equal angle_to_matrix(0, phi, chi)."""
        phi, chi = 17.0, -23.0
        assert get_rotation(phi, chi) == pytest.approx(angle_to_matrix(0, phi, chi))

    def test_is_inverse_returns_transpose(self):
        phi, chi = 12.0, 34.0
        R = get_rotation(phi, chi)
        R_inv = get_rotation(phi, chi, is_inverse=True)
        assert R_inv == pytest.approx(R.T)


class TestSampleLabConversion:
    """Tests for sample_to_lab_conversion / lab_to_sample_conversion round trips."""

    def test_zero_rotation_is_identity(self):
        vectors = (np.array([1, 2, 3]), np.array([4, 5, 6]), np.array([7, 8, 9]))
        lab_vectors = sample_to_lab_conversion(*vectors, roll=0, pitch=0, yaw=0)
        for original, converted in zip(vectors, lab_vectors):
            assert converted == pytest.approx(original)

    @pytest.mark.parametrize("roll,pitch,yaw", [
        (0, 0, 0), (30, 0, 0), (0, 45, 0), (0, 0, 60), (15, -20, 35),
    ])
    def test_round_trip_recovers_original_vectors(self, roll, pitch, yaw):
        vectors = (np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
        lab_vectors = sample_to_lab_conversion(*vectors, roll=roll, pitch=pitch, yaw=yaw)
        sample_vectors = lab_to_sample_conversion(*lab_vectors, roll=roll, pitch=pitch, yaw=yaw)
        for original, recovered in zip(vectors, sample_vectors):
            assert recovered == pytest.approx(original, abs=1e-10)

    def test_sample_to_lab_uses_euler_to_matrix(self):
        """sample_to_lab_conversion should apply euler_to_matrix directly."""
        roll, pitch, yaw = 10.0, 20.0, 30.0
        v = np.array([1.0, 2.0, 3.0])
        a_lab, _, _ = sample_to_lab_conversion(v, v, v, roll, pitch, yaw)
        expected = euler_to_matrix(roll, pitch, yaw) @ v
        assert a_lab == pytest.approx(expected)
