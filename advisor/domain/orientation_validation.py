#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Identifiability validation for UB-matrix orientation fitting.

Before fitting, reject inputs that cannot determine a reliable orientation:
too few measurements, non-finite values, a (0,0,0) reflection, non-physical
energy/tth, duplicate measurements, or measurements whose reciprocal (or
observed) vectors are all parallel (which leaves at least one rotational
degree of freedom unconstrained).

This module also provides `compute_measurement_vectors`, the shared
"turn one DiffractionMeasurement into (g_i, q_i)" step used both here (for
the independence/duplicate checks) and by the Kabsch solver in
`orientation.py`, so the two never drift apart.
"""
from __future__ import annotations

import itertools
import math
from typing import List, Optional, Tuple

import numpy as np

from advisor.domain.geometry import (
    EV_TO_ANGSTROM,
    angle_to_matrix,
    calculate_scattering_vector,
    energy_to_k_in,
    get_reciprocal_space_vectors,
)
from advisor.domain.orientation_types import DiffractionMeasurement, OrientationFitConfig


def compute_measurement_vectors(
    lattice_params: dict, measurement: DiffractionMeasurement
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute (g_i, q_i) for one measurement, where g_i = B.[H,K,L] is the
    bare (lattice-frame) reciprocal vector and q_i is the observed
    scattering vector rotated into the sample frame (i.e. with only the
    goniometer rotation undone, not the orientation U being fit for).

    Solving `q_i ~= U . g_i` for the proper rotation U (over all valid
    measurements) is the Wahba/Kabsch problem `fit_orientation_from_diffraction_tests`
    solves. See the derivation notes in `orientation.py`.
    """
    a_star, b_star, c_star = get_reciprocal_space_vectors(
        lattice_params["a"], lattice_params["b"], lattice_params["c"],
        lattice_params["alpha"], lattice_params["beta"], lattice_params["gamma"],
    )
    g = measurement.H * a_star + measurement.K * b_star + measurement.L * c_star

    k_in = energy_to_k_in(measurement.energy)
    q_beam = calculate_scattering_vector(k_in, measurement.tth)
    g_inv = angle_to_matrix(measurement.theta, measurement.phi, measurement.chi, is_inverse=True)
    q = g_inv @ q_beam

    return g, q


def _sin_angle_between(u: np.ndarray, v: np.ndarray) -> float:
    """sin of the angle between two vectors, via the cross product; 0 if
    either vector is (numerically) zero."""
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu < 1e-12 or nv < 1e-12:
        return 0.0
    return float(np.linalg.norm(np.cross(u, v)) / (nu * nv))


def _has_two_nonparallel(vectors: List[np.ndarray], tol: float) -> bool:
    for u, v in itertools.combinations(vectors, 2):
        if _sin_angle_between(u, v) > tol:
            return True
    return False


def validate_lattice_params(lattice_params: dict) -> Tuple[bool, Optional[str]]:
    """Sanity-check lattice constants before they're used to build the B
    matrix: finite, positive lengths and angles strictly between 0 and 180
    degrees. Mirrors the checks `InitWindow.on_cif_file_changed` already
    applies to CIF-parsed values, but the domain function is also callable
    directly (bypassing that UI), so it needs its own guard against
    malformed/degenerate lattices producing misleading identifiability
    errors or NaN/Inf from the reciprocal-vector construction.
    """
    a, b, c = lattice_params["a"], lattice_params["b"], lattice_params["c"]
    alpha, beta, gamma = lattice_params["alpha"], lattice_params["beta"], lattice_params["gamma"]

    for name, length in (("a", a), ("b", b), ("c", c)):
        if not math.isfinite(length) or length <= 0:
            return False, f"Lattice constant {name}={length} must be a finite, positive length."
    for name, angle in (("alpha", alpha), ("beta", beta), ("gamma", gamma)):
        if not math.isfinite(angle) or not (0.0 < angle < 180.0):
            return False, f"Lattice angle {name}={angle} must be finite and strictly between 0 and 180 degrees."
    return True, None


def validate_measurements(
    lattice_params: dict,
    measurements: List[DiffractionMeasurement],
    config: Optional[OrientationFitConfig] = None,
) -> Tuple[bool, Optional[str]]:
    """Check whether `measurements` can determine a well-posed orientation.

    Returns (identifiable, rejection_reason). rejection_reason is None iff
    identifiable is True.
    """
    config = config or OrientationFitConfig()

    if len(measurements) < config.min_measurements:
        return False, (
            f"At least {config.min_measurements} diffraction measurements are "
            f"required (got {len(measurements)})."
        )

    for i, m in enumerate(measurements):
        if not m.is_finite():
            return False, f"Measurement {i + 1} contains a non-finite value."
        if math.sqrt(m.H**2 + m.K**2 + m.L**2) < config.hkl_zero_tolerance:
            return False, f"Measurement {i + 1} is the (0,0,0) reflection, which carries no orientation information."
        if not math.isfinite(m.energy) or m.energy <= config.energy_min:
            return False, f"Measurement {i + 1} has a non-positive or non-finite energy ({m.energy})."
        if not (config.tth_min < m.tth <= config.tth_max):
            return False, (
                f"Measurement {i + 1} has tth={m.tth} outside the physical range "
                f"({config.tth_min}, {config.tth_max}] degrees."
            )
        for angle_name, angle_value in (("theta", m.theta), ("phi", m.phi), ("chi", m.chi)):
            if not (config.motor_angle_min <= angle_value <= config.motor_angle_max):
                return False, (
                    f"Measurement {i + 1} has {angle_name}={angle_value} outside the "
                    f"supported range [{config.motor_angle_min}, {config.motor_angle_max}] degrees."
                )

    vectors = [compute_measurement_vectors(lattice_params, m) for m in measurements]
    g_vectors = [g for g, _ in vectors]
    q_vectors = [q for _, q in vectors]

    # Rotation preserves vector norm, so a physically valid measurement must
    # have |g_i| ~= |q_i|; a mismatch means the entered HKL is inconsistent
    # with the entered tth/energy, independent of orientation.
    for i, (g_i, q_i) in enumerate(vectors):
        g_norm, q_norm = np.linalg.norm(g_i), np.linalg.norm(q_i)
        if g_norm < 1e-12:
            continue  # already rejected as (0,0,0) above
        relative_mismatch = abs(g_norm - q_norm) / g_norm
        if relative_mismatch > config.magnitude_mismatch_tolerance:
            m = measurements[i]
            k_in = energy_to_k_in(m.energy)
            ratio = g_norm / (2 * k_in)
            if ratio <= 1.0:
                expected_tth = 2 * math.degrees(math.asin(ratio))
                where = f"expected tth ≈ {expected_tth:.2f}°, but tth = {m.tth:g}° was entered"
            else:
                min_energy = (g_norm / 2) * EV_TO_ANGSTROM / (2 * math.pi)
                where = f"not reachable at {m.energy:g} eV at any angle (needs >= ~{min_energy:.0f} eV)"
            return False, (
                f"Measurement {i + 1}: HKL ({m.H:g},{m.K:g},{m.L:g}) doesn't satisfy Bragg's "
                f"law at {m.energy:g} eV ({where}, |Q| off by {relative_mismatch:.0%}). "
                f"Check for a tth/θ mix-up, energy units (eV not keV), the HKL, or the lattice constants."
            )

    # Duplicate / near-duplicate detection, using the combined (g, q) vectors
    # rather than raw HKL/angle tuples so it reflects actual physical distinctness.
    for (i, (g_i, q_i)), (j, (g_j, q_j)) in itertools.combinations(enumerate(vectors), 2):
        combined_dist = np.linalg.norm(g_i - g_j) + np.linalg.norm(q_i - q_j)
        if combined_dist < config.duplicate_tolerance:
            return False, f"Measurements {i + 1} and {j + 1} are duplicates (or near-duplicates) of each other."

    if not _has_two_nonparallel(g_vectors, config.parallel_sin_tolerance):
        return False, (
            "All reciprocal-lattice vectors (from the given HKL) are parallel; "
            "at least two non-parallel reflections are required to determine an orientation."
        )

    if not _has_two_nonparallel(q_vectors, config.parallel_sin_tolerance):
        return False, (
            "All observed scattering vectors (from the given angles) are parallel; "
            "at least two non-parallel measurements are required to determine an orientation."
        )

    return True, None
