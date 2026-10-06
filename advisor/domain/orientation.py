#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orientation fitting from diffraction tests.

Determines the crystal orientation (roll, pitch, yaw and the U/UB matrices)
that best explains a set of diffraction measurements (known HKL + measured
goniometer angles), via a deterministic closed-form rotation solve rather
than an iterative optimizer. Two methods are available (`method=`):

  - Busing-Levy (`FIT_METHOD_BUSING_LEVY`, the default): measurement 1 is the
    *primary* reflection and is matched exactly (U g_1 || q_1); measurement 2
    is the *secondary* reflection and only fixes the rotation about q_1 (it
    lies in the plane spanned by q_1, q_2). Further measurements don't affect
    U, only the reported residual. This is the convention of BLISS/SPEC
    (Busing & Levy, Acta Cryst. 22, 457 (1967)); with it ADVISOR reproduces
    the ESRF BLISS UB matrices to their printed precision -- see
    `tests/bliss_validation/test_bliss_ub_comparison.py`.
  - Kabsch (`FIT_METHOD_KABSCH`): symmetric least-squares (Wahba) over all
    measurements, described below.

The two agree exactly for perfectly consistent data. They differ when the
measured angle between reflections disagrees with the one implied by the
lattice constants: Kabsch splits that error between all reflections,
Busing-Levy puts it entirely on the secondary ones.

For each measurement i:
  1. g_i = B.[H_i,K_i,L_i]  -- the expected reciprocal-lattice vector, bare
     (lattice frame, no orientation rotation applied).
  2. q_i -- the observed scattering vector, rotated into the sample frame
     (i.e. only the goniometer rotation is undone; the orientation U is
     exactly what's being solved for). See
     `orientation_validation.compute_measurement_vectors` for the exact
     formula and its derivation/verification notes.
  3. Solve q_i ~= U . g_i for the proper rotation U -- via SVD (Kabsch) using
     all valid measurements at once, or via the Busing-Levy triad
     construction from measurements 1 and 2 -- no local minima, no restarts,
     no initial guess.
  4. U is converted to (roll, pitch, yaw) via `matrix_to_euler_zyx`
     (ZYX convention, matching `euler_to_matrix`).
  5. UB = U @ B is exposed alongside the Euler angles as a convenience.

Fit quality is then independently verified by re-running the existing,
already-tested forward angles->HKL calculation (via `OrientationCalculator`,
which itself now shares its core formula with
`scattering_geometry.domain.core._calculate_hkl` -- see
`advisor.domain.geometry.calculate_scattering_vector`) at the fitted
orientation, and comparing against the measured HKL values. This keeps the
reported residual correct regardless of any subtlety in the solver input
derivation above.

The previous multi-start L-BFGS-B optimizer has been retired from the
shipped code; it lives on only as a regression reference in
`tests/domain/test_legacy_optimizer_regression.py`.

Weighting policy (Kabsch): g_i and q_i are used raw (unnormalized). The SVD solve
therefore implicitly weights each measurement by |g_i|*|q_i| (both equal at
a consistent measurement, since rotation preserves norm) -- higher-order/
larger-|Q| reflections pull the fit harder than low-order ones. Fit
*acceptance*, by contrast, uses the unweighted per-component H/K/L residual
from the independent forward-recomputation step above, not the Kabsch
objective directly -- so the quantity being minimized and the quantity
being thresholded for validity are related but not identical. This was a
deliberate choice (raw vectors, not normalized) rather than an oversight;
it has not been observed to matter for the exact/near-exact data this
solver is meant for, but would be worth revisiting if very mixed reflection
orders or systematically noisy low-order measurements become common.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from advisor.domain.geometry import get_reciprocal_space_vectors, matrix_to_euler_zyx
from advisor.domain.orientation_calculator import OrientationCalculator
from advisor.domain.orientation_types import (
    FIT_METHOD_BUSING_LEVY,
    FIT_METHODS,
    FIT_QUALITY_GOOD,
    FIT_QUALITY_POOR,
    FIT_QUALITY_WARNING,
    DiffractionMeasurement,
    OrientationFitConfig,
    OrientationFitResult,
)
from advisor.domain.orientation_validation import (
    _sin_angle_between,
    compute_measurement_vectors,
    validate_lattice_params,
    validate_measurements,
)

_LATTICE_KEYS = ("a", "b", "c", "alpha", "beta", "gamma")


def _solve_kabsch(g_stack: np.ndarray, q_stack: np.ndarray):
    """Solve for the proper rotation U minimizing sum_i ||q_i - U g_i||^2.

    Returns (U, condition_number), where condition_number is the ratio of
    the largest to smallest singular value of the cross-covariance matrix
    (a measure of how well-conditioned/independent the measurement set is;
    large values mean the measurements are close to degenerate).

    With exactly 2 measurements the 3x3 cross-covariance is a sum of two
    rank-1 terms, so its smallest singular value is *structurally* ~0
    regardless of how well-separated the two measurements are -- two
    non-parallel vector pairs still determine a unique proper rotation via
    the same SVD/determinant-fixup procedure. condition_number is therefore
    None (not a numerically-meaningless "inf") whenever there are fewer than
    3 measurements, since it isn't an informative diagnostic in that case.
    """
    cross_covariance = g_stack.T @ q_stack  # sum_i outer(g_i, q_i)
    w, singular_values, vt = np.linalg.svd(cross_covariance)
    v = vt.T
    d = np.sign(np.linalg.det(v @ w.T))
    if d == 0:
        d = 1.0
    fixup = np.diag([1.0, 1.0, d])
    rotation = v @ fixup @ w.T

    if g_stack.shape[0] < 3:
        condition_number = None
    else:
        smallest = singular_values[-1]
        condition_number = float(singular_values[0] / smallest) if smallest > 1e-12 else float("inf")
    return rotation, condition_number


def _orthonormal_triad(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    """Columns: unit primary, the in-plane unit vector perpendicular to it
    (towards secondary), and their normal -- a right-handed orthonormal basis."""
    t1 = primary / np.linalg.norm(primary)
    t3 = np.cross(primary, secondary)
    t3 = t3 / np.linalg.norm(t3)
    return np.column_stack([t1, np.cross(t3, t1), t3])


def _solve_busing_levy(g1: np.ndarray, g2: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Busing-Levy U: the proper rotation taking the lattice-frame triad of
    (g1, g2) onto the sample-frame triad of (q1, q2). U g1 is exactly parallel
    to q1; U g2 lies in the (q1, q2) plane on q2's side of q1."""
    return _orthonormal_triad(q1, q2) @ _orthonormal_triad(g1, g2).T


def fit_orientation_from_diffraction_tests(
    lattice_params: dict,
    diffraction_tests: list,
    config: Optional[OrientationFitConfig] = None,
    method: str = FIT_METHOD_BUSING_LEVY,
) -> OrientationFitResult:
    """Fit crystal orientation from diffraction test data.

    Breaking change from prior releases: this used to return a plain dict
    and accept `initial_guess`/`n_restarts` parameters (for the retired
    L-BFGS-B optimizer). It now returns an `OrientationFitResult` dataclass
    and takes an optional `OrientationFitConfig` instead. This function is
    re-exported from `advisor.domain` and is technically importable by
    external code, but it has no documented usage examples outside this
    package and no compatibility shim is provided -- see CHANGELOG.md.

    Args:
        lattice_params: dict with a, b, c (Angstrom) and alpha, beta, gamma (degrees).
        diffraction_tests: list of dicts, each with H, K, L, energy, tth, theta, phi, chi.
        config: optional OrientationFitConfig overriding the default tolerances.
        method: `FIT_METHOD_BUSING_LEVY` (default; measurement 1 = primary,
            measurement 2 = secondary) or `FIT_METHOD_KABSCH` (least squares
            over all measurements). See the module docstring.

    Returns:
        OrientationFitResult. Use the Euler angles / UB matrix when
        `result.valid` is True (an orientation was determined); check
        `result.quality` ("good"/"warning"/"poor") for how much to trust it
        -- a completed, identifiable fit is never rejected outright, since
        it's always the chosen method's best rotation for the given
        measurements, but a "poor"-quality one should be surfaced to the
        user as a caveat rather than applied silently.
    """
    config = config or OrientationFitConfig()

    if method not in FIT_METHODS:
        return OrientationFitResult(
            completed=False, identifiable=False, valid=False,
            message=f"Unknown orientation-fit method {method!r}; expected one of {FIT_METHODS}.",
            rejection_reason=f"unknown_method:{method}",
            lattice_params=dict(lattice_params) if isinstance(lattice_params, dict) else {},
        )

    try:
        lattice_clean = {k: float(lattice_params[k]) for k in _LATTICE_KEYS}
    except (KeyError, TypeError, ValueError) as exc:
        return OrientationFitResult(
            completed=False, identifiable=False, valid=False,
            message=f"Invalid lattice parameters: {exc}",
            rejection_reason=str(exc),
            lattice_params=dict(lattice_params) if isinstance(lattice_params, dict) else {},
        )

    lattice_ok, lattice_reason = validate_lattice_params(lattice_clean)
    if not lattice_ok:
        return OrientationFitResult(
            completed=False, identifiable=False, valid=False,
            message=f"Invalid lattice parameters: {lattice_reason}",
            rejection_reason=lattice_reason,
            lattice_params=lattice_clean,
        )

    measurements = []
    for i, raw in enumerate(diffraction_tests):
        try:
            measurements.append(DiffractionMeasurement.from_dict(raw))
        except (KeyError, TypeError, ValueError) as exc:
            return OrientationFitResult(
                completed=False, identifiable=False, valid=False,
                message=f"Measurement {i + 1} is malformed: {exc}",
                rejection_reason=str(exc),
                lattice_params=lattice_clean,
            )

    identifiable, reason = validate_measurements(lattice_clean, measurements, config)
    if not identifiable:
        return OrientationFitResult(
            completed=True, identifiable=False, valid=False,
            message=reason,
            rejection_reason=reason,
            lattice_params=lattice_clean,
            measurements=measurements,
            n_measurements_used=len(measurements),
        )

    vectors = [compute_measurement_vectors(lattice_clean, m) for m in measurements]
    if method == FIT_METHOD_BUSING_LEVY:
        # validate_measurements only requires *some* non-parallel pair; Busing-Levy
        # specifically needs the primary and secondary (rows 1 and 2) to be one.
        (g1, q1), (g2, q2) = vectors[0], vectors[1]
        tol = config.parallel_sin_tolerance
        if _sin_angle_between(g1, g2) <= tol or _sin_angle_between(q1, q2) <= tol:
            reason = (
                "Busing-Levy uses measurements 1 (primary) and 2 (secondary), which must be "
                "non-parallel reflections; reorder the rows or use the Kabsch method."
            )
            return OrientationFitResult(
                completed=True, identifiable=False, valid=False,
                message=reason, rejection_reason=reason,
                lattice_params=lattice_clean, measurements=measurements,
                n_measurements_used=len(measurements), method=method,
            )

    try:
        if method == FIT_METHOD_BUSING_LEVY:
            rotation = _solve_busing_levy(g1, g2, q1, q2)
            condition_number = None
        else:
            g_stack = np.array([g for g, _ in vectors])
            q_stack = np.array([q for _, q in vectors])
            rotation, condition_number = _solve_kabsch(g_stack, q_stack)
        roll, pitch, yaw = matrix_to_euler_zyx(rotation)

        a_star, b_star, c_star = get_reciprocal_space_vectors(**lattice_clean)
        b_matrix = np.column_stack([a_star, b_star, c_star])
        ub_matrix = rotation @ b_matrix

        calculator = OrientationCalculator()
        if not calculator.initialize({
            **lattice_clean, "energy": measurements[0].energy,
            "roll": roll, "pitch": pitch, "yaw": yaw,
        }):
            return OrientationFitResult(
                completed=False, identifiable=True, valid=False,
                message="Failed to initialize calculator for residual verification.",
                rejection_reason="calculator_init_failed",
                lattice_params=lattice_clean, measurements=measurements,
                n_measurements_used=len(measurements),
            )

        per_measurement_residuals = []
        for m in measurements:
            calculator.change_energy(m.energy)
            predicted = calculator.calculate_hkl(m.tth, m.theta, m.phi, m.chi)
            d_h = predicted["H"] - m.H
            d_k = predicted["K"] - m.K
            d_l = predicted["L"] - m.L
            per_measurement_residuals.append(float(np.sqrt(d_h**2 + d_k**2 + d_l**2)))

        residual_rms = float(np.sqrt(np.mean(np.square(per_measurement_residuals))))
    except Exception as exc:  # pragma: no cover - defensive; SVD/init on finite input shouldn't fail
        return OrientationFitResult(
            completed=False, identifiable=True, valid=False,
            message=f"Orientation fit failed unexpectedly: {exc}",
            rejection_reason=str(exc),
            lattice_params=lattice_clean, measurements=measurements,
            n_measurements_used=len(measurements),
        )

    # A completed, identifiable fit is always the method's best
    # rotation for the given measurements -- it's never rejected outright.
    # residual_rms only grades how much to trust it (see quality below).
    if residual_rms < config.residual_rms_warning_threshold:
        quality = FIT_QUALITY_GOOD
        message = "Orientation fit accepted."
    elif residual_rms < config.residual_rms_severe_threshold:
        quality = FIT_QUALITY_WARNING
        message = (
            f"Orientation fit accepted, but the residual RMS ({residual_rms:.3e} r.l.u.) "
            f"is elevated -- the uncertainty on this orientation is a bit large."
        )
    else:
        quality = FIT_QUALITY_POOR
        message = (
            f"Orientation fit accepted, but the residual RMS ({residual_rms:.3e} r.l.u.) "
            f"is large -- treat this orientation with caution."
        )

    return OrientationFitResult(
        completed=True, identifiable=True, valid=True, quality=quality,
        message=message,
        rejection_reason=None,
        U=rotation, UB=ub_matrix, roll=roll, pitch=pitch, yaw=yaw,
        residual_rms=residual_rms, per_measurement_residuals=per_measurement_residuals,
        n_measurements_used=len(measurements), condition_number=condition_number,
        lattice_params=lattice_clean, measurements=measurements, method=method,
    )
