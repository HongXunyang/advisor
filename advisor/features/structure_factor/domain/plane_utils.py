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
