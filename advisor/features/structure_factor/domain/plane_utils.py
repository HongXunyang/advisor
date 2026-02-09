"""Utility functions for HKL plane generation in the structure factor feature."""


def generate_hkl_points_on_plane(U, V, C, u_range, v_range):
    """Generate integer HKL points lying on the plane Center + a*U + b*V.

    Args:
        U: tuple (h, k, l) defining the first basis vector of the plane.
        V: tuple (h, k, l) defining the second basis vector of the plane.
        C: tuple (h, k, l) defining the center of the plane.
        u_range: int, number of steps along U direction.
        v_range: int, number of steps along V direction.

    Returns:
        tuple: (uv_points, hkl_points) where
            uv_points is a list of dicts with keys {'u', 'v', 'H', 'K', 'L'},
            hkl_points is a list of [H, K, L] lists.
    """
    u_min = -(u_range // 2)
    u_max = u_range - (u_range // 2)
    v_min = -(v_range // 2)
    v_max = v_range - (v_range // 2)

    uv_points = []
    hkl_points = []
    for u in range(u_min, u_max + 1):
        for v in range(v_min, v_max + 1):
            H = C[0] + u * U[0] + v * V[0]
            K = C[1] + u * U[1] + v * V[1]
            L = C[2] + u * U[2] + v * V[2]
            uv_points.append({"u": u, "v": v, "H": H, "K": K, "L": L})
            hkl_points.append([H, K, L])

    return uv_points, hkl_points


def check_accessibility(uv_points, hkl_points, angle_calculator, constraints):
    """Check which HKL points are inaccessible given angle constraints.

    This is a pure domain function that accepts the angle calculator via
    dependency injection, avoiding cross-feature imports.

    Args:
        uv_points: list of dicts with keys {'u', 'v', 'H', 'K', 'L'}.
        hkl_points: list of [H, K, L] lists (same order as uv_points).
        angle_calculator: object with a ``calculate_angles(H, K, L,
            fixed_angle, fixed_angle_name)`` method that returns a dict
            with keys ``success``, ``number_of_solutions``, ``tth``,
            ``theta``, ``phi``, ``chi``.
        constraints: dict with keys ``tth_min``, ``tth_max``,
            ``theta_min``, ``theta_max``, ``chi_min``, ``chi_max``,
            ``phi_min``, ``phi_max``, ``fixed_angle_name``,
            ``fixed_angle_value``.

    Returns:
        list of uv_point dicts that are **inaccessible** (no valid
        solution falls within all the specified ranges).
    """
    tth_min = constraints["tth_min"]
    tth_max = constraints["tth_max"]
    theta_min = constraints["theta_min"]
    theta_max = constraints["theta_max"]
    chi_min = constraints["chi_min"]
    chi_max = constraints["chi_max"]
    phi_min = constraints["phi_min"]
    phi_max = constraints["phi_max"]
    fixed_angle_name = constraints["fixed_angle_name"]
    fixed_angle_value = constraints["fixed_angle_value"]

    inaccessible = []

    for pt, hkl in zip(uv_points, hkl_points):
        H, K, L = hkl
        try:
            result = angle_calculator.calculate_angles(
                H, K, L,
                fixed_angle=fixed_angle_value,
                fixed_angle_name=fixed_angle_name,
            )
        except Exception:
            inaccessible.append(pt)
            continue

        if not result.get("success", False):
            inaccessible.append(pt)
            continue

        # Check if at least one solution falls within all ranges
        n_sol = result.get("number_of_solutions", 0)
        any_ok = False
        for i in range(n_sol):
            if (
                tth_min <= result["tth"][i] <= tth_max
                and theta_min <= result["theta"][i] <= theta_max
                and chi_min <= result["chi"][i] <= chi_max
                and phi_min <= result["phi"][i] <= phi_max
            ):
                any_ok = True
                break

        if not any_ok:
            inaccessible.append(pt)

    return inaccessible
