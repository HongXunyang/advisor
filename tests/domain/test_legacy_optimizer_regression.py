"""Regression comparison between the retired multi-start L-BFGS-B optimizer
and the new deterministic Kabsch/SVD solver in advisor.domain.orientation.

The L-BFGS-B optimizer that used to be `fit_orientation_from_diffraction_tests`
is kept here only, as a cross-check that the new closed-form solver agrees
with it on the same synthetic data. It is intentionally not part of the
shipped `advisor` package.
"""
import numpy as np
import pytest

from advisor.domain.geometry import euler_to_matrix
from advisor.domain.orientation import fit_orientation_from_diffraction_tests
from advisor.domain.orientation_calculator import OrientationCalculator
from tests.conftest import LATTICE_CONFIGS

DEFAULT_N_RESTARTS = 20
TARGET_RESIDUAL = 1e-10


def _legacy_fit_orientation(
    lattice_params: dict,
    diffraction_tests: list,
    initial_guess: tuple = (0.0, 0.0, 0.0),
    n_restarts: int = DEFAULT_N_RESTARTS,
) -> dict:
    """Verbatim copy of the retired multi-start L-BFGS-B orientation fit,
    kept only for regression comparison against the Kabsch solver."""
    from scipy.optimize import minimize

    if not diffraction_tests:
        return {"success": False, "message": "No diffraction tests provided",
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0}

    required_keys = ["H", "K", "L", "energy", "tth", "theta", "phi", "chi"]
    for i, test in enumerate(diffraction_tests):
        missing = [k for k in required_keys if k not in test]
        if missing:
            return {"success": False, "message": f"Test {i+1} is missing required keys: {missing}",
                    "roll": 0.0, "pitch": 0.0, "yaw": 0.0}

    calculator = OrientationCalculator()
    init_params = {
        "a": lattice_params["a"], "b": lattice_params["b"], "c": lattice_params["c"],
        "alpha": lattice_params["alpha"], "beta": lattice_params["beta"], "gamma": lattice_params["gamma"],
        "energy": diffraction_tests[0]["energy"],
        "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
    }
    if not calculator.initialize(init_params):
        return {"success": False, "message": "Failed to initialize calculator with given lattice parameters",
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0}

    def objective(params):
        roll, pitch, yaw = params
        calculator.reorient_sample(roll, pitch, yaw)
        total_error = 0.0
        for test in diffraction_tests:
            calculator.change_energy(test["energy"])
            result = calculator.calculate_hkl(test["tth"], test["theta"], test["phi"], test["chi"])
            dH = result["H"] - test["H"]
            dK = result["K"] - test["K"]
            dL = result["L"] - test["L"]
            total_error += dH**2 + dK**2 + dL**2
        return total_error

    def run_optimization(start_point):
        return minimize(objective, start_point, method="L-BFGS-B",
                         bounds=[(-180, 180), (-180, 180), (-180, 180)],
                         options={"ftol": 1e-12, "gtol": 1e-10, "maxiter": 1000})

    best_result = None
    best_error = float("inf")
    initial_points = [initial_guess]
    rng = np.random.default_rng(seed=42)
    for _ in range(n_restarts - 1):
        initial_points.append(tuple(rng.uniform(-180, 180, 3)))
    structured_points = [(0, 0, 0), (90, 0, 0), (-90, 0, 0), (0, 90, 0), (0, -90, 0), (0, 0, 90), (0, 0, -90)]
    for pt in structured_points:
        if pt not in initial_points:
            initial_points.append(pt)

    for start_point in initial_points:
        try:
            result = run_optimization(start_point)
            if result.fun < best_error:
                best_error = result.fun
                best_result = result
            if best_error < TARGET_RESIDUAL:
                break
        except Exception:
            continue

    if best_result is None:
        return {"success": False, "message": "All optimization attempts failed",
                "roll": 0.0, "pitch": 0.0, "yaw": 0.0}

    roll_opt, pitch_opt, yaw_opt = best_result.x
    return {
        "success": best_result.success,
        "roll": float(roll_opt), "pitch": float(pitch_opt), "yaw": float(yaw_opt),
        "residual_error": float(best_result.fun),
    }


def _check_matrices_close(roll_a, pitch_a, yaw_a, roll_b, pitch_b, yaw_b, atol=1e-3):
    m_a = euler_to_matrix(roll_a, pitch_a, yaw_a)
    m_b = euler_to_matrix(roll_b, pitch_b, yaw_b)
    assert np.allclose(m_a, m_b, atol=atol)


def _generate_tests(lattice_params, energy, roll, pitch, yaw, angle_sets):
    calc = OrientationCalculator()
    calc.initialize({**lattice_params, "energy": energy, "roll": roll, "pitch": pitch, "yaw": yaw})
    tests = []
    for tth, theta, phi, chi in angle_sets:
        result = calc.calculate_hkl(tth, theta, phi, chi)
        assert result["success"]
        tests.append({
            "H": result["H"], "K": result["K"], "L": result["L"],
            "energy": energy, "tth": tth, "theta": theta, "phi": phi, "chi": chi,
        })
    return tests


@pytest.mark.parametrize("true_roll, true_pitch, true_yaw", [
    (0.0, 0.0, 0.0),
    (5.0, 3.0, 7.0),
    (45.0, -30.0, 60.0),
    (1.0, 2.0, 3.0),
])
def test_kabsch_agrees_with_legacy_optimizer(true_roll, true_pitch, true_yaw):
    lattice_params = LATTICE_CONFIGS["orthorhombic"].copy()
    energy = 3000.0
    angle_sets = [
        (90.0, 45.0, 0.0, 0.0),
        (60.0, 30.0, 82, 16),
        (120.0, 60.0, -5.0, 10.0),
    ]
    tests = _generate_tests(lattice_params, energy, true_roll, true_pitch, true_yaw, angle_sets)

    legacy = _legacy_fit_orientation(lattice_params, tests)
    new_result = fit_orientation_from_diffraction_tests(lattice_params, tests)

    assert legacy["success"] is True
    assert new_result.valid is True
    _check_matrices_close(
        legacy["roll"], legacy["pitch"], legacy["yaw"],
        new_result.roll, new_result.pitch, new_result.yaw,
    )
