"""Tests for advisor.features.structure_factor.domain.plane_utils."""
import pytest

from advisor.features.structure_factor.domain.plane_utils import (
    generate_hkl_points_on_plane,
    check_accessibility,
)


class TestGenerateHklPointsOnPlane:
    def test_point_count(self):
        """u_range/v_range steps each produce (range+1) values, centered at 0."""
        uv_points, hkl_points = generate_hkl_points_on_plane(
            U=(1, 0, 0), V=(0, 1, 0), C=(0, 0, 1), u_range=2, v_range=2
        )
        assert len(uv_points) == 3 * 3  # u,v in {-1,0,1}
        assert len(hkl_points) == len(uv_points)

    def test_center_point_present(self):
        uv_points, hkl_points = generate_hkl_points_on_plane(
            U=(1, 0, 0), V=(0, 1, 0), C=(2, 3, 4), u_range=2, v_range=2
        )
        center = next(p for p in uv_points if p["u"] == 0 and p["v"] == 0)
        assert (center["H"], center["K"], center["L"]) == (2, 3, 4)

    def test_hkl_computed_from_basis_vectors(self):
        uv_points, hkl_points = generate_hkl_points_on_plane(
            U=(1, 0, 0), V=(0, 2, 0), C=(0, 0, 1), u_range=2, v_range=2
        )
        point = next(p for p in uv_points if p["u"] == 1 and p["v"] == 1)
        assert (point["H"], point["K"], point["L"]) == (1, 2, 1)

    def test_uv_points_and_hkl_points_are_parallel(self):
        uv_points, hkl_points = generate_hkl_points_on_plane(
            U=(1, 1, 0), V=(0, 1, 1), C=(0, 0, 0), u_range=3, v_range=4
        )
        for uv, hkl in zip(uv_points, hkl_points):
            assert [uv["H"], uv["K"], uv["L"]] == hkl

    def test_asymmetric_range(self):
        """u_range=3 -> 4 steps, split -1..2 per the u_min/u_max formula."""
        uv_points, _ = generate_hkl_points_on_plane(
            U=(1, 0, 0), V=(0, 1, 0), C=(0, 0, 0), u_range=3, v_range=1
        )
        u_values = sorted(set(p["u"] for p in uv_points))
        v_values = sorted(set(p["v"] for p in uv_points))
        assert u_values == [-1, 0, 1, 2]
        assert v_values == [0, 1]


class _FakeAngleCalculator:
    """Duck-typed stand-in for BrillouinCalculator, per plane_utils's DI contract."""

    def __init__(self, response_by_hkl=None, raise_for_hkl=None):
        self._response_by_hkl = response_by_hkl or {}
        self._raise_for_hkl = raise_for_hkl or set()

    def calculate_angles(self, H, K, L, fixed_angle, fixed_angle_name):
        key = (H, K, L)
        if key in self._raise_for_hkl:
            raise RuntimeError("simulated solver failure")
        return self._response_by_hkl.get(key, {"success": False})


CONSTRAINTS = {
    "tth_min": 0.0, "tth_max": 180.0,
    "theta_min": 0.0, "theta_max": 180.0,
    "chi_min": -90.0, "chi_max": 90.0,
    "phi_min": -90.0, "phi_max": 90.0,
    "fixed_angle_name": "chi",
    "fixed_angle_value": 0.0,
}


class TestCheckAccessibility:
    def test_point_within_ranges_is_accessible(self):
        uv_points = [{"u": 0, "v": 0, "H": 1, "K": 0, "L": 0}]
        hkl_points = [[1, 0, 0]]
        calc = _FakeAngleCalculator(response_by_hkl={
            (1, 0, 0): {
                "success": True, "number_of_solutions": 1,
                "tth": [60.0], "theta": [30.0], "phi": [0.0], "chi": [0.0],
            }
        })
        inaccessible = check_accessibility(uv_points, hkl_points, calc, CONSTRAINTS)
        assert inaccessible == []

    def test_point_outside_ranges_is_inaccessible(self):
        uv_points = [{"u": 0, "v": 0, "H": 1, "K": 0, "L": 0}]
        hkl_points = [[1, 0, 0]]
        calc = _FakeAngleCalculator(response_by_hkl={
            (1, 0, 0): {
                "success": True, "number_of_solutions": 1,
                "tth": [60.0], "theta": [200.0], "phi": [0.0], "chi": [0.0],  # theta out of range
            }
        })
        inaccessible = check_accessibility(uv_points, hkl_points, calc, CONSTRAINTS)
        assert inaccessible == uv_points

    def test_one_of_two_solutions_within_range_is_accessible(self):
        uv_points = [{"u": 0, "v": 0, "H": 1, "K": 0, "L": 0}]
        hkl_points = [[1, 0, 0]]
        calc = _FakeAngleCalculator(response_by_hkl={
            (1, 0, 0): {
                "success": True, "number_of_solutions": 2,
                "tth": [60.0, 60.0],
                "theta": [200.0, 30.0],  # first out of range, second in range
                "phi": [0.0, 0.0],
                "chi": [0.0, 0.0],
            }
        })
        inaccessible = check_accessibility(uv_points, hkl_points, calc, CONSTRAINTS)
        assert inaccessible == []

    def test_failed_solve_is_inaccessible(self):
        uv_points = [{"u": 0, "v": 0, "H": 1, "K": 0, "L": 0}]
        hkl_points = [[1, 0, 0]]
        calc = _FakeAngleCalculator(response_by_hkl={(1, 0, 0): {"success": False}})
        inaccessible = check_accessibility(uv_points, hkl_points, calc, CONSTRAINTS)
        assert inaccessible == uv_points

    def test_exception_from_calculator_is_inaccessible(self):
        uv_points = [{"u": 0, "v": 0, "H": 1, "K": 0, "L": 0}]
        hkl_points = [[1, 0, 0]]
        calc = _FakeAngleCalculator(raise_for_hkl={(1, 0, 0)})
        inaccessible = check_accessibility(uv_points, hkl_points, calc, CONSTRAINTS)
        assert inaccessible == uv_points

    def test_no_solutions_is_inaccessible(self):
        uv_points = [{"u": 0, "v": 0, "H": 1, "K": 0, "L": 0}]
        hkl_points = [[1, 0, 0]]
        calc = _FakeAngleCalculator(response_by_hkl={
            (1, 0, 0): {"success": True, "number_of_solutions": 0,
                        "tth": [], "theta": [], "phi": [], "chi": []}
        })
        inaccessible = check_accessibility(uv_points, hkl_points, calc, CONSTRAINTS)
        assert inaccessible == uv_points

    def test_mixed_batch_returns_only_inaccessible_points(self):
        uv_points = [
            {"u": 0, "v": 0, "H": 1, "K": 0, "L": 0},
            {"u": 1, "v": 0, "H": 2, "K": 0, "L": 0},
        ]
        hkl_points = [[1, 0, 0], [2, 0, 0]]
        calc = _FakeAngleCalculator(response_by_hkl={
            (1, 0, 0): {"success": True, "number_of_solutions": 1,
                        "tth": [60.0], "theta": [30.0], "phi": [0.0], "chi": [0.0]},
            (2, 0, 0): {"success": False},
        })
        inaccessible = check_accessibility(uv_points, hkl_points, calc, CONSTRAINTS)
        assert inaccessible == [uv_points[1]]

    def test_with_real_brillouin_calculator(self, make_calculator):
        """Integration-style check using the real duck-typed BrillouinCalculator,
        matching how StructureFactorController wires this up in practice."""
        calc = make_calculator("cubic")
        uv_points, hkl_points = generate_hkl_points_on_plane(
            U=(1, 0, 0), V=(0, 1, 0), C=(0, 0, 0), u_range=2, v_range=2
        )
        constraints = {
            "tth_min": 0.0, "tth_max": 180.0,
            "theta_min": -180.0, "theta_max": 180.0,
            "chi_min": -180.0, "chi_max": 180.0,
            "phi_min": -180.0, "phi_max": 180.0,
            "fixed_angle_name": "chi",
            "fixed_angle_value": 0.0,
        }
        inaccessible = check_accessibility(uv_points, hkl_points, calc, constraints)
        # H=K=L=0 (the center point) must always be accessible/trivial.
        center = next(p for p in uv_points if p["u"] == 0 and p["v"] == 0)
        assert center not in inaccessible
